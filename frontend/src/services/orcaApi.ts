/**
 * Client for the ORCA backend.
 *
 * Everything the app knows about the API lives here, so components never build
 * URLs or shape payloads themselves.
 */

export const getApiBase = (): string => {
  const envBase = import.meta.env.VITE_API_BASE_URL?.trim();

  if (typeof window !== 'undefined' && window.location?.hostname) {
    const hostname = window.location.hostname;
    const isLocalhost =
      hostname === 'localhost' ||
      hostname === '127.0.0.1' ||
      hostname === '[::1]';

    // When accessed from a mobile phone or another LAN device (e.g. 192.168.29.43:3000):
    if (!isLocalhost && hostname) {
      // If an explicit remote URL was configured (not pointing to localhost/127.0.0.1), use it.
      if (envBase && !envBase.includes('localhost') && !envBase.includes('127.0.0.1')) {
        return envBase.replace(/\/+$/, '');
      }
      // Otherwise, the backend is running on the host machine serving this page, on port 8000.
      return `http://${hostname}:8000`;
    }
  }

  if (envBase) {
    return envBase.replace(/\/+$/, '');
  }

  return 'http://localhost:8000';
};

const API_BASE: string = getApiBase();

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

/* ---------------------------------------------------------------------------
 * Potential Fishing Zones — the real INCOIS advisory.
 *
 * These back the map's PFZ layer and the Find Fish recommendation. The data is
 * the Indian government's own daily advisory, scraped by the backend; the
 * frontend only draws it.
 * ------------------------------------------------------------------------- */

export interface PfzPoint {
  landing_centre: string;
  direction: string;
  bearing_deg: number | null;
  distance_km_from: number | null;
  distance_km_to: number | null;
  depth_m_from: number | null;
  depth_m_to: number | null;
  latitude: number;
  longitude: number;
  latitude_dms: string;
  longitude_dms: string;
  /** Straight-line distance from the user, added by /pfz/advisory. */
  range_km?: number;
}

export interface PfzAdvisory {
  secid: string;
  sector_name: string;
  language: string;
  forecast_date: string | null;
  valid_upto: string | null;
  empty: boolean;
  stale: boolean;
  points: PfzPoint[];
  origin?: { latitude: number; longitude: number };
}

/** GeoJSON of the PFZ lines INCOIS draws, tagged with the forecast date. */
export interface PfzLines {
  type: string;
  features: GeoJSON.Feature[];
  orca_forecast_date?: string | null;
  orca_valid_upto?: string | null;
  orca_stale?: boolean;
}

/**
 * Every sector's advisory rows as a GeoJSON point layer — the map's fishing
 * zones. All 14 coastal sectors, scraped daily from INCOIS.
 */
export async function getPfzPoints(lang = 'en'): Promise<PfzLines> {
  const response = await fetch(`${API_BASE}/pfz/points?lang=${encodeURIComponent(lang)}`);
  return parseOrThrow<PfzLines>(response, 'PFZ points');
}

/** The PFZ line geometry the INCOIS WebGIS draws, for the map. */
export async function getPfzLines(): Promise<PfzLines> {
  const response = await fetch(`${API_BASE}/pfz/lines`);
  return parseOrThrow<PfzLines>(response, 'PFZ lines');
}

/**
 * The government advisory for whichever coastal sector is nearest a position.
 * `lang` selects the language INCOIS returns landing-centre names in.
 */
export async function getPfzAdvisory(
  latitude: number,
  longitude: number,
  lang = 'en',
): Promise<PfzAdvisory> {
  const response = await fetch(
    `${API_BASE}/pfz/advisory?lat=${latitude}&lon=${longitude}&lang=${encodeURIComponent(lang)}`,
  );
  return parseOrThrow<PfzAdvisory>(response, 'PFZ advisory');
}

export async function checkHealth(): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE}/health`);
    return response.ok;
  } catch {
    return false;
  }
}

export interface PlaceResult {
  name: string;
  latitude: number;
  longitude: number;
  admin: string | null;
  country: string | null;
  country_code: string | null;
  timezone: string | null;
}

/** Search for a place by name. Results are biased to India. */
export async function searchPlaces(query: string, signal?: AbortSignal): Promise<PlaceResult[]> {
  const response = await fetch(
    `${API_BASE}/location/search?q=${encodeURIComponent(query)}&limit=8`,
    { signal },
  );
  const body = await parseOrThrow<{ results: PlaceResult[] }>(response, 'Place search');
  return body.results;
}

/**
 * Name a coordinate from the device GPS.
 *
 * Purely cosmetic: the forecast needs the coordinate, not the name, so callers
 * fall back to showing the numbers if this fails.
 */
export async function reverseGeocode(
  latitude: number,
  longitude: number,
): Promise<{ name: string; admin: string | null }> {
  const response = await fetch(
    `${API_BASE}/location/reverse?latitude=${latitude}&longitude=${longitude}`,
  );
  return parseOrThrow<{ name: string; admin: string | null }>(response, 'Location lookup');
}
