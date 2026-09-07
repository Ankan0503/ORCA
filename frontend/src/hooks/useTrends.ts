import { useEffect, useState } from 'react';
import { SeasonTrends, getTrends } from '../services/orcaApi';

/**
 * A decade of the sea at one place.
 *
 * Deliberately the slowest hook in the app — it fans out across three archives
 * for every year — so it is never awaited alongside the live conditions. The
 * screen renders without it and the trend section appears when it lands.
 */
export function useTrends(latitude?: number, longitude?: number, years = 10) {
  const [data, setData] = useState<SeasonTrends | null>(null);
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

    getTrends(latitude, longitude, years)
      .then((result) => {
        if (!cancelled) setData(result);
      })
      .catch((err) => {
        if (!cancelled) setError(err?.message ?? 'Could not load the historical record');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [latitude, longitude, years]);

  return { data, loading, error };
}
