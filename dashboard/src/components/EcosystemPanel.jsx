import { useEffect, useState } from 'react';
import { ProtocolLeaderboard } from './ProtocolLeaderboard';
import { SmartMoneyFlow } from './SmartMoneyFlow';
import { TrendSparklines } from './TrendSparklines';

const ORACLE_URL = import.meta.env.VITE_ORACLE_URL || 'http://localhost:8080';

function useProtocolHealthData() {
  const [protocols, setProtocols] = useState([]);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    const poll = async () => {
      try {
        const res = await fetch(`${ORACLE_URL}/api/v1/intelligence/protocols`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        if (!cancelled) { setProtocols(data); setError(null); }
      } catch (e) {
        if (!cancelled) setError(e.message);
      }
    };
    poll();
    const interval = setInterval(poll, 60000);
    return () => { cancelled = true; clearInterval(interval); };
  }, []);

  return { protocols, error };
}

function useSmartMoneyFlows() {
  const [flows, setFlows] = useState(null);
  useEffect(() => {
    let cancelled = false;
    const poll = async () => {
      const res = await fetch(`${ORACLE_URL}/api/v1/intelligence/smart-money/flows?days=14`);
      if (res.ok && !cancelled) setFlows(await res.json());
    };
    poll();
    const interval = setInterval(poll, 60000);
    return () => { cancelled = true; clearInterval(interval); };
  }, []);
  return flows;
}

export function EcosystemPanel() {
  const { protocols, error } = useProtocolHealthData();
  const flows = useSmartMoneyFlows();

  if (error) {
    return (
      <div className="ecosystem-panel bg-slate-900 rounded-xl p-4 text-slate-400 text-sm">
        Intelligence layer unavailable: {error}. Retrying...
      </div>
    );
  }

  return (
    <div className="ecosystem-panel">
      <h2 className="text-xl font-bold text-white mb-1">Mantle Ecosystem Health</h2>
      <p className="text-sm text-slate-400 mb-4">
        Live Protocol Humanness Scores, smart-money capital flows, and 30-day trends
      </p>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <ProtocolLeaderboard protocols={protocols} />
        <SmartMoneyFlow flows={flows} />
        <TrendSparklines protocols={protocols} />
      </div>
    </div>
  );
}
