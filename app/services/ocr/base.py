from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class OcrResult:
    text: str
    engine: str
    duration_ms: int


class OcrEngine(ABC):
    name: str

    @abstractmethod
    def extract(self, path: Path) -> OcrResult:
        ...