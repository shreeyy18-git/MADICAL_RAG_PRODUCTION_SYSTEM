"""
Offline evaluation, run locally -- never deploy this to Render. Install
the separate eval dependencies first:

    pip install -r requirements-eval.txt

Usage:
    python scripts/evaluate_ragas.py eval_questions.json

eval_questions.json format:
[
  {"question": "What are the symptoms of Type 2 diabetes?", "ground_truth": "..."},
  ...
]
"""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from datasets import Dataset  # noqa: E402
from ragas import evaluate  # noqa: E402
from ragas.metrics import (  # noqa: E402
    answer_relevancy,
    context_precision,
    context_recall,
    faithfulness,
)

from app.services import llm, retrieval  # noqa: E402


async def run_pipeline(question: str) -> tuple[str, list[str]]:
    chunks = await retrieval.retrieve(question)
    context_block = "\n\n".join(c["chunk_text"] for c in chunks)
    messages = [
        {
            "role": "system",
            "content": "Answer the question using only the provided context.",
        },
        {"role": "user", "content": f"Context:\n{context_block}\n\nQuestion: {question}"},
    ]
    answer, _, _ = await llm.generate(messages)
    return answer, [c["chunk_text"] for c in chunks]


async def build_eval_dataset(questions_path: str) -> Dataset:
    items = json.loads(Path(questions_path).read_text())
    rows = {"question": [], "answer": [], "contexts": [], "ground_truth": []}
    for item in items:
        answer, contexts = await run_pipeline(item["question"])
        rows["question"].append(item["question"])
        rows["answer"].append(answer)
        rows["contexts"].append(contexts)
        rows["ground_truth"].append(item.get("ground_truth", ""))
    return Dataset.from_dict(rows)


def main(questions_path: str) -> None:
    dataset = asyncio.run(build_eval_dataset(questions_path))
    result = evaluate(
        dataset,
        metrics=[faithfulness, context_precision, context_recall, answer_relevancy],
    )
    print(result)
    result.to_pandas().to_csv("ragas_results.csv", index=False)
    print("Saved detailed results to ragas_results.csv")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python scripts/evaluate_ragas.py eval_questions.json")
        sys.exit(1)
    main(sys.argv[1])
