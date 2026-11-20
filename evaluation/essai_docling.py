import sys
import time
from pathlib import Path

from docling.document_converter import DocumentConverter

DEFAULT_FILES = [
    "data/tests/facture_propre_001.pdf",
    "data/tests/facture_scan_002.jpg",
]


def main(paths: list[str]) -> None:
    converter = DocumentConverter()
    for raw in paths:
        path = Path(raw)
        started = time.perf_counter()
        result = converter.convert(path)
        elapsed = time.perf_counter() - started
        print(f"=== {path.name} ({elapsed:.1f} s)")
        print(result.document.export_to_markdown())
        print()


if __name__ == "__main__":
    main(sys.argv[1:] or DEFAULT_FILES)