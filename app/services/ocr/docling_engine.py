import threading
import time
from pathlib import Path

from app.services.errors import OcrError
from app.services.ocr.base import OcrEngine, OcrResult


class DoclingEngine(OcrEngine):
    name = "docling"

    def __init__(self):
        self._converter = None
        self._lock = threading.Lock()

    def warm_up(self) -> None:
        with self._lock:
            self._get_converter()

    def extract(self, path: Path) -> OcrResult:
        with self._lock:
            started = time.perf_counter()
            try:
                result = self._get_converter().convert(path)
                text = result.document.export_to_markdown()
            except Exception as exc:
                raise OcrError(f"Échec de l'OCR Docling : {exc}") from exc
            elapsed = int((time.perf_counter() - started) * 1000)
        return OcrResult(text=text, engine=self.name, duration_ms=elapsed)

    def _get_converter(self):
        if self._converter is None:
            from docling.document_converter import DocumentConverter

            self._converter = DocumentConverter()
        return self._converter