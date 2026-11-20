from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_extraction_service
from app.api.schemas import ChampResponse, ExtractionResponse
from app.services.errors import DocumentNotFoundError, OcrRequiredError
from app.services.extraction_service import ExtractionService

router = APIRouter(prefix="/documents", tags=["extraction"])


@router.post("/{document_id}/extract", response_model=ExtractionResponse)
def run_extraction(
    document_id: int,
    force: bool = False,
    service: ExtractionService = Depends(get_extraction_service),
) -> ExtractionResponse:
    try:
        outcome = service.run(document_id, force=force)
    except DocumentNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    except OcrRequiredError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc

    return ExtractionResponse(
        document_id=outcome.document_id,
        facture_id=outcome.facture_id,
        champs={
            name: ChampResponse.model_validate(champ)
            for name, champ in outcome.champs.items()
        },
        score_global=outcome.score_global,
        deja_realise=outcome.deja_realise,
    )