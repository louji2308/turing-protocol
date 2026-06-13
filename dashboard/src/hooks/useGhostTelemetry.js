import { useState, useEffect, useCallback } from 'react';
import { ORACLE_API, POLL_INTERVAL_MS } from '../config';

export function useGhostTelemetry(ghostAddress) {
  const [telemetry, setTelemetry] = useState(null);
  const [featureContributions, setFeatureContributions] = useState([]);
  const [ghostStatus, setGhostStatus] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [lastFetched, setLastFetched] = useState(null);
  const [apiAvailable, setApiAvailable] = useState(false);

  const apiBase = ORACLE_API;

  const fetchTelemetry = useCallback(async () => {
    if (!ghostAddress || ghostAddress === '0x0000000000000000000000000000000000000000') return;

    try {
      const resp = await fetch(
        `${apiBase}/score/${ghostAddress}?include_explanation=true`,
        { signal: AbortSignal.timeout(45000) }
      );

      if (resp.ok) {
        const data = await resp.json();
        setTelemetry(data);
        setApiAvailable(true);

        if (data.explanation && Array.isArray(data.explanation)) {
          const sorted = [...data.explanation]
            .sort((a, b) => Math.abs(b.contribution) - Math.abs(a.contribution))
            .slice(0, 12);
          setFeatureContributions(sorted);
        }

        setLastFetched(new Date());
      }
    } catch {
      setApiAvailable(false);
    } finally {
      setIsLoading(false);
    }

    try {
      const statusResp = await fetch('http://localhost:9100/status', { signal: AbortSignal.timeout(3000) });
      if (statusResp.ok) {
        const statusData = await statusResp.json();
        setGhostStatus(statusData);
      }
    } catch {
    }
  }, [ghostAddress, apiBase]);

  useEffect(() => {
    fetchTelemetry();
    const pollInterval = POLL_INTERVAL_MS;
    const interval = setInterval(fetchTelemetry, pollInterval);
    return () => clearInterval(interval);
  }, [fetchTelemetry]);

  return {
    telemetry,
    featureContributions,
    ghostStatus,
    isLoading,
    lastFetched,
    apiAvailable,
    refetch: fetchTelemetry,
  };
}
