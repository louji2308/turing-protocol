import { useEffect, useState } from 'react';
import { LineChart, Line, ResponsiveContainer } from 'recharts';

const ORACLE_URL = import.meta.env.VITE_ORACLE_URL || 'http://localhost:8080';

const cardStyle = {
  background: 'var(--surface-01)',
  border: '1px solid var(--border-subtle)',
  borderRadius: 'var(--radius-md)',
  padding: 'var(--space-4)',
  display: 'flex',
  flexDirection: 'column',
  minHeight: 260,
};

function Sparkline({ protocol }) {
  const [history, setHistory] = useState(null);

  useEffect(() => {
    let cancelled = false;
    fetch(`${ORACLE_URL}/api/v1/intelligence/protocols/${protocol.address}/health?days=30`)
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => { if (!cancelled && data) setHistory(data.history); })
      .catch(() => {});
    return () => { cancelled = true; };
  }, [protocol.address]);

  const up = (protocol.trend_30d ?? 0) >= 0;
  const trendColor = up ? 'var(--signal-human)' : 'var(--signal-agent)';

  return (
    <div className="data-row" style={{ padding: '6px 8px' }}>
      <span style={{ fontSize: 'var(--text-xs)', color: 'var(--text-secondary)', flex: 1, minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
        {protocol.protocol}
      </span>
      <div style={{ width: 90, height: 28 }}>
        <ResponsiveContainer>
          <LineChart data={history ?? []}>
            <Line type="monotone" dataKey="human_ratio" stroke={trendColor} strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <span style={{
        fontSize: 'var(--text-xs)', width: 50, textAlign: 'right',
        fontFamily: 'var(--font-mono)', fontWeight: 600, color: trendColor,
      }}>
        {protocol.trend_30d != null ? `${up ? '+' : ''}${(protocol.trend_30d * 100).toFixed(1)}%` : '—'}
      </span>
    </div>
  );
}

export function TrendSparklines({ protocols }) {
  return (
    <div style={cardStyle}>
      <div style={{ fontSize: 'var(--text-md)', fontWeight: 700, color: 'var(--text-primary)' }}>30-Day Trends</div>
      <div className="label-caps" style={{ marginTop: 2, marginBottom: 'var(--space-3)' }}>Human ratio change over time</div>
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 2 }}>
        {(!protocols || protocols.length === 0) ? (
          <div style={{ color: 'var(--text-muted)', fontSize: 'var(--text-sm)', textAlign: 'center', padding: 'var(--space-4)' }}>
            Trend data loading…
          </div>
        ) : (
          protocols.slice(0, 6).map((p) => <Sparkline key={p.address} protocol={p} />)
        )}
      </div>
    </div>
  );
}
