/**
 * Boundary Alert Service — ORCA Frontend
 *
 * Monitors geofence and closure state and triggers:
 *   1. Maritime siren (Web Audio synthesized) for critical/proximity events.
 *   2. Browser SpeechSynthesis voice warnings for verbal announcements.
 *
 * Designed for the ORCA mobile-first frontend — uses only browser-native APIs
 * (Web Audio + SpeechSynthesis) so it works offline on any Android/iOS device.
 */

import { GeofenceResult, ClosureCheck } from '../orcaApi';
import { maritimeSiren } from './maritimeSirenService';

export type AlertLevel = 'critical' | 'warning' | 'advisory' | 'clear';

export interface BoundaryAlertState {
  level: AlertLevel;
  headline: string;
  detail: string;
  isSirenActive: boolean;
  isSpeaking: boolean;
}

/**
 * Voice warning phrases for boundary events.
 * Uses simple English (understood by coastal speakers) by default;
 * a language parameter can be added for regional languages in the future.
 */
function buildVoicePhrase(
  geofence: GeofenceResult | null,
  closures: ClosureCheck | null,
): { phrase: string; isCritical: boolean } | null {
  if (!geofence) return null;

  const nearest = geofence.nearestBoundary;
  const distKm = nearest?.distanceKm ?? 999;
  const neighbour = nearest?.neighbour ?? 'foreign waters';
  const bearing = nearest?.bearing ?? '';

  // 1. Crossed into foreign waters or outside EEZ
  if (geofence.level === 'critical' || geofence.level === 'outside' || geofence.level === 'beyond_eez') {
    const crossed = !geofence.insideEez;
    if (crossed) {
      return {
        phrase: `Emergency warning! Your vessel has crossed the international maritime boundary into ${neighbour}. You are ${distKm.toFixed(1)} kilometers from the Indian border. Turn to heading ${bearing} immediately and return to Indian waters. I repeat, return to Indian waters immediately.`,
        isCritical: true,
      };
    }
    return {
      phrase: `Critical warning! Your vessel is only ${distKm.toFixed(1)} kilometers from the ${neighbour} maritime boundary. Bearing ${bearing}. Alter course immediately to avoid crossing into foreign waters.`,
      isCritical: true,
    };
  }

  // 2. Warning zone — approaching boundary
  if (geofence.level === 'warning') {
    return {
      phrase: `Proximity warning. You are ${distKm.toFixed(1)} kilometers from the ${neighbour} maritime boundary. Bearing ${bearing}. Exercise caution and monitor your position.`,
      isCritical: false,
    };
  }

  // 3. Inside a protected area (MPA/sanctuary)
  if (closures?.insideProtectedArea) {
    const areaNames = closures.areas
      .filter((a) => a.inside)
      .map((a) => a.name)
      .join(', ');
    return {
      phrase: `Warning! Your vessel is inside a Marine Protected Area: ${areaNames}. Fishing is restricted in this zone. Leave the protected area immediately.`,
      isCritical: true,
    };
  }

  // 4. Near a protected area (close but not inside)
  if (closures?.areas?.length) {
    const nearAreas = closures.areas.filter((a) => !a.inside && a.distanceKm < 5);
    if (nearAreas.length > 0) {
      const closest = nearAreas.sort((a, b) => a.distanceKm - b.distanceKm)[0];
      return {
        phrase: `Advisory. You are ${closest.distanceKm.toFixed(1)} kilometers from the ${closest.name} Marine Protected Area. Fishing may be restricted nearby.`,
        isCritical: false,
      };
    }
  }

  return null;
}

class BoundaryAlertService {
  private isMuted: boolean = false;
  private isSpeaking: boolean = false;
  private lastAnnouncedKey: string | null = null;
  private cooldownMs: number = 20000; // Don't repeat same alert within 20s
  private lastAnnouncedAt: number = 0;
  private listeners: Set<(state: BoundaryAlertState) => void> = new Set();
  private currentState: BoundaryAlertState = {
    level: 'clear',
    headline: '',
    detail: '',
    isSirenActive: false,
    isSpeaking: false,
  };

  public subscribe(listener: (state: BoundaryAlertState) => void): () => void {
    this.listeners.add(listener);
    listener(this.currentState);
    return () => this.listeners.delete(listener);
  }

  private emit(state: Partial<BoundaryAlertState>) {
    this.currentState = { ...this.currentState, ...state };
    this.listeners.forEach((fn) => fn(this.currentState));
  }

  public setMuted(muted: boolean) {
    this.isMuted = muted;
    maritimeSiren.setMuted(muted);
    if (muted) {
      this.cancelSpeech();
      maritimeSiren.stop();
      this.emit({ isSirenActive: false, isSpeaking: false });
    }
  }

  public getIsMuted(): boolean {
    return this.isMuted;
  }

