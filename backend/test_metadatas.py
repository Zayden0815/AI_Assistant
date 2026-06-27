import json

with open(
    r"D:\11\AI_ASSISTANT\faissDB\ISO26262_FAISS_QWEN3\metadatas.jsonl",
    encoding="utf-8"
) as f:

    for i in range(5):
        print(json.loads(next(f)))