#!/usr/bin/env python3
"""
Embed all .txt documents in `dataset/docs/` and save embeddings + metadata to `dataset/`.
Output:
 - dataset/embeddings.npy
 - dataset/meta.jsonl  (one JSON per line with keys: filename, text)

Usage:
 python3 scripts/embed_documents.py --input dataset/docs --out dataset --model all-MiniLM-L6-v2
"""
import os
import argparse
import json
import glob
import numpy as np


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="dataset/docs", help="input docs dir")
    parser.add_argument("--out", default="dataset", help="output dataset dir")
    parser.add_argument("--model", default="all-MiniLM-L6-v2", help="sentence-transformers model")
    args = parser.parse_args()

    os.makedirs(args.out, exist_ok=True)
    txts = []
    metas = []
    files = sorted(glob.glob(os.path.join(args.input, "*.txt")))
    for i, p in enumerate(files):
        with open(p, "r", encoding="utf-8") as f:
            text = f.read().strip()
        txts.append(text)
        metas.append({"id": i, "filename": os.path.basename(p), "text_excerpt": text[:500]})

    if not txts:
        print("No .txt files found in", args.input)
        return

    # Import here to avoid forcing heavy deps on module import
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(args.model)
    embs = model.encode(txts, batch_size=64, convert_to_numpy=True, show_progress_bar=True)

    emb_path = os.path.join(args.out, "embeddings.npy")
    meta_path = os.path.join(args.out, "meta.jsonl")

    np.save(emb_path, embs)
    with open(meta_path, "w", encoding="utf-8") as f:
        for m in metas:
            f.write(json.dumps(m, ensure_ascii=False) + "\n")

    print("Saved:")
    print(" -", emb_path)
    print(" -", meta_path)


if __name__ == "__main__":
    main()
