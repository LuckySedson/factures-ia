import hashlib
import io
from dataclasses import dataclass
from pathlib import Path, PureWindowsPath

from pypdf import PdfReader

from app.services.errors import FileTooLargeError, UnsupportedFileTypeError

SIGNATURES = (
    (b"%PDF-", "pdf"),
    (b"\x89PNG\r\n\x1a\n", "png"),
    (b"\xff\xd8\xff", "jpg"),
)
MIN_TEXT_CHARS = 20
PDF_PAGES_TO_CHECK = 3
MAX_NAME_LENGTH = 255


@dataclass(frozen=True)
class InspectedFile:
    nom_original: str
    sha256: str
    extension: str
    type_document: str
    size: int


class StorageService:
    def __init__(self, root: Path, max_bytes: int):
        self._root = root
        self._max_bytes = max_bytes

    def inspect(self, content: bytes, original_name: str) -> InspectedFile:
        if len(content) > self._max_bytes:
            limit_mb = self._max_bytes // (1024 * 1024)
            raise FileTooLargeError(
                f"Fichier trop volumineux (maximum {limit_mb} Mo)"
            )
        extension = self._detect_extension(content)
        type_document = (
            self._classify_pdf(content) if extension == "pdf" else "image"
        )
        return InspectedFile(
            nom_original=self._clean_name(original_name),
            sha256=hashlib.sha256(content).hexdigest(),
            extension=extension,
            type_document=type_document,
            size=len(content),
        )

    @staticmethod
    def relative_path(info: InspectedFile) -> str:
        return f"{info.sha256}.{info.extension}"

    def save(self, content: bytes, info: InspectedFile) -> str:
        relative = self.relative_path(info)
        target = self._root / relative
        self._root.mkdir(parents=True, exist_ok=True)
        temp = target.with_name(target.name + ".tmp")
        temp.write_bytes(content)
        temp.replace(target)
        return relative

    def delete(self, relative_path: str) -> None:
        (self._root / relative_path).unlink(missing_ok=True)

    @staticmethod
    def _detect_extension(content: bytes) -> str:
        for signature, extension in SIGNATURES:
            if content.startswith(signature):
                return extension
        raise UnsupportedFileTypeError(
            "Format non pris en charge (PDF, PNG ou JPEG attendus)"
        )

    @staticmethod
    def _classify_pdf(content: bytes) -> str:
        try:
            reader = PdfReader(io.BytesIO(content))
            total = len(reader.pages)
            if total == 0:
                raise ValueError("PDF sans page")
            text = "".join(
                reader.pages[i].extract_text() or ""
                for i in range(min(total, PDF_PAGES_TO_CHECK))
            )
        except Exception as exc:
            raise UnsupportedFileTypeError("PDF illisible ou corrompu") from exc
        return "pdf_texte" if len(text.strip()) >= MIN_TEXT_CHARS else "pdf_scan"

    @staticmethod
    def _clean_name(original_name: str) -> str:
        name = PureWindowsPath(original_name or "").name
        return name[:MAX_NAME_LENGTH] or "sans_nom"