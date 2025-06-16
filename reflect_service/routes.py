"""API routes for the Reflect service."""

from fastapi import APIRouter, HTTPException

from datetime import datetime
from typing import List
import os
import json
from shared.logger import logger
from schemas import (
    AnchorRequest,
    AnchorResponse,
    ReflectRequest,
    ReflectResponse,
)
from validation import validate_embedding
import openai

OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

router = APIRouter()


@router.post("/anchor", response_model=AnchorResponse)
async def anchor(request: AnchorRequest):
    try:
        anchored, status, summary = await validate_embedding(
            request.pruned_embedding
        )
        response = AnchorResponse(
            uuid=request.uuid,
            anchored_embedding=anchored,
            status=status,
            timestamp=datetime.utcnow(),
            summary=summary,
        )
        logger.info(f"[REFLECT] {request.uuid} => {status} : {summary}")
        return response
    except Exception as e:
        logger.error(f"[REFLECT] Error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/reflect", response_model=List[ReflectResponse])
async def reflect(request: ReflectRequest) -> List[ReflectResponse]:
    """Analyze interpreted sentences with GPT-4o."""

    if not request.sentences:
        raise HTTPException(status_code=400, detail="No sentences provided")

    if not OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="OpenAI API key missing")

    prompt = (
        "Group the following interpreted sentences by time, type, and tags. "
        "Detect anomalies or trends. Provide a confirmed_cause only if it is "
        "explicitly mentioned in a sentence. If no cause is stated, return a "
        "clarifying question. Respond in JSON array using the keys: timestamp, "
        "event, confirmed_cause, next_question."
    )
    joined = "\n".join(request.sentences)
    openai.api_key = OPENAI_API_KEY
    try:
        completion = openai.ChatCompletion.create(
            model=OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt + "\n\n" + joined}],
        )
        content = completion.choices[0].message["content"].strip()
        analysis = json.loads(content)
    except Exception as exc:  # pragma: no cover - network issues
        logger.error(f"[REFLECT] GPT call failed: {exc}")
        raise HTTPException(status_code=500, detail="GPT analysis failed")

    logger.info("[REFLECT] Generated %d pattern(s)", len(analysis))
    return analysis
