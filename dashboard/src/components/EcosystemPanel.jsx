import { useEffect, useState } from 'react';
import { Activity } from 'lucide-react';
import { ProtocolLeaderboard } from './ProtocolLeaderboard';
import { SmartMoneyFlow } from './SmartMoneyFlow';
import { TrendSparklines } from './TrendSparklines';
import { ORACLE_API as ORACLE_URL } from '../config';

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
      try {
        const res = await fetch(`${ORACLE_URL}/api/v1/intelligence/smart-money/flows?days=14`);
        if (res.ok && !cancelled) setFlows(await res.json());
      } catch { /* offline */ }
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

  return (
    <div className="panel">
      <div className="panel-header">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div className="panel-title">MANTLE ECOSYSTEM HEALTH</div>
          <span className="badge badge-green">
            <span style={{ width: 5, height: 5, borderRadius: '50%', background: 'currentColor', display: 'inline-block' }} />
            INTELLIGENCE
          </span>
        </div>
        <div className="panel-subtitle">
          Live Protocol Humanness Scores, smart-money capital flows, and 30-day trends
        </div>
      </div>

      {error ? (
        <div style={{
          flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center',
          justifyContent: 'center', gap: 10, padding: 'var(--space-6)',
          color: 'var(--text-muted)', textAlign: 'center',
          border: '1px dashed var(--border-subtle)', borderRadius: 'var(--radius-lg)',
        }}>
          <Activity size={26} color="var(--text-disabled)" />
          <div style={{ fontSize: 'var(--text-sm)', color: 'var(--text-tertiary)' }}>
            Intelligence layer offline
          </div>
          <div style={{ fontSize: 'var(--text-2xs)', fontFamily: 'var(--font-mono)' }}>
            {error} · retrying every 60s
          </div>
        </div>
      ) : (
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
          gap: 'var(--space-3)',
          flex: 1,
        }}>
          <ProtocolLeaderboard protocols={protocols} />
          <SmartMoneyFlow flows={flows} />
          <TrendSparklines protocols={protocols} />
        </div>
      )}
    </div>
  );
}
