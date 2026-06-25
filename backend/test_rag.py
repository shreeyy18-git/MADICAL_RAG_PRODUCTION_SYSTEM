import asyncio
from app.services.graph import run_rag_workflow
from app.config import get_settings

async def main():
    print("Testing RAG workflow")
    resp = await run_rag_workflow("550e8400-e29b-41d4-a716-446655440000", None, "hello")
    print(resp)

if __name__ == "__main__":
    asyncio.run(main())
