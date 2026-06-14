import { useEffect, useState } from 'react';
import { LineChart, Line, ResponsiveContainer } from 'recharts';
import { ORACLE_API as ORACLE_URL } from '../config';

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

  const isLoading = !history;

  return (
    <div className="data-row" style={{ padding: '6px 8px' }}>
      <span style={{ fontSize: 'var(--text-xs)', color: 'var(--text-secondary)', flex: 1, minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontWeight: 600 }}>
        {protocol.protocol}
      </span>
      <div style={{ width: 90, height: 28 }}>
        {isLoading ? (
          <div style={{
            height: '100%', borderRadius: 2,
            background: 'linear-gradient(90deg, var(--surface-01) 25%, var(--surface-02) 50%, var(--surface-01) 75%)',
            backgroundSize: '200% 100%',
            animation: 'shimmer 1.5s ease-in-out infinite',
          }} />
        ) : (
          <ResponsiveContainer>
            <LineChart data={history ?? []}>
              <Line type="monotone" dataKey="human_ratio" stroke={trendColor} strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>
      <span className="badge" style={{
        fontSize: '9px', padding: '2px 8px',
        background: up ? 'var(--signal-human-glow)' : 'var(--signal-agent-glow)',
        borderColor: up ? 'var(--signal-human-border)' : 'var(--signal-agent-border)',
        color: trendColor,
        fontWeight: 700,
      }}>
        {protocol.trend_30d != null ? `${up ? '+' : ''}${(protocol.trend_30d * 100).toFixed(1)}%` : '\u2014'}
      </span>
    </div>
  );
}

function LoadingSkeleton() {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6, padding: 'var(--space-2)' }}>
      {[1, 2, 3, 4, 5, 6].map((i) => (
        <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <div style={{ flex: 1, height: 12, borderRadius: 2, background: 'linear-gradient(90deg, var(--surface-01) 25%, var(--surface-02) 50%, var(--surface-01) 75%)', backgroundSize: '200% 100%', animation: 'shimmer 1.5s ease-in-out infinite' }} />
          <div style={{ width: 90, height: 28, borderRadius: 2, background: 'linear-gradient(90deg, var(--surface-01) 25%, var(--surface-02) 50%, var(--surface-01) 75%)', backgroundSize: '200% 100%', animation: 'shimmer 1.5s ease-in-out infinite' }} />
          <div style={{ width: 50, height: 18, borderRadius: 20, background: 'linear-gradient(90deg, var(--surface-01) 25%, var(--surface-02) 50%, var(--surface-01) 75%)', backgroundSize: '200% 100%', animation: 'shimmer 1.5s ease-in-out infinite' }} />
        </div>
      ))}
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
          <LoadingSkeleton />
        ) : (
          protocols.slice(0, 6).map((p) => <Sparkline key={p.address} protocol={p} />)
        )}
      </div>
    </div>
  );
}
