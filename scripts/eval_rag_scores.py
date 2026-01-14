#!/usr/bin/env python3
"""
Evaluate RAG retrieval outputs with simple BLEU (corpus-level cum. 1-4 gram) and ROUGE-L (LCS-based) scores.
Loads question/reference pairs from a JSONL `--pairs` file or uses a small default sample.
For each question, calls the `retrieve` function from `scripts/rag_call.py` (loaded dynamically) to get top-k retrieved excerpts,
then uses the concatenated excerpts as the hypothesis. Outputs results to `results/eval_rag_scores.json`.

Usage:
  python3 scripts/eval_rag_scores.py --pairs path/to/pairs.jsonl --out results --top-k 3

Output:
  - results/eval_rag_scores.json

Note: Running this script will import and execute code from `scripts/rag_call.py` (it may require heavy ML packages).
"""
import os
import sys
import json
import argparse
import math
import importlib.util
from typing import List, Tuple


# --- simple BLEU (corpus-level, cumulative 1-4 gram) ---

def ngram_counts(tokens: List[str], n: int):
    counts = {}
    for i in range(len(tokens) - n + 1):
        g = tuple(tokens[i : i + n])
        counts[g] = counts.get(g, 0) + 1
    return counts


def clipped_counts_sum(ref_tokens_list: List[List[str]], hyp_tokens: List[str], n: int):
    hyp_counts = ngram_counts(hyp_tokens, n)
    max_ref_counts = {}
    for ref in ref_tokens_list:
        ref_counts = ngram_counts(ref, n)
        for g, c in ref_counts.items():
            max_ref_counts[g] = max(max_ref_counts.get(g, 0), c)
    clipped = 0
    for g, c in hyp_counts.items():
        clipped += min(c, max_ref_counts.get(g, 0))
    return clipped, sum(hyp_counts.values())


def corpus_bleu(references: List[List[str]], hypotheses: List[List[str]], max_n=4):
    # references: list of lists of reference tokens per example (taking only first ref per example for simplicity)
    # hypotheses: list of hypothesis tokens per example
    # Build corpus-level ngram clipped counts and total hyp ngram counts
    weights = [1.0 / max_n] * max_n
    clipped_counts = [0] * max_n
    total_counts = [0] * max_n
    ref_length = 0
    hyp_length = 0
    for refs, hyp in zip(references, hypotheses):
        # refs: list of reference token lists (we allow list-of-lists inside), but for now refs is list with single ref
        ref_tokens_list = refs
        for n in range(1, max_n + 1):
            c, tot = clipped_counts_sum(ref_tokens_list, hyp, n)
            clipped_counts[n - 1] += c
            total_counts[n - 1] += tot
        # choose reference length as closest ref length (only 1 ref supported per example here)
        ref_length += min((len(r) for r in ref_tokens_list), default=0)
        hyp_length += len(hyp)

    precisions = []
    for i in range(max_n):
        if total_counts[i] == 0:
            precisions.append(0.0)
        else:
            precisions.append(clipped_counts[i] / total_counts[i])

    # geometric mean of precisions
    if min(precisions) > 0:
        log_prec = sum((weights[i] * math.log(precisions[i]) for i in range(max_n)))
        geo_mean = math.exp(log_prec)
    else:
        geo_mean = 0.0

    # brevity penalty
    if hyp_length == 0:
        bp = 0.0
    elif hyp_length > ref_length:
        bp = 1.0
    else:
        bp = math.exp(1 - ref_length / hyp_length) if hyp_length > 0 else 0.0

    bleu = bp * geo_mean
    return bleu * 100.0  # return as percentage


# --- ROUGE-L implementation (per-example F1) ---

def lcs(a: List[str], b: List[str]) -> int:
    # classic dynamic programming LCS length
    m, n = len(a), len(b)
    if m == 0 or n == 0:
        return 0
    dp = [0] * (n + 1)
    for i in range(1, m + 1):
        prev = 0
        for j in range(1, n + 1):
            tmp = dp[j]
            if a[i - 1] == b[j - 1]:
                dp[j] = prev + 1
            else:
                dp[j] = max(dp[j], dp[j - 1])
            prev = tmp
    return dp[n]


