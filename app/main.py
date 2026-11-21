from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes_documents import router as documents_router
from app.api.routes_extraction import router as extraction_router
from app.api.routes_health import router as health_router
from app.api.routes_ocr import router as ocr_router
from app.api.routes_controls import router as controls_router
from app.config import get_settings
from app.db.connection import Database
from app.services.extraction.llm_extractor import LlmExtractor
from app.services.extraction.pipeline import ExtractionPipeline
from app.services.extraction.regex_extractor import RegexExtractor
from app.services.ocr.docling_engine import DoclingEngine


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    settings.storage_path.mkdir(parents=True, exist_ok=True)
    db = Database(settings)
    db.open()
    app.state.db = db
    app.state.ocr_engine = DoclingEngine()

    fallbacks = []
    if settings.llm_enabled:
        fallbacks.append(
            LlmExtractor(
                settings.ollama_base_url,
                settings.ollama_model,
                settings.ollama_timeout_s,
            )
        )
    app.state.extraction_pipeline = ExtractionPipeline(RegexExtractor(), fallbacks)

    yield
    db.close()


app = FastAPI(
    title="Factures IA",
    description="Réception, OCR et extraction de factures fournisseurs",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(health_router)
app.include_router(documents_router)
app.include_router(ocr_router)
app.include_router(extraction_router)
app.include_router(controls_router)