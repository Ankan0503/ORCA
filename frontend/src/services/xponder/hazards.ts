/**
 * What the transponder has told us, kept so the map can draw it.
 *
 * The warning overlay shows one message and dismisses it. A storm's extent and a
 * cyclone's forecast track are not that kind of message — they are geography, and
 * they are only useful drawn. This holds them between arriving and being drawn.
 *
 * It subscribes to the same singleton link the overlay and the SOS screen use, so
 * there is one radio, one subscription per screen, and no second copy of the
 * frames to fall out of step.
 *
 * Everything here is deliberately provenance-tagged. A fisherman looking at a
 * storm on the map must be able to tell "the forecast believes this" from "this
 * was transmitted to me" — the second means somebody decided he needed telling.
 */

import {
  XponderFrame,
  XponderMessageType,
  lightningMinutes,
  lightningRadiusKm,
  trackPosition,
  trackTimeIst,
} from './frame';
import { getXponderLink } from './link';

export interface LightningCell {
  latitude: number;
  longitude: number;
  /** Null when the terminal reported no extent — draw a marker, not a circle. */
  radiusKm: number | null;
  minutesAway: number;
  severity: number;
  receivedAt: number;
}

export interface TrackPoint {
  index: number;
  latitude: number;
  longitude: number;
  /** "14:30 IST" — the time this position is forecast for. */
  ist: string;
}

export interface CycloneTrack {
  points: TrackPoint[];
  /** How many the terminal said to expect, so a gap can be reported honestly. */
  total: number;
  severity: number;
  receivedAt: number;
}

export interface XponderHazards {
  lightning: LightningCell[];
  track: CycloneTrack | null;
}

/** How many cells to keep. A warning an hour old is history, not a hazard. */
const MAX_CELLS = 4;
const CELL_TTL_MS = 60 * 60 * 1000;

let state: XponderHazards = { lightning: [], track: null };
const listeners = new Set<(hazards: XponderHazards) => void>();
let started = false;

function publish() {
  listeners.forEach((listener) => listener(state));
}

function absorb(frame: XponderFrame) {
  if (frame.type === XponderMessageType.Lightning) {
    const cell: LightningCell = {
      latitude: frame.latitude,
      longitude: frame.longitude,
      radiusKm: lightningRadiusKm(frame),
      minutesAway: lightningMinutes(frame),
      severity: frame.severity,
      receivedAt: Date.now(),
    };
    const fresh = state.lightning.filter((c) => Date.now() - c.receivedAt < CELL_TTL_MS);
    state = { ...state, lightning: [cell, ...fresh].slice(0, MAX_CELLS) };
    publish();
    return;
  }

  if (frame.type === XponderMessageType.CycloneTrack) {
    const { index, total } = trackPosition(frame);
    const point: TrackPoint = {
      index,
      latitude: frame.latitude,
      longitude: frame.longitude,
      ist: trackTimeIst(frame),
    };

    // A track arriving with a different length is a new track, not a continuation.
    const existing = state.track && state.track.total === total ? state.track : null;
    const points = [...(existing?.points ?? []).filter((p) => p.index !== index), point].sort(
      (a, b) => a.index - b.index,
    );
    state = {
      ...state,
      track: { points, total, severity: frame.severity, receivedAt: Date.now() },
    };
    publish();
  }
}

/**
 * Watch what the transponder has sent.
 *
 * Starts listening on first use rather than at import, so a screen that never
 * draws a hazard never touches the radio.
 */
export function subscribeHazards(listener: (hazards: XponderHazards) => void): () => void {
  if (!started) {
    started = true;
    getXponderLink().onFrame(absorb);
  }
  listeners.add(listener);
  listener(state);
  return () => {
    listeners.delete(listener);
  };
}

/** Clear everything received. Used when a warning is dismissed. */
export function clearHazards() {
  state = { lightning: [], track: null };
  publish();
}

export function currentHazards(): XponderHazards {
  return state;
}
