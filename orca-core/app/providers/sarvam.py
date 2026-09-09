"""Sarvam AI client — speech-to-text, text-to-speech and translation.

Sarvam handles the language edges of ORCA: turning a fisherman's spoken
question into text, and turning ORCA's answer back into speech in the same
language. Endpoints and field names verified against docs.sarvam.ai.

Everything sits behind this one class so a second provider (Bhashini,
IndicTrans2, Whisper) can be slotted in later without touching callers.
"""

import base64
from dataclasses import dataclass

import httpx

from ..config import Settings

# Sarvam authenticates with this header rather than a bearer token.
_AUTH_HEADER = "api-subscription-key"


def _clean_content_type(content_type: str | None) -> str:
    """Strip MIME parameters before handing the type to Sarvam.

    Browsers report recorded audio as `audio/webm;codecs=opus`, and Sarvam
    matches the content type against an exact allowlist — the `;codecs=...`
    parameter makes it reject the upload with a 400, even though it decodes the
    identical bytes happily when the type is plain `audio/webm`. So the
    parameters are dropped here rather than trusting every client to do it.
    """
    if not content_type:
        return "application/octet-stream"
    base = content_type.split(";", 1)[0].strip().lower()
    return base or "application/octet-stream"


class SarvamError(RuntimeError):
    """Raised when Sarvam rejects a request or is unreachable."""


@dataclass
class Transcription:
    text: str
    language_code: str
    confidence: float | None = None


class SarvamClient:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    @property
    def available(self) -> bool:
        return self._settings.has_sarvam

    def _headers(self) -> dict[str, str]:
        if not self.available:
            raise SarvamError("SARVAM_API_KEY is not set")
        return {_AUTH_HEADER: self._settings.sarvam_api_key}

    async def speech_to_text(
        self,
        audio: bytes,
        filename: str = "audio.wav",
        content_type: str = "audio/wav",
        language_code: str = "unknown",
        mode: str = "transcribe",
    ) -> Transcription:
        """Transcribe speech, keeping the speaker's own language and words.

        `language_code="unknown"` asks Sarvam to identify the language itself,
        which is how ORCA detects language on the voice path — no separate
        detector needed.

        `mode="transcribe"` deliberately keeps the original language rather
        than `"translate"`, which would return English and throw away the
        exact words the fisherman used.
        """
        data = {
            "model": self._settings.sarvam_stt_model,
            "language_code": language_code,
            "mode": mode,
        }

        async with httpx.AsyncClient(timeout=self._settings.request_timeout_seconds) as client:
            response = await client.post(
                f"{self._settings.sarvam_base_url}/speech-to-text",
                headers=self._headers(),
                files={"file": (filename, audio, _clean_content_type(content_type))},
                data=data,
            )

        if response.status_code >= 400:
            raise SarvamError(f"speech-to-text failed ({response.status_code}): {response.text}")

        payload = response.json()
        return Transcription(
            text=payload.get("transcript", ""),
            language_code=payload.get("language_code") or language_code,
            confidence=payload.get("language_probability"),
        )

    async def text_to_speech(
        self,
        text: str,
        language_code: str,
        speaker: str = "ritu",
    ) -> bytes:
        """Speak `text` in `language_code`, returning decoded WAV bytes."""
        body = {
            "text": text,
            "target_language_code": language_code,
            "model": self._settings.sarvam_tts_model,
            "speaker": speaker,
        }

        async with httpx.AsyncClient(timeout=self._settings.request_timeout_seconds) as client:
            response = await client.post(
                f"{self._settings.sarvam_base_url}/text-to-speech",
                headers={**self._headers(), "Content-Type": "application/json"},
                json=body,
            )

        if response.status_code >= 400:
            raise SarvamError(f"text-to-speech failed ({response.status_code}): {response.text}")

        audios = response.json().get("audios") or []
        if not audios:
            raise SarvamError("text-to-speech returned no audio")

        # The API returns base64 chunks; concatenating the decoded bytes gives
        # the complete clip.
        return b"".join(base64.b64decode(chunk) for chunk in audios)

    async def translate(
        self,
        text: str,
        target_language_code: str,
        source_language_code: str = "auto",
    ) -> str:
        """Translate text. `source_language_code="auto"` lets Sarvam detect it."""
        body = {
            "input": text,
            "source_language_code": source_language_code,
            "target_language_code": target_language_code,
            "model": self._settings.sarvam_translate_model,
        }

        async with httpx.AsyncClient(timeout=self._settings.request_timeout_seconds) as client:
            response = await client.post(
                f"{self._settings.sarvam_base_url}/translate",
                headers={**self._headers(), "Content-Type": "application/json"},
                json=body,
            )

        if response.status_code >= 400:
            raise SarvamError(f"translate failed ({response.status_code}): {response.text}")

        return response.json().get("translated_text", "")
