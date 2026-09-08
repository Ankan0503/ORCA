/**
 * Client for the ORCA backend.
 *
 * Everything the app knows about the API lives here, so components never build
 * URLs or shape payloads themselves.
 */

/**
 * Where the backend lives when ORCA is running as an installed app.
 *
 * Hardcoded rather than left to an environment variable on purpose. If the
 * variable is missing at build time the APK silently reaches nothing — every
 * screen shows its "could not be reached" state and there is no clue why, on a
 * device with no console. A public URL in source is the cheaper mistake.
 * Override it with VITE_API_BASE_URL when pointing a build somewhere else.
 */
const HOSTED_API_BASE = 'https://orca-backend-fzw9.onrender.com';

/**
 * Whether this is the packaged app rather than a browser.
 *
 * Capacitor serves the bundle from `https://localhost` on Android and
 * `capacitor://localhost` on iOS, so the hostname check below sees "localhost"
 * and concludes a developer is running a backend on the same machine. On a
 * phone there is no such backend, and the app would spend the whole trip
 * talking to itself. Checked without importing @capacitor/core so the web
 * bundle stays free of it.
 */
const isNativeApp = (): boolean => {
  if (typeof window === 'undefined') return false;
  const capacitor = (
    window as unknown as {
      Capacitor?: { isNativePlatform?: () => boolean; platform?: string };
    }
  ).Capacitor;
  if (!capacitor) return false;
  if (typeof capacitor.isNativePlatform === 'function') return capacitor.isNativePlatform();
  return capacitor.platform != null && capacitor.platform !== 'web';
};

export const getApiBase = (): string => {
  const envBase = import.meta.env.VITE_API_BASE_URL?.trim();

  // The packaged app, first: it is the one case where "localhost" means the
  // handset and not a developer's laptop.
  if (isNativeApp()) {
    const usable =
      envBase && !envBase.includes('localhost') && !envBase.includes('127.0.0.1');
    return (usable ? envBase : HOSTED_API_BASE).replace(/\/+$/, '');
  }

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
      // If on a private local network IP (192.168.x.x, 10.x.x.x, 172.16-31.x.x), use host on port 8000:
      const isLanIp =
        /^(192\.168\.\d+\.\d+|10\.\d+\.\d+\.\d+|172\.(1[6-9]|2\d|3[0-1])\.\d+\.\d+)$/.test(hostname);
      if (isLanIp) {
        return `http://${hostname}:8000`;
      }
      // On production cloud deployments (e.g. Vercel multi-service), use same-origin /api:
      return '/api';
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
  /**
   * An agent's own findings, in machine-readable form. The visualization agent
   * puts a chart specification here, the reporting agent a dated brief, and the
   * data discovery agent the source catalogue with its live probe. Everything
   * else leaves it empty.
   */
  data?: Record<string, unknown>;
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
  const response = await fetch(
    `${API_BASE}/pfz/points?lang=${encodeURIComponent(lang)}&_t=${Date.now()}`,
    { cache: 'no-store' },
  );
  return parseOrThrow<PfzLines>(response, 'PFZ points');
}

