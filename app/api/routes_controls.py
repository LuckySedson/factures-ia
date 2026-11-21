from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_control_service
from app.api.schemas import AnomalyResponse, ControlResponse
from app.services.control_service import ControlService
from app.services.errors import (
    DocumentNotFoundError,
    ExtractionRequiredError,
    FactureLockedError,
)

router = APIRouter(prefix="/documents", tags=["controles"])


@router.post("/{document_id}/controls", response_model=ControlResponse)
def run_controls(
    document_id: int,
    service: ControlService = Depends(get_control_service),
) -> ControlResponse:
    try:
        outcome = service.run(document_id)
    except DocumentNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    except (ExtractionRequiredError, FactureLockedError) as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc

    return ControlResponse(
        document_id=outcome.document_id,
        facture_id=outcome.facture_id,
        statut=outcome.statut,
        score_global=outcome.score_global,
        anomalies=[AnomalyResponse.model_validate(item) for item in outcome.anomalies],
    )