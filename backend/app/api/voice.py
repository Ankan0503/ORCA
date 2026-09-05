"""Voice endpoints.

These replace the browser Web Speech API the frontend currently uses, which
only maps Hindi, Bengali and English — Tamil, Telugu and Malayalam silently
fall through to en-US there, so those users' speech comes back as nonsense.
Sarvam handles all of them, and identifies the language itself.

`/voice/ask` is the one the app should call: speak a question, get a spoken
answer back, without the client having to orchestrate three round trips.
"""

import base64

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile

from ..agents.orchestrator import Orchestrator
from ..dependencies import get_orchestrator, get_sarvam
from ..language.detect import to_sarvam_code
from ..providers.sarvam import SarvamClient, SarvamError
from ..schemas import (
    SpeakRequest,
    TranscriptionResponse,
    TranslateRequest,
    TranslateResponse,
)

router = APIRouter(prefix="/voice", tags=["voice"])

# Sarvam returns codes like "bn-IN"; the frontend works in short codes.
def _short_code(sarvam_code: str) -> str:
    return (sarvam_code or "en-IN").split("-")[0]


@router.post("/stt", response_model=TranscriptionResponse)
async def speech_to_text(
    file: UploadFile = File(...),
    language: str = Form("unknown"),
    sarvam: SarvamClient = Depends(get_sarvam),
) -> TranscriptionResponse:
    """Transcribe speech, keeping the speaker's own language and words.

    `language="unknown"` (the default) asks Sarvam to identify the language,
    which is how ORCA detects language on the voice path.
    """
    audio = await file.read()
    if not audio:
        raise HTTPException(status_code=400, detail="Empty audio upload")

    language_code = "unknown" if language == "unknown" else to_sarvam_code(language)

    try:
        result = await sarvam.speech_to_text(
            audio=audio,
            filename=file.filename or "audio.wav",
            content_type=file.content_type or "audio/wav",
            language_code=language_code,
        )
    except SarvamError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return TranscriptionResponse(
        transcript=result.text,
        language=_short_code(result.language_code),
        confidence=result.confidence,
    )


@router.post("/tts")
async def text_to_speech(
    request: SpeakRequest,
    sarvam: SarvamClient = Depends(get_sarvam),
) -> Response:
    """Speak text in the given language, returning WAV audio."""
    try:
        audio = await sarvam.text_to_speech(
            text=request.text,
            language_code=to_sarvam_code(request.language),
            speaker=request.speaker,
        )
    except SarvamError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return Response(content=audio, media_type="audio/wav")


@router.post("/translate", response_model=TranslateResponse)
async def translate(
    request: TranslateRequest,
    sarvam: SarvamClient = Depends(get_sarvam),
) -> TranslateResponse:
    try:
        translated = await sarvam.translate(
            text=request.text,
            target_language_code=to_sarvam_code(request.target_language),
            source_language_code=(
                "auto"
                if request.source_language == "auto"
                else to_sarvam_code(request.source_language)
            ),
        )
    except SarvamError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return TranslateResponse(translated_text=translated)


@router.post("/ask")
async def ask_by_voice(
    file: UploadFile = File(...),
    language: str = Form("unknown"),
    latitude: float | None = Form(None),
    longitude: float | None = Form(None),
    session_id: str | None = Form(None),
    sarvam: SarvamClient = Depends(get_sarvam),
    orchestrator: Orchestrator = Depends(get_orchestrator),
) -> dict:
    """Full voice turn: speech in, reasoned answer out, spoken back.

    The audio is returned base64-encoded alongside the text so the client gets
    the transcript, the answer and the reasoning in a single response.
    """
    audio = await file.read()
    if not audio:
        raise HTTPException(status_code=400, detail="Empty audio upload")

    language_code = "unknown" if language == "unknown" else to_sarvam_code(language)

    try:
        transcription = await sarvam.speech_to_text(
            audio=audio,
            filename=file.filename or "audio.wav",
            content_type=file.content_type or "audio/wav",
            language_code=language_code,
        )
    except SarvamError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    detected = _short_code(transcription.language_code)

    result = await orchestrator.handle(
        question=transcription.text,
        ui_language=detected,
        latitude=latitude,
        longitude=longitude,
        session_id=session_id,
        known_language=detected,
    )

    # Speaking the answer is a bonus; if TTS fails the text answer still stands.
    spoken: str | None = None
    try:
        spoken = base64.b64encode(
            await sarvam.text_to_speech(
                text=result.answer,
                language_code=to_sarvam_code(result.language),
            )
        ).decode("ascii")
    except SarvamError:
        spoken = None

    return {
        "transcript": transcription.text,
        "detected_language": detected,
        "language_confidence": transcription.confidence,
        **result.to_dict(),
        "audio_base64": spoken,
    }
