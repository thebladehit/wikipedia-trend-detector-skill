# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy>=1.26", "matplotlib>=3.8", "fpdf2>=2.7.9"]
# ///
"""wiki-interest CLI entry point. Run: uv run scripts/wit.py --help"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from wikitrends.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
