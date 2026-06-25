import asyncio
from app.services.llm import generate

async def test():
    messages = [{"role": "user", "content": "hi"}]
    try:
        ans, model, usage = await generate(messages)
        print("generate OK:", ans, model, usage)
    except Exception as e:
        print("generate ERROR:", type(e), e)

if __name__ == "__main__":
    asyncio.run(test())
