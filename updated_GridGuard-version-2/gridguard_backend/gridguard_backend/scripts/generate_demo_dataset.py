"""Generate a safe, synthetic CSV for GridGuard demonstrations.

Usage:
    python scripts/generate_demo_dataset.py

The generated file is written to ``data/demo/gridguard_demo.csv`` and is
intended for upload through the Datasets page. It contains 60 consumers,
35 daily readings, three feeders, and 12 labelled suspicious patterns.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_use_cases import make_demo_csv  # noqa: E402


def main():
    output = Path(__file__).resolve().parent.parent / "data" / "demo" / "gridguard_demo.csv"
    output.parent.mkdir(parents=True, exist_ok=True)
    make_demo_csv(output)
    print(f"Created {output} (60 consumers, 35 days, 3 feeders)")


if __name__ == "__main__":
    main()