/** The PFZ line geometry the INCOIS WebGIS draws, for the map. */
export async function getPfzLines(): Promise<PfzLines> {
  const response = await fetch(`${API_BASE}/pfz/lines?_t=${Date.now()}`, {
    cache: 'no-store',
  });
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

/* ---------------------------------------------------------------------------
 * Live sea conditions — backs the Safety, Sea Today and Alerts screens.
 *
 * One fetch serves all three so they can never contradict each other. Every
 * figure is a real Open-Meteo observation graded by the same thresholds the
 * weather agent uses.
 * ------------------------------------------------------------------------- */

export interface LiveCondition {
  id: 'wind' | 'waves' | 'rain' | 'visibility';
  name: string;
  value: number | null;
  unit: string;
  statusType: 'good' | 'caution' | 'alert';
  icon: 'wind' | 'waves' | 'rain' | 'visibility';
  note: string | null;
}

export interface LiveAlert {
  id: string;
  severity: 'high' | 'caution';
  badgeLabel: string;
  title: string;
  message: string;
  startsAt: string;
  actionRequired?: string;
}

export interface LiveForecastHour {
  time: string;
  temp: number | null;
  waveHeight: number | null;
  windSpeed: number | null;
  condition: string;
  status: 'safe' | 'caution' | 'unsafe';
}

export interface LiveConditions {
  location: { latitude: number; longitude: number; timezone: string };
  source: string;
  observedAt: string;
  fetchedAt: string;
  safety: {
    status: 'safe' | 'caution' | 'unsafe' | 'unknown';
    reasons: string[];
    safeUntil: string | null;
    safeUntilReasons: string[];
    conditions: LiveCondition[];
    adviceSteps: string[];
    maxWaveHeightM: number | null;
    maxWindKmh: number | null;
    maxGustKmh: number | null;
  };
  seaToday: {
    seaStatus: 'calm' | 'moderate' | 'rough';
    description: string;
    conditions: LiveCondition[];
    forecast: LiveForecastHour[];
    seaTemperatureC: number | null;
    airTemperatureC: number | null;
  };
  alerts: LiveAlert[];
  tides: { time: string; heightM: number; kind: 'high' | 'low' }[];
  sun: { sunrise: string | null; sunset: string | null };
}

/* ---------------------------------------------------------------------------
 * The hourly series behind the forecast charts.
 *
 * Separate from getConditions because only one screen draws it: three screens
 * read /conditions, and none of them should pay for 72 rows of series data
 * they never plot.
 * ------------------------------------------------------------------------ */

export interface TimelineHour {
  /** Local time at the forecast location, e.g. "2026-09-07T14:00:00". */
  time: string;
  waveHeightM: number | null;
  windSpeedKmh: number | null;
  windGustsKmh: number | null;
  windDirectionDeg: number | null;
  precipitationMm: number | null;
  isThunderstorm: boolean;
  status: 'safe' | 'caution' | 'unsafe' | 'unknown';
  /** Why this hour is graded as it is — shown when the reader taps the chart. */
  reasons: string[];
}

export interface TimelineThreshold {
  unit: string;
  label: string;
  caution: number;
  danger: number;
  dangerLabel: string;
  cautionLabel: string;
  /** The agency and document the danger line comes from. Always printed. */
  source: string;
  /** True when the caution line is ORCA's own approach warning, not a ruling. */
  cautionIsOrca: boolean;
}

export interface ForecastTimeline {
  location: { latitude: number; longitude: number; timezone: string };
  source: string;
  observedAt: string;
  fetchedAt: string;
  hours: TimelineHour[];
  thresholds: Record<'wave' | 'wind' | 'gust', TimelineThreshold>;
  safeUntil: string | null;
  safeUntilReasons: string[];
  sun: { sunrise: string[]; sunset: string[] };
}

/** The hourly wave/wind series, with the thresholds that grade it. */
export async function getForecastTimeline(
  latitude: number,
  longitude: number,
): Promise<ForecastTimeline> {
  const response = await fetch(
    `${API_BASE}/conditions/timeline?lat=${latitude}&lon=${longitude}`,
  );
  return parseOrThrow<ForecastTimeline>(response, 'Forecast timeline');
}

/* ---------------------------------------------------------------------------
 * A trip across several grounds, and whether it fits.
 *
 * The single-destination route answers "can I get there". This answers the
 * question that actually decides a day's fishing: can I work these grounds and
 * still be home before the weather turns. The return passage is usually the
 * longest leg, and it was never in the arithmetic before.
 * ------------------------------------------------------------------------ */

export interface ChainStop {
  /** 'ground' for a fishing zone, 'home' for the passage back. */
  kind: 'ground' | 'home';
  /** Position in the chain, or null for the return leg. */
  index: number | null;
  label: string;
  latitude: number;
  longitude: number;
  arrivalAt: string;
  cumulativeHours: number;
  cumulativeDistanceKm: number;
  /** Whether you arrive here before the sea turns. */
  withinSafeWindow: boolean;
  route: SeaRoute;
}

export interface ChainPlan {
  origin: RoutePlan['origin'];
  departureAt: string;
  boatSpeedKmh: number;
  stops: ChainStop[];
  totals: {
    distanceKm: number;
    hours: number;
    arrivalHomeAt: string | null;
    includesReturn: boolean;
  };
  safety: {
    safeUntil: string | null;
    reasons: string[];
    verdict: 'fits' | 'partly_fits' | 'does_not_fit';
    /** Index of the last ground reachable inside the window; null if none. */
    lastStopThatFits: number | null;
    message: string;
    /** The honest limit: the window is measured at the starting position. */
    basis: string;
  };
}

/** Plan a trip across several grounds and back, checked against the weather. */
export async function getChainRoute(
  latitude: number,
  longitude: number,
  stops: { latitude: number; longitude: number }[],
  options: { home?: boolean; speed?: number; lang?: string } = {},
): Promise<ChainPlan> {
  const stopParams = stops
    .map((s) => `&stop=${s.latitude.toFixed(4)},${s.longitude.toFixed(4)}`)
    .join('');
  const home = options.home === false ? '&home=false' : '';
  const speed = options.speed ? `&speed=${options.speed}` : '';
  const lang = `&lang=${encodeURIComponent(options.lang ?? 'en')}`;
  const response = await fetch(
    `${API_BASE}/route/chain?lat=${latitude}&lon=${longitude}${stopParams}${home}${speed}${lang}`,
  );
  return parseOrThrow<ChainPlan>(response, 'Trip plan');
}

/* ---------------------------------------------------------------------------
 * A decade of the sea at one place.
 *
 * Slow by nature — roughly thirty upstream requests across three archives — so
 * it is fetched on its own and never blocks the live conditions.
 * ------------------------------------------------------------------------ */

export interface TrendPoint {
  year: number;
  value: number;
}

export interface TrendMetric {
  key: 'sst' | 'wind' | 'rain' | 'wave';
  label: string;
  unit: string;
  source: string;
  byYear: TrendPoint[];
  /** Change per decade from a least-squares fit; null when too few years. */
  slopePerDecade: number | null;
  /** This season against the average of the earlier ones; null when not comparable. */
  anomaly: number | null;
  baseline: number | null;
  latest: number | null;
  firstYear: number | null;
  lastYear: number | null;
}

export interface SeasonTrends {
  location: { latitude: number; longitude: number };
  /** The calendar window compared in every year, e.g. "03 Aug – 02 Sep". */
  window: string;
  metrics: TrendMetric[];
  /** Limits of the record, including that ORCA holds no catch data at all. */
  notes: string[];
}

/** How the sea here has changed over the past decade. */
export async function getTrends(
  latitude: number,
  longitude: number,
  years = 10,
): Promise<SeasonTrends> {
  const response = await fetch(
    `${API_BASE}/trends?lat=${latitude}&lon=${longitude}&years=${years}`,
  );
  return parseOrThrow<SeasonTrends>(response, 'Historical trends');
}

/** Live sea conditions for a coordinate. */
export async function getConditions(
  latitude: number,
  longitude: number,
): Promise<LiveConditions> {
  const response = await fetch(`${API_BASE}/conditions?lat=${latitude}&lon=${longitude}`);
  return parseOrThrow<LiveConditions>(response, 'Sea conditions');
}

/* ---------------------------------------------------------------------------
 * Maritime boundaries — is the boat still in Indian waters?
 *
 * Backed by Marine Regions v12 geometry held on the server, so this answer does
 * not depend on any third-party service being reachable.
 * ------------------------------------------------------------------------- */

export interface GeofenceResult {
  latitude: number;
  longitude: number;
  insideEez: boolean;
  zone: string | null;
  /** clear | watch | warning | critical | outside | beyond_eez | not_at_sea */
  level: string;
  message: string;
  source: string;
  thresholds: { criticalKm: number; warningKm: number; watchKm: number; note: string };
  nearestBoundary: {
    lineName: string;
    neighbour: string;
    lineType: string;
    distanceKm: number;
    bearing: string;
    latitude: number;
    longitude: number;
  } | null;
}

/** Where a position stands relative to India's EEZ and its neighbours. */
export async function getGeofence(
  latitude: number,
  longitude: number,
): Promise<GeofenceResult> {
  const response = await fetch(`${API_BASE}/geofence?lat=${latitude}&lon=${longitude}`);
  return parseOrThrow<GeofenceResult>(response, 'Boundary check');
}

/* ---------------------------------------------------------------------------
 * Overall trip risk — the combined verdict.
 *
 * Synthesises sea safety, maritime-boundary proximity and whether the advised
 * fishing ground can be reached and left before conditions turn.
 * ------------------------------------------------------------------------- */

export interface TripRisk {
  /** low | moderate | high | severe */
  level: string;
  headline: string;
  drivers: string[];
  safeHours: number | null;
  trip: {
    distanceKm?: number;
    roundTripHours?: number;
    landingCentre?: string;
    assumedSpeedKmh?: number;
    fishingHours?: number;
    safeHours?: number | null;
    reachable?: boolean | null;
  };
}

export interface RiskResult {
  agent: string;
  summary: string;
  evidence: EvidenceItem[];
  confidence: number;
  is_stub: boolean;
  error: string | null;
  data: TripRisk;
}

/** Should I go out, and can I get back? */
export async function getRisk(
  latitude: number,
  longitude: number,
  lang = 'en',
): Promise<RiskResult> {
  const response = await fetch(
    `${API_BASE}/risk?lat=${latitude}&lon=${longitude}&lang=${encodeURIComponent(lang)}`,
  );
  return parseOrThrow<RiskResult>(response, 'Risk assessment');
}

/* ---------------------------------------------------------------------------
 * Area conditions — rain, storms and currents across the sea.
 *
 * Backs the hazard overlay and the current arrows on the map. The router plans
 * around this same grid, so what is drawn and what was routed around agree.
 * ------------------------------------------------------------------------- */

export interface SeaCell {
  /** Inside India's EEZ. Current arrows are clipped to this. */
  insideEez?: boolean;
  latitude: number;
  longitude: number;
  isSea: boolean;
  /** clear | light_rain | moderate_rain | heavy_rain | fog | thunderstorm */
  hazard: string;
  rainBand: string;
  precipitationMm: number | null;
  isThunderstorm: boolean;
  currentSpeedMs: number | null;
  currentDirectionDeg: number | null;
  currentTowards: string | null;
  currentSuspect: boolean;
}

export interface SeaGrid {
  origin: { latitude: number; longitude: number };
  spanDeg: number;
  cells: SeaCell[];
  counts: {
    total: number;
    sea: number;
    thunderstorm: number;
    rain: number;
    suspectCurrents: number;
  };
  thresholds: Record<string, number | string>;
  source: string;
}

/** Rain, storms and currents on a grid around a position. */
export async function getSeaGrid(
  latitude: number,
  longitude: number,
  span = 1.5,
): Promise<SeaGrid> {
  const response = await fetch(
    `${API_BASE}/seagrid?lat=${latitude}&lon=${longitude}&span=${span}`,
  );
  return parseOrThrow<SeaGrid>(response, 'Sea conditions grid');
}

/* ---------------------------------------------------------------------------
 * The passage — how to actually reach the fishing ground.
 *
 * A route around the weather, with the heading to steer on each leg once the
 * current has been allowed for. Times assume a boat speed and say so.
 * ------------------------------------------------------------------------- */

export interface RouteLeg {
  from: { latitude: number; longitude: number };
  to: { latitude: number; longitude: number };
  distanceKm: number;
  courseDeg: number;
  headingDeg: number;
  headingCompass: string;
  speedOverGroundKmh: number;
  hours: number;
  hazard: string;
  currentSpeedMs: number | null;
  currentTowardsDeg: number | null;
}

export interface SeaRoute {
  waypoints: { latitude: number; longitude: number }[];
  legs: RouteLeg[];
  totalDistanceKm: number;
  totalHours: number;
  directDistanceKm: number;
  detourKm: number;
  boatSpeedKmh: number;
  avoided: string[];
  assumption: string;
}

export interface RoutePlan {
  origin: {
    requested: { latitude: number; longitude: number };
    insideEez: boolean;
    atSea: boolean;
    sector: string;
    nearestLandingCentre: string | null;
    distanceToGroundKm: number | null;
  };
  destination: {
    latitude: number;
    longitude: number;
    landingCentre?: string;
    forecastDate?: string | null;
    validUpto?: string | null;
    sector?: string;
    depthFromM?: number | null;
    depthToM?: number | null;
    source?: string;
  };
  route: SeaRoute;
}

/** Plan a passage to the nearest INCOIS-advised ground. */
export async function getRoute(
  latitude: number,
  longitude: number,
  lang = 'en',
  speed?: number,
  /** Steer to a chosen zone instead of the nearest advised one. */
  destination?: { latitude: number; longitude: number },
): Promise<RoutePlan> {
  const speedParam = speed ? `&speed=${speed}` : '';
  const destParam = destination
    ? `&dest_lat=${destination.latitude}&dest_lon=${destination.longitude}`
    : '';
  const response = await fetch(
    `${API_BASE}/route?lat=${latitude}&lon=${longitude}&lang=${encodeURIComponent(lang)}${speedParam}${destParam}`,
  );
  return parseOrThrow<RoutePlan>(response, 'Route');
}

/* ---------------------------------------------------------------------------
 * Fishing closures — the rules, not the weather.
 *
 * A boat can break these on a calm, sunny day with a good catch showing: the
 * annual 61-day ban, and the marine protected areas it is an offence to fish in.
 * ------------------------------------------------------------------------- */

export interface FishingBan {
  coast: string;
  active: boolean;
  start: string;
  end: string;
  daysRemaining: number | null;
  daysUntil: number | null;
  message: string;
  exemption: string;
  source: string;
}

export interface ProtectedAreaHit {
  name: string;
  designation: string;
  iucnCategory: string | null;
  marineAreaKm2: number | null;
  distanceKm: number;
  inside: boolean;
  source: string;
}

export interface ClosureCheck {
  fishingBan: FishingBan;
  insideProtectedArea: boolean;
  areas: ProtectedAreaHit[];
  layerCount: number;
  /** Says plainly how complete the protected-area layer is. */
  coverageNote: string;
}

/** Is this position inside a protected area, and is the ban on today? */
export async function checkClosures(
  latitude: number,
  longitude: number,
): Promise<ClosureCheck> {
  const response = await fetch(
    `${API_BASE}/closures/check?lat=${latitude}&lon=${longitude}`,
  );
  return parseOrThrow<ClosureCheck>(response, 'Closure check');
}

/** Marine protected areas as GeoJSON, for the map. */
export async function getProtectedAreas(): Promise<PfzLines> {
  const response = await fetch(`${API_BASE}/closures/protected-areas`);
  return parseOrThrow<PfzLines>(response, 'Protected areas');
}

/**
 * Rain, storms and currents across the whole EEZ.
 *
 * The local grid answers "what is the weather where I am"; this answers "where
 * is the weather", which is what a fisherman needs to see a system closing on
 * his coast. Coarse by design and cached hard on the server.
 */
export async function getNationalSeaGrid(): Promise<{
  cells: SeaCell[];
  stepDeg: number;
  box: { latMin: number; lonMin: number; latMax: number; lonMax: number };
}> {
  const response = await fetch(`${API_BASE}/seagrid/national`);
  return parseOrThrow(response, 'National sea grid');
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
