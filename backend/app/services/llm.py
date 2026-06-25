import logging

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GEMINI_GENERATE_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
)
GEMINI_STREAM_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/{model}:streamGenerateContent"
)


async def _call_groq(messages: list[dict], temperature: float, max_tokens: int) -> tuple[str, dict]:
    settings = get_settings()
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            GROQ_URL,
            headers={"Authorization": f"Bearer {settings.groq_api_key}"},
            json={
                "model": settings.groq_model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
        )
        resp.raise_for_status()
        data = resp.json()
    usage = data.get("usage", {})
    return data["choices"][0]["message"]["content"], {
        "model": settings.groq_model,
        "input_tokens": usage.get("prompt_tokens", 0),
        "output_tokens": usage.get("completion_tokens", 0),
    }


async def _call_gemini(messages: list[dict], temperature: float, max_tokens: int) -> tuple[str, dict]:
    settings = get_settings()
    url = GEMINI_GENERATE_URL.format(model=settings.gemini_model)
    system_parts = [m["content"] for m in messages if m["role"] == "system"]
    contents = [
        {"role": "user" if m["role"] == "user" else "model", "parts": [{"text": m["content"]}]}
        for m in messages
        if m["role"] != "system"
    ]
    payload = {
        "contents": contents,
        "generationConfig": {"temperature": temperature, "maxOutputTokens": max_tokens},
    }
    if system_parts:
        payload["systemInstruction"] = {"parts": [{"text": "\n".join(system_parts)}]}

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(url, params={"key": settings.gemini_api_key}, json=payload)
        resp.raise_for_status()
        data = resp.json()
    text = data["candidates"][0]["content"]["parts"][0]["text"]
    meta = data.get("usageMetadata", {})
    return text, {
        "model": settings.gemini_model,
        "input_tokens": meta.get("promptTokenCount", 0),
        "output_tokens": meta.get("candidatesTokenCount", 0),
    }


async def _call_litellm(messages: list[dict], temperature: float, max_tokens: int) -> tuple[str, dict]:
    try:
        from litellm import acompletion
    except ImportError:
        logger.error("litellm not installed. Falling back to direct Groq/Gemini calls.")
        return await _call_groq(messages, temperature, max_tokens)

    settings = get_settings()
    try:
        response = await acompletion(
            model=settings.llm_model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            fallbacks=[settings.llm_fallback_model],
        )
        content = response.choices[0].message.content
        usage = getattr(response, "usage", {}) or {}
        return content, {
            "model": getattr(response, "model", settings.llm_model),
            "input_tokens": getattr(usage, "prompt_tokens", 0) if not isinstance(usage, dict) else usage.get("prompt_tokens", 0),
            "output_tokens": getattr(usage, "completion_tokens", 0) if not isinstance(usage, dict) else usage.get("completion_tokens", 0),
        }
    except Exception as exc:
        logger.error("All LiteLLM providers failed: %s", exc)
        raise


async def generate(
    messages: list[dict], temperature: float = 0.3, max_tokens: int = 1024
) -> tuple[str, str, dict]:
    """Returns (answer, model_used, usage).

    Behaviour:
    - If LiteLLM model is explicitly configured, uses LiteLLM.
    - Otherwise uses the original Groq -> Gemini fallback chain.
    """
    settings = get_settings()
    if settings.llm_model and settings.llm_model != "groq/llama-3.3-70b-versatile":
        content, meta = await _call_litellm(messages, temperature, max_tokens)
        return content, meta.get("model", "litellm"), meta

    try:
        content, meta = await _call_groq(messages, temperature, max_tokens)
        return content, meta.get("model", "groq"), meta
    except (httpx.HTTPStatusError, httpx.TimeoutException) as exc:
        logger.warning("Groq generation failed (%s), falling back to Gemini", exc)
        content, meta = await _call_gemini(messages, temperature, max_tokens)
        return content, meta.get("model", "gemini"), meta


# ---------------------------------------------------------------------------
# Streaming support
# ---------------------------------------------------------------------------