  /**
   * Evaluate the current geofence and closure state and trigger alerts.
   * Call this whenever the geofence or closure data changes.
   */
  public evaluate(geofence: GeofenceResult | null, closures: ClosureCheck | null) {
    if (!geofence) {
      this.emit({ level: 'clear', headline: '', detail: '' });
      return;
    }

    // Determine alert level
    let level: AlertLevel = 'clear';
    let headline = '';
    let detail = geofence.message;

    if (
      geofence.level === 'critical' ||
      geofence.level === 'outside' ||
      geofence.level === 'beyond_eez'
    ) {
      level = 'critical';
      headline = !geofence.insideEez ? 'MARITIME BOUNDARY CROSSED' : 'CRITICAL PROXIMITY';
    } else if (geofence.level === 'warning') {
      level = 'warning';
      headline = 'APPROACHING BOUNDARY';
    } else if (closures?.insideProtectedArea) {
      level = 'critical';
      headline = 'INSIDE PROTECTED AREA';
      detail = `${closures.areas.filter((a) => a.inside).map((a) => a.name).join(', ')} — fishing restricted`;
    } else if (closures?.areas?.some((a) => !a.inside && a.distanceKm < 5)) {
      level = 'advisory';
      headline = 'NEAR PROTECTED AREA';
      const closest = closures.areas
        .filter((a) => !a.inside)
        .sort((a, b) => a.distanceKm - b.distanceKm)[0];
      if (closest) {
        detail = `${closest.distanceKm.toFixed(1)} km from ${closest.name}`;
      }
    }

    this.emit({ level, headline, detail });

    // Trigger audio if not muted and not recently announced
    if (this.isMuted) return;

    const voiceData = buildVoicePhrase(geofence, closures);
    if (!voiceData) return;

    const dedupeKey = `${level}:${headline}`;
    const now = Date.now();
    if (dedupeKey === this.lastAnnouncedKey && now - this.lastAnnouncedAt < this.cooldownMs) {
      return; // Don't repeat the same alert too quickly
    }

    this.lastAnnouncedKey = dedupeKey;
    this.lastAnnouncedAt = now;

    this.playAlert(voiceData.phrase, voiceData.isCritical);
  }

  /**
   * Manually trigger a voice alert (e.g. from a "Listen" button).
   */
  public async speakCurrentState(geofence: GeofenceResult | null, closures: ClosureCheck | null) {
    await maritimeSiren.unlock();
    const voiceData = buildVoicePhrase(geofence, closures);
    if (voiceData) {
      this.lastAnnouncedKey = null; // Reset cooldown for manual trigger
      await this.playAlert(voiceData.phrase, voiceData.isCritical);
    }
  }

  /**
   * Play siren first, then speak the voice warning.
   */
  private async playAlert(phrase: string, isCritical: boolean): Promise<void> {
    // 1. Sound the siren
    if (isCritical) {
      maritimeSiren.playCriticalSiren(3.0);
      this.emit({ isSirenActive: true });
      await new Promise((r) => setTimeout(r, 3200)); // Wait for siren to finish
    } else {
      maritimeSiren.playProximityChime();
      this.emit({ isSirenActive: true });
      await new Promise((r) => setTimeout(r, 1000));
    }
    this.emit({ isSirenActive: false });

    // 2. Speak the voice warning
    await this.speakText(phrase, isCritical);
  }

  private speakText(text: string, isCritical: boolean): Promise<void> {
    return new Promise((resolve) => {
      if (typeof window === 'undefined' || !window.speechSynthesis) {
        resolve();
        return;
      }

      window.speechSynthesis.cancel();

      const utterance = new SpeechSynthesisUtterance(text);

      // Try to find an Indian English voice, falling back to any English voice
      const voices = window.speechSynthesis.getVoices();
      const indianEn = voices.find((v) => v.lang.toLowerCase().startsWith('en-in'));
      const anyEn = voices.find((v) => v.lang.toLowerCase().startsWith('en'));
      if (indianEn) {
        utterance.voice = indianEn;
        utterance.lang = 'en-IN';
      } else if (anyEn) {
        utterance.voice = anyEn;
        utterance.lang = anyEn.lang;
      } else {
        utterance.lang = 'en';
      }

      utterance.rate = isCritical ? 1.0 : 0.92;
      utterance.pitch = isCritical ? 1.05 : 1.0;
      utterance.volume = 0.95;

      this.isSpeaking = true;
      this.emit({ isSpeaking: true });

      utterance.onend = () => {
        this.isSpeaking = false;
        this.emit({ isSpeaking: false });
        resolve();
      };
      utterance.onerror = () => {
        this.isSpeaking = false;
        this.emit({ isSpeaking: false });
        resolve();
      };

      window.speechSynthesis.speak(utterance);
    });
  }

  public cancelSpeech() {
    if (typeof window !== 'undefined' && window.speechSynthesis) {
      window.speechSynthesis.cancel();
    }
    maritimeSiren.stop();
    this.isSpeaking = false;
    this.emit({ isSirenActive: false, isSpeaking: false });
  }

  /**
   * Stop all audio immediately.
   */
  public stopAll() {
    this.cancelSpeech();
    maritimeSiren.stop();
  }
}

export const boundaryAlerts = new BoundaryAlertService();
