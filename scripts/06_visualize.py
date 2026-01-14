#!/usr/bin/env python3
"""
06_visualize.py
Generate visualization figures from existing results
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.python.visualizer import generate_all_figures


def main():
    print("="*60)
    print("PP-RAG HE Benchmark - Visualization")
    print("="*60)
    
    generate_all_figures("./results/timings.json", "./results/figures")


if __name__ == "__main__":
    main()
