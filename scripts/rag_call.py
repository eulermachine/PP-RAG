#!/usr/bin/env python3
"""
Simple RAG caller:
 - loads embeddings from `dataset/embeddings.npy` and metadata from `dataset/meta.jsonl`
 - given a query, computes embedding and returns top-k documents (plaintext as 'decrypted')
 - optionally calls Qwen3-max API with retrieved context (API key/endpoint left empty placeholders)

Usage:
 python3 scripts/rag_call.py "your question here"

Note: This script uses `sentence-transformers` locally for query embedding and `requests` for API call.
"""
import os
import sys
import json
import numpy as np
from typing import List, Tuple


def load_meta(meta_path: str) -> List[dict]:
    meta = []
    if not os.path.exists(meta_path):
        return meta
    with open(meta_path, "r", encoding="utf-8") as f:
        for line in f:
            meta.append(json.loads(line))
    return meta


def cosine_sim(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    a_norm = a / (np.linalg.norm(a, axis=1, keepdims=True) + 1e-12)
    b_norm = b / (np.linalg.norm(b) + 1e-12)
    return a_norm.dot(b_norm)


def retrieve(query: str, top_k: int = 3, dataset_dir: str = "dataset", model_name: str = "all-MiniLM-L6-v2") -> List[Tuple[float, dict]]:
    emb_path = os.path.join(dataset_dir, "embeddings.npy")
    meta_path = os.path.join(dataset_dir, "meta.jsonl")
    if not os.path.exists(emb_path):
        raise FileNotFoundError(f"Embeddings not found at {emb_path}; run scripts/embed_documents.py first")

    embeddings = np.load(emb_path)
    meta = load_meta(meta_path)

    # lazy import to avoid heavy deps on module import
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(model_name)
    q_emb = model.encode([query], convert_to_numpy=True)[0]

    sims = cosine_sim(embeddings, q_emb)
    top_idx = np.argsort(-sims)[:top_k]
    results = [(float(sims[int(i)]), meta[int(i)]) for i in top_idx]
    return results


def call_qwen3(prompt: str, api_key: str = "", endpoint: str = "") -> dict:
    """Call Qwen3-max API. Placeholder: api_key and endpoint must be provided by user."""
    if not api_key or not endpoint:
        print("Qwen3 API key or endpoint not set; returning placeholder response.")
        return {"error": "missing_api_credentials"}
    import requests
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {"model": "qwen3-max", "input": prompt}
    resp = requests.post(endpoint, headers=headers, json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json()


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/rag_call.py \"your question\"")
        return
    query = sys.argv[1]
    results = retrieve(query, top_k=3)
    print("Retrieved (score, meta):")
    for score, m in results:
        print(f"- score={score:.4f}, file={m.get('filename')}")
        print("  excerpt:", m.get('text_excerpt'))

    # build a prompt using retrieved docs
    context = "\n\n".join([m.get("text_excerpt", "") for _, m in results])
    prompt = f"Use the following context to answer the question:\nContext:\n{context}\nQuestion: {query}\nAnswer:"

    # placeholder: user must fill these
    API_KEY = ""  # <-- fill in your Qwen3 API key
    ENDPOINT = ""  # <-- fill in the Qwen3 endpoint URL

    answer = call_qwen3(prompt, api_key=API_KEY, endpoint=ENDPOINT)
    print("Qwen3 response:", answer)


if __name__ == "__main__":
    main()
