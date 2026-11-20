import json

import httpx

from app.services.extraction.base import FIELD_NAMES
from app.services.extraction.llm_extractor import LlmExtractor
from app.services.extraction.pipeline import ExtractionPipeline
from app.services.extraction.regex_extractor import RegexExtractor


def make_extractor(handler):
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return LlmExtractor("http://ollama.test", "modele-test", timeout_s=5, client=client)


def answer(**fields):
    payload = {name: None for name in FIELD_NAMES}
    payload.update(fields)

    def handler(request):
        return httpx.Response(
            200, json={"message": {"role": "assistant", "content": json.dumps(payload)}}
        )

    return handler


def assert_all_missing(result):
    assert set(result) == set(FIELD_NAMES)
    assert all(champ.valeur is None and champ.confiance == 0.0 for champ in result.values())


def test_grounded_answer_gets_good_confidence(sample_scan_text):
    seen = {}
    reply = answer(
        fournisseur="Librairie Universitaire",
        numero_facture="FAC-2026-002",
        date_facture="2026-11-16",
        montant_ttc="50000",
    )

    def handler(request):
        seen["body"] = json.loads(request.content)
        return reply(request)

    result = make_extractor(handler).extract(sample_scan_text)

    assert result["montant_ttc"].valeur == "50000.00"
    assert result["montant_ttc"].confiance == 0.75
    assert result["montant_ttc"].methode == "llm"
    assert result["fournisseur"].confiance == 0.75
    assert result["date_facture"].valeur == "2026-11-16"
    assert result["montant_ht"].valeur is None
    body = seen["body"]
    assert body["model"] == "modele-test"
    assert body["stream"] is False
    assert body["options"]["temperature"] == 0
    assert "properties" in body["format"]


def test_ungrounded_value_gets_low_confidence(sample_scan_text):
    result = make_extractor(answer(montant_ttc="99999")).extract(sample_scan_text)
    assert result["montant_ttc"].valeur == "99999.00"
    assert result["montant_ttc"].confiance == 0.3


def test_separated_amount_is_parsed(sample_fr_text):
    result = make_extractor(answer(montant_ht="1 250 000,50 Ar")).extract(sample_fr_text)
    assert result["montant_ht"].valeur == "1250000.50"
    assert result["montant_ht"].confiance == 0.75


def test_http_error_returns_all_missing(sample_scan_text):
    extractor = make_extractor(lambda request: httpx.Response(500, text="erreur"))
    assert_all_missing(extractor.extract(sample_scan_text))


def test_invalid_json_returns_all_missing(sample_scan_text):
    extractor = make_extractor(
        lambda request: httpx.Response(200, json={"message": {"content": "pas du json"}})
    )
    assert_all_missing(extractor.extract(sample_scan_text))


def test_connection_error_returns_all_missing(sample_scan_text):
    def handler(request):
        raise httpx.ConnectError("connexion refusée")

    assert_all_missing(make_extractor(handler).extract(sample_scan_text))


def test_llm_repairs_garbled_scan(sample_scan_text):
    reply = answer(
        fournisseur="Librairie Universitaire",
        numero_facture="FAC-2026-002",
        date_facture="2026-11-16",
        montant_ttc="50000",
    )
    pipeline = ExtractionPipeline(RegexExtractor(), [make_extractor(reply)])
    result = pipeline.run(sample_scan_text)

    assert result["montant_ttc"].valeur == "50000.00"
    assert result["montant_ttc"].methode == "llm"
    assert result["numero_facture"].methode == "llm"
    assert result["fournisseur"].methode == "regex"
    assert result["montant_ht"].valeur is None


def test_llm_not_called_for_confident_pdf(sample_pdf_text):
    calls = []

    def handler(request):
        calls.append(request)
        return answer()(request)

    pipeline = ExtractionPipeline(RegexExtractor(), [make_extractor(handler)])
    result = pipeline.run(sample_pdf_text)

    assert calls == []
    assert result["montant_ttc"].methode == "regex"