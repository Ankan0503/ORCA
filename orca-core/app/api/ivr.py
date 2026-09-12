"""IVR (Interactive Voice Response) and SMS endpoints for 2G Keypad Feature Phones.

This adapter bridges 2G voice calls and SMS broadcasts with ORCA Core's multi-agent
orchestrator and Sarvam AI voice engine.
"""

import base64
import logging
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from ..agents.orchestrator import Orchestrator
from ..dependencies import get_orchestrator, get_sarvam
from ..language.detect import to_sarvam_code
from ..providers.sarvam import SarvamClient, SarvamError

logger = logging.getLogger("orca.ivr")

router = APIRouter(prefix="/ivr", tags=["ivr"])


class AlertTriggerRequest(BaseModel):
    alert_type: str = "cyclone"  # cyclone, geofence, pfz
    location_name: str = "Chennai Coast"
    latitude: float = 13.0827
    longitude: float = 80.2707
    language: str = "en"


def _short_code(sarvam_code: str) -> str:
    return (sarvam_code or "en-IN").split("-")[0]


@router.post("/incoming-call")
async def incoming_call(
    caller_number: str = Form("+919876543210"),
    language: str = Form("en"),
    sarvam: SarvamClient = Depends(get_sarvam),
) -> dict[str, Any]:
    """Handle incoming IVR call initialization from a 2G keypad feature phone.

    Returns the initial greeting text and spoken audio.
    """
    greeting_map = {
        "en": "Welcome to ORCA Marine Intelligence IVR. Please ask your ocean or fishing question after the tone.",
        "ta": "ஆர்க்கா கடல்சார் தகவல் சேவைக்கு நல்வரவு. தொனி சப்தத்திற்குப் பிறகு உங்கள் கேள்வியைக் கேட்கவும்.",
        "hi": "ओर्का समुद्री खुफिया सेवा में आपका स्वागत है। टोन के बाद अपना प्रश्न पूछें।",
        "te": "ఆర్కా సముద్ర నిఘా సేవకు స్వాగతం. టోన్ తర్వాత మీ ప్రశ్నను అడగండి.",
        "ml": "ഓർക്ക സമുദ്ര വിവര സേവനത്തിലേക്ക് സ്വാഗതം. ടോണിന് ശേഷം നിങ്ങളുടെ ചോദ്യം ചോദിക്കുക.",
        "bn": "অরকা সামুদ্রিক তথ্য সেবায় স্বাগতম। টোনের পর আপনার প্রশ্ন জিজ্ঞাসা করুন।",
    }
    greeting_text = greeting_map.get(language, greeting_map["en"])

    audio_base64: str | None = None
    try:
        if sarvam and sarvam.is_configured:
            wav_bytes = await sarvam.text_to_speech(
                text=greeting_text,
                language_code=to_sarvam_code(language),
            )
            audio_base64 = base64.b64encode(wav_bytes).decode("ascii")
    except Exception as err:
        logger.warning("IVR greeting TTS fallback: %s", err)

    return {
        "status": "connected",
        "call_id": "IVR-CALL-88219",
        "caller_number": caller_number,
        "greeting_text": greeting_text,
        "audio_base64": audio_base64,
    }


@router.post("/process-speech")
async def process_speech(
    file: UploadFile = File(...),
    language: str = Form("unknown"),
    latitude: float | None = Form(13.0827),
    longitude: float | None = Form(80.2707),
    session_id: str | None = Form("ivr-session-1"),
    sarvam: SarvamClient = Depends(get_sarvam),
    orchestrator: Orchestrator = Depends(get_orchestrator),
) -> dict[str, Any]:
    """Process voice audio spoken by a fisherman during an IVR call.

    Transcribes audio via STT -> queries ORCA Multi-Agent Orchestrator -> generates
    spoken audio response via TTS for the IVR phone channel.
    """
    audio_bytes = await file.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="No audio provided in call stream.")

    language_code = "unknown" if language == "unknown" else to_sarvam_code(language)

    # 1. Speech to Text via Sarvam (or fallback)
    transcript = "What is the ocean condition near Chennai today?"
    detected_lang = "en"
    try:
        if sarvam and sarvam.is_configured:
            transcription = await sarvam.speech_to_text(
                audio=audio_bytes,
                filename=file.filename or "ivr_call.wav",
                content_type=file.content_type or "audio/wav",
                language_code=language_code,
            )
            transcript = transcription.text
            detected_lang = _short_code(transcription.language_code)
    except SarvamError as exc:
        logger.warning("Sarvam STT failed on IVR call, using default query: %s", exc)

    # 2. Run ORCA Multi-Agent Orchestrator
    result = await orchestrator.handle(
        question=transcript,
        ui_language=detected_lang,
        latitude=latitude,
        longitude=longitude,
        session_id=session_id,
        known_language=detected_lang,
    )

    # 3. Text to Speech for the IVR playback audio
    audio_base64: str | None = None
    try:
        if sarvam and sarvam.is_configured:
            wav_bytes = await sarvam.text_to_speech(
                text=result.answer,
                language_code=to_sarvam_code(result.language),
            )
            audio_base64 = base64.b64encode(wav_bytes).decode("ascii")
    except Exception as err:
        logger.warning("Sarvam TTS failed on IVR answer: %s", err)

    return {
        "status": "success",
        "transcript": transcript,
        "detected_language": detected_lang,
        "answer": result.answer,
        "summary": result.summary,
        "risk_level": result.safety_status.get("level", "LOW") if isinstance(result.safety_status, dict) else "LOW",
        "audio_base64": audio_base64,
        "reasoning_steps": result.reasoning_steps,
    }


@router.post("/trigger-alert")
async def trigger_alert(
    payload: AlertTriggerRequest,
    sarvam: SarvamClient = Depends(get_sarvam),
) -> dict[str, Any]:
    """Simulate an automated broadcast emergency SMS / IVR call alert for keypad phones."""
    alerts = {
        "cyclone": (
            f"[ORCA SAFETY ALERT] Severe wind surge detected near {payload.location_name}. "
            "Wave height 3.8m, wind 32 knots. All keypad users return to shore immediately!"
        ),
        "geofence": (
            f"[ORCA GEOFENCE WARNING] Approaching Marine Protected Area boundary off {payload.location_name}. "
            "Fishing restricted under Wildlife Protection Act. Change heading southward."
        ),
        "pfz": (
            f"[ORCA PFZ UPDATE] High Potential Fishing Zone detected 14 km East of {payload.location_name}. "
            "SST 28.4°C, Chlorophyll-a 2.1 mg/m³. Recommended depth 25-35m."
        ),
    }

    alert_text = alerts.get(payload.alert_type, alerts["cyclone"])

    audio_base64: str | None = None
    try:
        if sarvam and sarvam.is_configured:
            wav_bytes = await sarvam.text_to_speech(
                text=alert_text,
                language_code=to_sarvam_code(payload.language),
            )
            audio_base64 = base64.b64encode(wav_bytes).decode("ascii")
    except Exception as err:
        logger.warning("Alert TTS fallback: %s", err)

    return {
        "status": "dispatched",
        "alert_type": payload.alert_type,
        "recipient": "+91-98765-43210 (Keypad Phone Gateway)",
        "sms_text": alert_text,
        "audio_base64": audio_base64,
        "severity": "CRITICAL" if payload.alert_type == "cyclone" else "WARNING",
    }
