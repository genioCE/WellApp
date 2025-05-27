from fastapi import APIRouter, HTTPException
from datetime import datetime
from shared.logger import logger
from schemas import AnchorRequest, AnchorResponse
from validation import validate_embedding

router = APIRouter()

@router.post("/anchor", response_model=AnchorResponse)
async def anchor(request: AnchorRequest):
    try:
        anchored, status, summary = await validate_embedding(request.pruned_embedding)
        response = AnchorResponse(
            uuid=request.uuid,
            anchored_embedding=anchored,
            status=status,
            timestamp=datetime.utcnow(),
            summary=summary
        )
        logger.info(f"[REFLECT] {request.uuid} => {status} : {summary}")
        return response
    except Exception as e:
        logger.error(f"[REFLECT] Error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
