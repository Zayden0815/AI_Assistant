import os
import re
import json
import shutil
from pathlib import Path

import fitz
import faiss
import numpy as np
from tqdm import tqdm
from sentence_transformers import SentenceTransformer


BASE_DIR = Path(r"D:\11\AI_ASSISTANT")

PDF_PATH = BASE_DIR / "data" / "iso26262.pdf"

FAISS_DIR = BASE_DIR / "faissDB" / "ISO26262_FAISS_QWEN3"
INDEX_PATH = FAISS_DIR / "index.faiss"
TEXT_PATH = FAISS_DIR / "texts.jsonl"
META_PATH = FAISS_DIR / "metadatas.jsonl"
CONFIG_PATH = FAISS_DIR / "config.json"

EMBEDDING_MODEL = "Qwen/Qwen3-Embedding-4B"

CHUNK_SIZE = 1200
CHUNK_OVERLAP = 250

MIN_PAGE_TEXT_LEN = 80
MIN_CHUNK_TEXT_LEN = 120

NOISE_KEYWORDS = [
    "copyright",
    "all rights reserved",
    "provided by ihs",
    "not for resale",
    "no reproduction or networking permitted",
    "iso copyright office",
    "published in switzerland",
    "price based on",
    "www.iso.org",
    "reference number",
    "international standard",
    "foreword",
    "contents",
    "table of contents",
]

DOMAIN_KEYWORDS = {
    "Part 3 - Concept Phase": [
        "hazard analysis",
        "risk assessment",
        "hara",
        "safety goal",
        "asil determination",
        "controllability",
        "exposure",
        "severity",
    ],
    "Part 4 - System Development": [
        "system level",
        "technical safety requirement",
        "system integration",
        "system testing",
        "item integration",
    ],
    "Part 5 - Hardware Development": [
        "hardware safety requirement",
        "hardware integration",
        "hardware architectural metrics",
        "fault injection",
        "diagnostic coverage",
        "random hardware failure",
    ],
    "Part 6 - Software Development": [
        "software safety requirement",
        "software unit testing",
        "software integration testing",
        "software architectural design",
        "software verification",
    ],
    "Part 8 - Supporting Processes": [
        "supporting processes",
        "configuration management",
        "change management",
        "verification",
        "documentation",
        "traceability",
        "tool qualification",
    ],
    "Part 9 - ASIL-Oriented Analysis": [
        "asil decomposition",
        "dependent failure analysis",
        "freedom from interference",
        "safety analysis",
        "common cause failure",
        "cascading failure",
    ],
    "Part 11 - Semiconductors": [
        "semiconductor",
        "ip integrator",
        "integrated circuit",
        "semiconductor component",
        "safety mechanism",
        "fault injection",
        "hardware integration tests",
    ],
}


def normalize_for_search(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def clean_text(text: str) -> str:
    if not text:
        return ""

    text = text.replace("\x00", " ")
    text = re.sub(r"--`,.*?---", " ", text)
    text = re.sub(r"`+", " ", text)
    text = re.sub(r"\.{5,}", " ", text)
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def is_noise_text(text: str) -> bool:
    t = normalize_for_search(text)

    if len(t) < MIN_PAGE_TEXT_LEN:
        return True

    noise_hits = sum(1 for kw in NOISE_KEYWORDS if kw in t)

    # 저작권/라이선스 문구가 대부분인 페이지 제거
    if noise_hits >= 2 and len(t) < 1800:
        return True

    # 의미 없는 짧은 footer chunk 제거
    if "not for resale" in t and "no reproduction" in t and len(t) < 2000:
        return True

    return False


def is_noise_chunk(text: str) -> bool:
    t = normalize_for_search(text)

    if len(t) < MIN_CHUNK_TEXT_LEN:
        return True

    noise_hits = sum(1 for kw in NOISE_KEYWORDS if kw in t)

    # 저작권 문구 중심 chunk 제거
    if noise_hits >= 2:
        return True

    # 특수기호/라이선스 footer 중심 chunk 제거
    alpha_count = sum(c.isalpha() for c in t)
    if alpha_count < 80:
        return True

    return False


def extract_pages(pdf_path: Path):
    doc = fitz.open(str(pdf_path))
    pages = []

    for page_no, page in enumerate(doc, start=1):
        text = page.get_text("text")
        text = clean_text(text)

        pages.append(
            {
                "page": page_no,
                "text": text,
            }
        )

    return pages


def guess_part(text: str) -> str:
    t = normalize_for_search(text)

    # 문서 자체가 Part 11이면 기본값은 Part 11
    # 하지만 내용상 ISO26262-5, ISO26262-9 등이 언급되면 해당 Part로 태깅
    if "iso 26262-3" in t or "concept phase" in t:
        return "Part 3 - Concept Phase"
    if "iso 26262-4" in t or "system level" in t:
        return "Part 4 - System Development"
    if "iso 26262-5" in t or "hardware safety requirement" in t:
        return "Part 5 - Hardware Development"
    if "iso 26262-6" in t or "software safety requirement" in t:
        return "Part 6 - Software Development"
    if "iso 26262-8" in t or "supporting processes" in t:
        return "Part 8 - Supporting Processes"
    if "iso 26262-9" in t or "asil decomposition" in t or "dependent failure analysis" in t:
        return "Part 9 - ASIL-Oriented Analysis"
    if "iso 26262-11" in t or "semiconductor" in t or "ip integrator" in t:
        return "Part 11 - Semiconductors"

    # 키워드 기반 보조 분류
    best_part = "Unknown"
    best_score = 0

    for part, keywords in DOMAIN_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in t)
        if score > best_score:
            best_score = score
            best_part = part

    if best_score > 0:
        return best_part

    return "Unknown"


