/**
 * Client for the ORCA backend.
 *
 * Everything the app knows about the API lives here, so components never build
 * URLs or shape payloads themselves.
 */

const API_BASE: string =
  (import.meta as unknown as { env?: Record<string, string> }).env?.VITE_API_BASE_URL ||
  'http://localhost:8000';

export interface EvidenceItem {
  source: string;
  label: string;
  value: string;
  unit: string | null;
  observed_at: string | null;
  note: string | null;
}

export interface AgentEvidence {
  agent: string;
  summary: string;
  evidence: EvidenceItem[];
  confidence: number;
  is_stub: boolean;
  error: string | null;
}

export interface ReasoningStep {
  stage: string;
  detail: string;
}

export interface ChatResult {
  answer: string;
  language: string;
  agents_used: string[];
  evidence: AgentEvidence[];
  reasoning: ReasoningStep[];
  used_stub_data: boolean;
}

/** A full voice turn: what was heard, what ORCA answered, and the spoken reply. */
export interface VoiceAskResult extends ChatResult {
  transcript: string;
  detected_language: string;
  language_confidence: number | null;
  audio_base64: string | null;
}

export class OrcaApiError extends Error {
  constructor(
    message: string,
    readonly status?: number,
  ) {
    super(message);
    this.name = 'OrcaApiError';
  }
}

async function parseOrThrow<T>(response: Response, what: string): Promise<T> {
  if (!response.ok) {
    let detail = `${what} failed (${response.status})`;
    try {
      const body = await response.json();
      if (body?.detail) detail = `${what}: ${body.detail}`;
    } catch {
      // Response had no JSON body; the status message is all we have.
    }
    throw new OrcaApiError(detail, response.status);
  }
  return (await response.json()) as T;
}

export interface Transcription {
  transcript: string;
  language: string;
  confidence: number | null;
}

/**
 * Transcribe speech only, without answering.
 *
 * This backs the review step: the user sees and can correct what was heard
 * before the slow part (planning and agents) runs on it.
 */
export async function transcribe(audio: Blob): Promise<Transcription> {
  const form = new FormData();
  const extension = audio.type.includes('ogg') ? 'ogg' : 'webm';
  form.append('file', audio, `speech.${extension}`);
  // "unknown" asks the backend to identify the spoken language itself.
  form.append('language', 'unknown');

  const response = await fetch(`${API_BASE}/voice/stt`, { method: 'POST', body: form });
  return parseOrThrow<Transcription>(response, 'Transcription');
}

/** Ask a typed question. */
export async function askOrca(params: {
  message: string;
  language?: string;
  /** Language already identified from speech, so it is not guessed again. */
  knownLanguage?: string;
  latitude?: number;
  longitude?: number;
  sessionId?: string;
}): Promise<ChatResult> {
  const response = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message: params.message,
      language: params.language,
      known_language: params.knownLanguage,
      latitude: params.latitude,
      longitude: params.longitude,
      session_id: params.sessionId,
    }),
  });
  return parseOrThrow<ChatResult>(response, 'Ask ORCA');
}

/**
 * Send recorded speech and get back the transcript, the answer and spoken audio.
 *
 * `language` defaults to "unknown", which asks the backend to identify the
 * spoken language rather than assuming the one selected in the UI.
 */
export async function askOrcaByVoice(params: {
  audio: Blob;
  language?: string;
  latitude?: number;
  longitude?: number;
  sessionId?: string;
}): Promise<VoiceAskResult> {
  const form = new FormData();
  const extension = params.audio.type.includes('ogg') ? 'ogg' : 'webm';
  form.append('file', params.audio, `question.${extension}`);
  form.append('language', params.language ?? 'unknown');
  if (params.latitude !== undefined) form.append('latitude', String(params.latitude));
  if (params.longitude !== undefined) form.append('longitude', String(params.longitude));
  if (params.sessionId) form.append('session_id', params.sessionId);

  const response = await fetch(`${API_BASE}/voice/ask`, { method: 'POST', body: form });
  return parseOrThrow<VoiceAskResult>(response, 'Voice question');
}

/** Speak text in the given language. Returns a playable object URL. */
export async function speak(text: string, language: string): Promise<string> {
  const response = await fetch(`${API_BASE}/voice/tts`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text, language }),
  });

  if (!response.ok) {
    throw new OrcaApiError(`Speech synthesis failed (${response.status})`, response.status);
  }

  return URL.createObjectURL(await response.blob());
}

/** Turn base64 audio from /voice/ask into a playable object URL. */
export function audioUrlFromBase64(base64: string, mimeType = 'audio/wav'): string {
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i += 1) bytes[i] = binary.charCodeAt(i);
  return URL.createObjectURL(new Blob([bytes], { type: mimeType }));
}

export async function checkHealth(): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE}/health`);
    return response.ok;
  } catch {
    return false;
  }
}