def rouge_l_score(ref_tokens: List[str], hyp_tokens: List[str]) -> float:
    if len(ref_tokens) == 0 or len(hyp_tokens) == 0:
        return 0.0
    lcs_len = lcs(ref_tokens, hyp_tokens)
    prec = lcs_len / len(hyp_tokens)
    rec = lcs_len / len(ref_tokens)
    if prec + rec == 0:
        return 0.0
    f1 = (2 * prec * rec) / (prec + rec)
    return f1 * 100.0


# --- utility: dynamic load retrieve from scripts/rag_call.py ---

def load_retrieve_func(script_path: str = "scripts/rag_call.py"):
    if not os.path.exists(script_path):
        raise FileNotFoundError(f"{script_path} not found")
    spec = importlib.util.spec_from_file_location("rag_call_module", script_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if not hasattr(mod, "retrieve"):
        raise AttributeError("retrieve function not found in rag_call.py")
    return mod.retrieve


def tokenize(text: str) -> List[str]:
    # simple whitespace tokenizer; lowercase
    return text.lower().split()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pairs", help="jsonl with {question, reference}", default=None)
    parser.add_argument("--out", help="results dir", default="results")
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--dataset-dir", default="dataset")
    parser.add_argument("--model", default="all-MiniLM-L6-v2")
    parser.add_argument("--max-examples", type=int, default=50)
    args = parser.parse_args()

    os.makedirs(args.out, exist_ok=True)

    # load question-reference pairs
    pairs = []
    if args.pairs and os.path.exists(args.pairs):
        with open(args.pairs, "r", encoding="utf-8") as f:
            for line in f:
                obj = json.loads(line)
                if "question" in obj and "reference" in obj:
                    pairs.append((obj["question"], obj["reference"]))
    else:
        # fallback: small default pair using sample doc if available
        sample_doc = None
        sample_path = os.path.join(args.dataset_dir, "docs", "sample_doc1.txt")
        if os.path.exists(sample_path):
            with open(sample_path, "r", encoding="utf-8") as f:
                sample_doc = f.read().strip()
        if sample_doc:
            pairs = [("What is this document about?", sample_doc)]
        else:
            print("No pairs file provided and no sample doc found. Exiting.")
            return

    # load retrieve function
    try:
        retrieve = load_retrieve_func(os.path.join("scripts", "rag_call.py"))
    except Exception as e:
        print("Failed to load retrieve function:", e)
        return

    references_tokens = []
    hypotheses_tokens = []
    per_example = []

    for i, (q, ref) in enumerate(pairs[: args.max_examples]):
        print(f"[{i+1}] Query: {q}")
        try:
            results = retrieve(q, top_k=args.top_k, dataset_dir=args.dataset_dir, model_name=args.model)
        except Exception as e:
            print("retrieve() failed:", e)
            return
        # build hypothesis as concatenation of retrieved excerpts
        hyp_texts = [r[1].get("text_excerpt", "") for r in results]
        hypothesis = "\n\n".join(hyp_texts).strip()
        references = [ref]

        ref_toks = [tokenize(ref)]
        hyp_toks = tokenize(hypothesis)

        references_tokens.append(ref_toks)
        hypotheses_tokens.append(hyp_toks)

        bleu = None
        rouge_l = rouge_l_score(ref_toks[0], hyp_toks)

        per_example.append({
            "question": q,
            "reference": ref,
            "hypothesis": hypothesis,
            "rouge_l": rouge_l,
        })
        print(f"  Retrieved top-{args.top_k}, ROUGE-L={rouge_l:.2f}")

    # compute corpus BLEU
    bleu = corpus_bleu(references_tokens, hypotheses_tokens)
    # compute average ROUGE-L
    avg_rouge = sum(x["rouge_l"] for x in per_example) / max(1, len(per_example))

    out = {
        "num_examples": len(per_example),
        "bleu": bleu,
        "avg_rouge_l": avg_rouge,
        "per_example": per_example,
    }

    out_path = os.path.join(args.out, "eval_rag_scores.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print("Wrote results to", out_path)
    print(f"BLEU: {bleu:.2f}, ROUGE-L (avg): {avg_rouge:.2f}")


if __name__ == "__main__":
    import argparse
    main()