async def _call_groq_stream(
    messages: list[dict], temperature: float = 0.3, max_tokens: int = 1024
):
    """Async generator yielding token dicts from Groq streaming API."""
    import json
    settings = get_settings()
    async with httpx.AsyncClient(timeout=60) as client:
        async with client.stream(
            "POST",
            GROQ_URL,
            headers={"Authorization": f"Bearer {settings.groq_api_key}"},
            json={
                "model": settings.groq_model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": True,
            },
        ) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line.startswith("data: "):
                    continue
                payload = line[6:].strip()
                if payload == "[DONE]":
                    break
                try:
                    chunk = json.loads(payload)
                    delta = chunk.get("choices", [{}])[0].get("delta", {})
                    content = delta.get("content", "")
                    if content:
                        yield {"type": "token", "content": content}
                except json.JSONDecodeError:
                    continue


async def _call_gemini_stream(
    messages: list[dict], temperature: float = 0.3, max_tokens: int = 1024
):
    """Async generator yielding token dicts from Gemini streaming API."""
    import json
    settings = get_settings()
    url = GEMINI_STREAM_URL.format(model=settings.gemini_model)
    system_parts = [m["content"] for m in messages if m["role"] == "system"]
    contents = [
        {"role": "user" if m["role"] == "user" else "model", "parts": [{"text": m["content"]}]}
        for m in messages
        if m["role"] != "system"
    ]
    payload = {
        "contents": contents,
        "generationConfig": {"temperature": temperature, "maxOutputTokens": max_tokens},
    }
    if system_parts:
        payload["systemInstruction"] = {"parts": [{"text": "\n".join(system_parts)}]}

    async with httpx.AsyncClient(timeout=60) as client:
        async with client.stream(
            "POST", url, params={"key": settings.gemini_api_key}, json=payload
        ) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line.startswith("data: "):
                    continue
                payload = line[6:].strip()
                try:
                    data = json.loads(payload)
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        for part in parts:
                            text = part.get("text", "")
                            if text:
                                yield {"type": "token", "content": text}
                except json.JSONDecodeError:
                    continue


async def generate_stream(
    messages: list[dict], temperature: float = 0.3, max_tokens: int = 1024
):
    """Async generator that yields streamed tokens + final metadata.

    Yields dicts with keys:
      - {"type": "token", "content": "..."} for each token
      - {"type": "done", "answer": "...", "model": "...", "usage": {...}} at end
    """
    settings = get_settings()
    # Collect full answer for the done event
    full_answer = ""
    model_used = ""
    usage = {}

    try:
        if settings.llm_model and settings.llm_model != "groq/llama-3.3-70b-versatile":
            # LiteLLM streaming — fall back to non-streaming for now since LiteLLM import may fail
            content, meta = await _call_litellm(messages, temperature, max_tokens)
            full_answer = content
            yield {"type": "token", "content": content}
        else:
            try:
                async for event in _call_groq_stream(messages, temperature, max_tokens):
                    full_answer += event["content"]
                    yield event
                model_used = settings.groq_model
                # Estimate usage from input
                input_tokens = sum(len(m.get("content", "")) for m in messages) // 4
                output_tokens = len(full_answer) // 4
                usage = {"input_tokens": input_tokens, "output_tokens": output_tokens}
            except Exception as exc:
                logger.warning("Groq streaming failed (%s), falling back to Gemini", exc)
                async for event in _call_gemini_stream(messages, temperature, max_tokens):
                    full_answer += event["content"]
                    yield event
                model_used = settings.gemini_model
                input_tokens = sum(len(m.get("content", "")) for m in messages) // 4
                output_tokens = len(full_answer) // 4
                usage = {"input_tokens": input_tokens, "output_tokens": output_tokens}
    except Exception as exc:
        logger.error("All streaming providers failed: %s", exc)
        full_answer = f"Error: {exc}"
        yield {"type": "token", "content": full_answer}

    yield {"type": "done", "answer": full_answer, "model": model_used, "usage": usage}
