import { useEffect, useState } from 'react';
import { getConditions, LiveConditions } from '../services/orcaApi';

/**
 * Live sea conditions for a coordinate, shared by Safety, Sea Today and Alerts.
 *
 * One hook so the three screens always agree: they read the same forecast, taken
 * at the same moment, graded by the same thresholds. `loading` and `error` are
 * surfaced rather than swallowed, because a screen that quietly falls back to
 * invented numbers is exactly what this replaced.
 */
export function useConditions(latitude?: number, longitude?: number) {
  const [data, setData] = useState<LiveConditions | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (latitude == null || longitude == null) {
      setLoading(false);
      setError('No location set');
      return;
    }

    let cancelled = false;
    setLoading(true);
    setError(null);

    getConditions(latitude, longitude)
      .then((result) => {
        if (!cancelled) setData(result);
      })
      .catch((err) => {
        if (!cancelled) setError(err?.message ?? 'Could not load sea conditions');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [latitude, longitude]);

  return { data, loading, error };
}

/** Format an ISO timestamp as a local clock time, e.g. "14:00". */
export function clockTime(iso: string | null | undefined): string {
  if (!iso) return '';
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return '';
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false });
}

/** "3 mins ago" style relative label for when the forecast was taken. */
export function relativeTime(iso: string | null | undefined): string {
  if (!iso) return '';
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return '';
  const mins = Math.max(0, Math.round((Date.now() - then) / 60000));
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins} min ago`;
  const hours = Math.round(mins / 60);
  return hours === 1 ? '1 hour ago' : `${hours} hours ago`;
}
