from collections.abc import Sequence

from app.services.extraction.base import FIELD_NAMES, FieldExtractor, FieldValue


class ExtractionPipeline:
    def __init__(
        self,
        primary: FieldExtractor,
        fallbacks: Sequence[FieldExtractor] = (),
        threshold: float = 0.8,
    ):
        self._primary = primary
        self._fallbacks = tuple(fallbacks)
        self._threshold = threshold

    def run(self, text: str) -> dict[str, FieldValue]:
        result = dict(self._primary.extract(text))
        for extractor in self._fallbacks:
            if all(result[name].confiance >= self._threshold for name in FIELD_NAMES):
                break
            candidate = extractor.extract(text)
            for name in FIELD_NAMES:
                if candidate[name].confiance > result[name].confiance:
                    result[name] = candidate[name]
        return result