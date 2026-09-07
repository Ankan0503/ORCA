import { useEffect, useState } from 'react';
import { ForecastTimeline, getForecastTimeline } from '../services/orcaApi';

/**
 * The hourly wave/wind series behind the forecast chart.
 *
 * Kept out of `useConditions` on purpose. Three screens read that hook, and only
 * the ones that draw a chart should pay for 72 rows of series data — the same
 * reason the endpoint is separate on the server.
 *
 * Failure is surfaced, never smoothed over: a chart drawn from nothing would be
 * a picture of a calm sea that nobody measured.
 */
export function useForecastTimeline(latitude?: number, longitude?: number) {
  const [data, setData] = useState<ForecastTimeline | null>(null);
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

    getForecastTimeline(latitude, longitude)
      .then((result) => {
        if (!cancelled) setData(result);
      })
      .catch((err) => {
        if (!cancelled) setError(err?.message ?? 'Could not load the forecast timeline');
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