def guess_clause(text: str) -> str:
    # 4.12, 5.3.3.1 같은 clause 추출
    matches = re.findall(r"\b\d{1,2}(?:\.\d+){1,4}\b", text)
    if matches:
        return matches[0]
    return "Unknown"


def guess_title(text: str) -> str:
    # 앞쪽 문장 중 제목처럼 보이는 것 추출
    cleaned = clean_text(text)
    candidates = re.split(r"(?<=[.!?])\s+", cleaned[:500])

    for c in candidates:
        c = c.strip()
        if 20 <= len(c) <= 120:
            return c

    return cleaned[:100]


def extract_keywords(text: str):
    t = normalize_for_search(text)

    keywords = []

    for part_keywords in DOMAIN_KEYWORDS.values():
        for kw in part_keywords:
            if kw in t and kw not in keywords:
                keywords.append(kw)

    return keywords[:10]


def chunk_text(text: str):
    chunks = []
    start = 0

    while start < len(text):
        end = start + CHUNK_SIZE
        chunk = text[start:end].strip()

        if chunk and not is_noise_chunk(chunk):
            chunks.append(chunk)

        start += CHUNK_SIZE - CHUNK_OVERLAP

    return chunks


def build_documents(pages):
    texts = []
    metadatas = []
    skipped_pages = 0
    skipped_chunks = 0

    for page in tqdm(pages, desc="Cleaning and chunking"):
        page_no = page["page"]
        text = page["text"]

        # 앞부분 표지/저작권/목차 강제 제거
        if page_no <= 5:
            skipped_pages += 1
            continue

        if is_noise_text(text):
            skipped_pages += 1
            continue

        chunks = chunk_text(text)

        for idx, chunk in enumerate(chunks):
            if is_noise_chunk(chunk):
                skipped_chunks += 1
                continue

            part = guess_part(chunk)
            clause = guess_clause(chunk)
            title = guess_title(chunk)
            keywords = extract_keywords(chunk)

            texts.append(
                {
                    "text": chunk,
                }
            )

            metadatas.append(
                {
                    "source": "ISO26262",
                    "page": page_no,
                    "part": part,
                    "clause": clause,
                    "title": title,
                    "keywords": keywords,
                    "chunk_index": idx,
                }
            )

    print("Skipped pages:", skipped_pages)
    print("Skipped chunks:", skipped_chunks)
    print("Valid chunks:", len(texts))

    return texts, metadatas


def save_jsonl(path: Path, rows):
    with open(path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def build_faiss():
    if not PDF_PATH.exists():
        raise FileNotFoundError(f"PDF not found: {PDF_PATH}")

    if FAISS_DIR.exists():
        print("Removing old FAISS DB:", FAISS_DIR)
        shutil.rmtree(FAISS_DIR)

    FAISS_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 100)
    print("PDF_PATH:", PDF_PATH)
    print("FAISS_DIR:", FAISS_DIR)
    print("EMBEDDING_MODEL:", EMBEDDING_MODEL)
    print("=" * 100)

    pages = extract_pages(PDF_PATH)

    texts, metadatas = build_documents(pages)

    if not texts:
        raise ValueError("No valid chunks generated.")

    print("Loading Qwen3 embedding model...")
    model = SentenceTransformer(
        EMBEDDING_MODEL,
        trust_remote_code=True,
        device="cpu",
    )

    documents_for_embedding = [row["text"] for row in texts]

    print("Embedding chunks:", len(documents_for_embedding))

    embeddings = model.encode(
        documents_for_embedding,
        batch_size=1,
        show_progress_bar=True,
        normalize_embeddings=True,
    )

    embeddings = np.array(embeddings).astype("float32")

    dim = embeddings.shape[1]

    print("Embedding dim:", dim)

    index = faiss.IndexFlatIP(dim)
    index.add(embeddings)

    faiss.write_index(index, str(INDEX_PATH))

    save_jsonl(TEXT_PATH, texts)
    save_jsonl(META_PATH, metadatas)

    config = {
        "pdf_path": str(PDF_PATH),
        "embedding_model": EMBEDDING_MODEL,
        "chunk_size": CHUNK_SIZE,
        "chunk_overlap": CHUNK_OVERLAP,
        "min_page_text_len": MIN_PAGE_TEXT_LEN,
        "min_chunk_text_len": MIN_CHUNK_TEXT_LEN,
        "embedding_dim": dim,
        "total_chunks": len(texts),
        "faiss_metric": "IndexFlatIP",
        "normalized_embeddings": True,
        "db_type": "faiss_jsonl",
        "index_file": "index.faiss",
        "text_file": "texts.jsonl",
        "metadata_file": "metadatas.jsonl",
    }

    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

    print("=" * 100)
    print("FAISS DB build completed")
    print("Index:", INDEX_PATH)
    print("Texts:", TEXT_PATH)
    print("Metadata:", META_PATH)
    print("Config:", CONFIG_PATH)
    print("Total chunks:", len(texts))
    print("=" * 100)


if __name__ == "__main__":
    build_faiss()