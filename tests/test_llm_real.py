import httpx
import pytest

from app.config import get_settings
from app.services.extraction.base import FIELD_NAMES
from app.services.extraction.llm_extractor import LlmExtractor


@pytest.mark.slow
def test_real_ollama_extracts_fields(sample_scan_text):
    settings = get_settings()
    try:
        httpx.get(settings.ollama_base_url, timeout=3)
    except httpx.HTTPError:
        pytest.skip("Ollama n'est pas démarré")

    extractor = LlmExtractor(
        settings.ollama_base_url, settings.ollama_model, settings.ollama_timeout_s
    )
    result = extractor.extract(sample_scan_text)

    assert set(result) == set(FIELD_NAMES)
    filled = [name for name, champ in result.items() if champ.valeur is not None]
    assert len(filled) >= 3