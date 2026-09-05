/**
 * The user's working location.
 *
 * Everything ORCA reports is tied to a coordinate — waves, wind, fishing zones,
 * distance to a maritime boundary. The app previously hardcoded Digha, so every
 * answer was wrong for anyone else on the coast.
 */

export interface UserLocation {
  name: string;
  latitude: number;
  longitude: number;
  /** How we came by it, so the UI can say whether it was detected or chosen. */
  source: 'default' | 'gps' | 'manual';
}

/** Digha fishing harbour — the starting point until the user says otherwise. */
export const DEFAULT_LOCATION: UserLocation = {
  name: 'Digha, West Bengal',
  latitude: 21.6272,
  longitude: 87.5079,
  source: 'default',
};

const STORAGE_KEY = 'orca.location';

export function loadStoredLocation(): UserLocation {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return DEFAULT_LOCATION;
    const parsed = JSON.parse(raw) as Partial<UserLocation>;
    if (
      typeof parsed.latitude === 'number' &&
      typeof parsed.longitude === 'number' &&
      typeof parsed.name === 'string'
    ) {
      return {
        name: parsed.name,
        latitude: parsed.latitude,
        longitude: parsed.longitude,
        source: parsed.source === 'gps' || parsed.source === 'manual' ? parsed.source : 'manual',
      };
    }
  } catch {
    // Private browsing, cleared storage, or corrupt JSON — fall back quietly.
  }
  return DEFAULT_LOCATION;
}

export function storeLocation(location: UserLocation): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(location));
  } catch {
    // Persistence is a convenience; the session still works without it.
  }
}

/** Used when a coordinate has no name — better than showing nothing. */
export function coordinateLabel(latitude: number, longitude: number): string {
  const ns = latitude >= 0 ? 'N' : 'S';
  const ew = longitude >= 0 ? 'E' : 'W';
  return `${Math.abs(latitude).toFixed(3)}°${ns}, ${Math.abs(longitude).toFixed(3)}°${ew}`;
}
