"""TTS API endpoints for lazy audio retrieval."""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse

from app.api.v1.auth import get_current_session
from app.models.session import Session
from app.services.tts_audio_cache import tts_audio_cache

router = APIRouter()


@router.get("/{audio_id}")
async def get_tts_audio(
    audio_id: str,
    session: Session = Depends(get_current_session),
):
    """Fetch generated TTS audio for the given audio_id.

    Returns:
    - 202 + {status: "pending"} while audio is still generating
    - 200 + {status: "ready", audio_base64: "..."} when available
    - 404 if not found / not owned by session
    - 500 + {status: "failed"} if generation failed (still not exposing internal error)
    """
    entry = tts_audio_cache.get(audio_id)
    if entry is None or entry.session_id != session.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audio not found")

    if entry.status == "pending":
        return JSONResponse(status_code=status.HTTP_202_ACCEPTED, content=entry.to_api_payload())

    if entry.status == "failed":
        # Keep semantics explicit for the client, but avoid leaking details.
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=entry.to_api_payload())

    return entry.to_api_payload()

