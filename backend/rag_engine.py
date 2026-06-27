import os
import json
from typing import List, Dict, Any

import numpy as np
import faiss
from sentence_transformers import SentenceTransformer


FAISS_DIR = r"D:\11\AI_ASSISTANT\faissDB\ISO26262_FAISS_QWEN3"

INDEX_PATH = os.path.join(FAISS_DIR, "index.faiss")
TEXT_PATH = os.path.join(FAISS_DIR, "texts.jsonl")
META_PATH = os.path.join(FAISS_DIR, "metadatas.jsonl")
CONFIG_PATH = os.path.join(FAISS_DIR, "config.json")


class ISO26262RAG:
    def __init__(self):
        print("========== RAG DEBUG ==========")
        print("FAISS_DIR:", FAISS_DIR)
        print("INDEX:", INDEX_PATH, os.path.exists(INDEX_PATH))
        print("TEXT:", TEXT_PATH, os.path.exists(TEXT_PATH))
        print("META:", META_PATH, os.path.exists(META_PATH))
        print("CONFIG:", CONFIG_PATH, os.path.exists(CONFIG_PATH))
        print("================================")

        required = [INDEX_PATH, TEXT_PATH, META_PATH, CONFIG_PATH]

        if not all(os.path.exists(p) for p in required):
            raise FileNotFoundError("FAISS DB 파일이 부족합니다. 경로와 파일명을 확인하세요.")

        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            self.config = json.load(f)

        self.embedding_model_name = self.config["embedding_model"]

        print("[RAG] Loading FAISS index...")
        self.index = faiss.read_index(INDEX_PATH)

        print("[RAG] Loading texts...")
        self.documents = self._load_jsonl(TEXT_PATH)

        print("[RAG] Loading metadata...")
        self.metadata = self._load_jsonl(META_PATH)

        if len(self.documents) != len(self.metadata):
            raise ValueError(
                f"documents와 metadata 개수가 다릅니다. "
                f"documents={len(self.documents)}, metadata={len(self.metadata)}"
            )

        print("[RAG] Loading embedding model:", self.embedding_model_name)
        self.model = SentenceTransformer(
            self.embedding_model_name,
            trust_remote_code=True,
            device="cpu"
        )

        print("[RAG] Ready")
        print("Vectors:", self.index.ntotal)
        print("Documents:", len(self.documents))
        print("Embedding dim:", self.config.get("embedding_dim"))

    def _load_jsonl(self, path: str):
        items = []

        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()

                if not line:
                    continue

                items.append(json.loads(line))

        return items

    def _get_text(self, item):
        if isinstance(item, str):
            return item

        if isinstance(item, dict):
            return (
                item.get("text")
                or item.get("content")
                or item.get("document")
                or ""
            )

        return ""

    def search(self, query: str, top_k: int = 5, iso_part: str = "all") -> List[Dict[str, Any]]:
        query_embedding = self.model.encode(
            [query],
            normalize_embeddings=True
        )

        query_embedding = np.array(query_embedding).astype("float32")

        search_k = max(top_k * 5, 20)

        scores, indices = self.index.search(query_embedding, search_k)

        results = []

        for rank, idx in enumerate(indices[0]):
            if idx == -1:
                continue

            text_item = self.documents[idx]
            meta = self.metadata[idx]

            doc = self._get_text(text_item)

            if not doc or len(doc.strip()) < 80:
                continue

            if iso_part != "all":
                part_text = str(meta.get("part", "")).lower().replace(" ", "")
                target = iso_part.lower().replace(" ", "")

                if target not in part_text:
                    continue

            results.append(
                {
                    "rank": len(results) + 1,
                    "score": round(float(scores[0][rank]), 4),
                    "page": meta.get("page", "-"),
                    "part": meta.get("part", "Unknown"),
                    "clause": meta.get("clause", "Unknown"),
                    "content": doc[:1500],
                }
            )

            if len(results) >= top_k:
                break

        return results