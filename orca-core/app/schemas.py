"""Request and response models for the public API."""

from typing import Any

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    # The language the UI is currently showing; used as a prior when the query
    # is written in Latin script.
    language: str | None = None
    # Set when the language is already known from speech recognition, so the
    # orchestrator does not re-guess it from the text. Matters for romanised
    # input, where the script gives nothing away.
    known_language: str | None = None
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    session_id: str | None = None


class EvidenceModel(BaseModel):
    source: str
    label: str
    value: str
    unit: str | None = None
    observed_at: str | None = None
    note: str | None = None


class AgentResultModel(BaseModel):
    agent: str
    summary: str
    evidence: list[EvidenceModel] = []
    confidence: float
    is_stub: bool
    error: str | None = None
    # An agent's own findings in machine-readable form. Without this the
    # visualization agent's chart and the reporting agent's brief are built on
    # the server and then dropped by the response model on the way out.
    data: dict[str, Any] = {}


class ReasoningStepModel(BaseModel):
    stage: str
    detail: str


class ChatResponse(BaseModel):
    answer: str
    language: str
    agents_used: list[str]
    evidence: list[AgentResultModel]
    reasoning: list[ReasoningStepModel]
    used_stub_data: bool
    directive: str | None = None
    status: str = "COMPLETE"
    degraded_components: list[str] = []
    data_freshness: dict[str, str] = {}


class TranscriptionResponse(BaseModel):
    transcript: str
    language: str
    confidence: float | None = None


class SpeakRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)
    language: str = "en"
    speaker: str = "ritu"


class TranslateRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)
    target_language: str
    source_language: str = "auto"


class TranslateResponse(BaseModel):
    translated_text: str
