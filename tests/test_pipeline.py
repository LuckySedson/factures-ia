from app.services.extraction.base import FIELD_NAMES, FieldExtractor, FieldValue
from app.services.extraction.pipeline import ExtractionPipeline


def all_fields(confiance, methode, valeur="x"):
    return {name: FieldValue(valeur, confiance, methode) for name in FIELD_NAMES}


class StubExtractor(FieldExtractor):
    def __init__(self, fields):
        self.fields = fields
        self.calls = 0

    def extract(self, text):
        self.calls += 1
        return dict(self.fields)


def test_fallback_improves_low_confidence_fields():
    primary = all_fields(0.9, "regex")
    primary["tva"] = FieldValue(None, 0.0, "regex")
    fallback = StubExtractor(all_fields(0.7, "llm", valeur="y"))
    result = ExtractionPipeline(StubExtractor(primary), [fallback]).run("texte")
    assert result["tva"].methode == "llm"
    assert result["numero_facture"].methode == "regex"


def test_fallback_not_called_when_primary_is_confident():
    fallback = StubExtractor(all_fields(1.0, "llm"))
    ExtractionPipeline(StubExtractor(all_fields(0.9, "regex")), [fallback]).run("texte")
    assert fallback.calls == 0