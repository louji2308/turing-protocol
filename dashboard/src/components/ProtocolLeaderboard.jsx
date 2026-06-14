import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';

function colorFor(ratio) {
  if (ratio >= 0.70) return 'var(--signal-human)';
  if (ratio >= 0.40) return 'var(--signal-uncertain)';
  return 'var(--signal-agent)';
}

function dimColor(color) {
  if (color === 'var(--signal-human)') return 'rgba(0,255,163,0.2)';
  if (color === 'var(--signal-uncertain)') return 'rgba(245,158,11,0.2)';
  return 'rgba(255,51,85,0.2)';
}

function trendArrow(trend) {
  if (trend == null) return '';
  if (trend > 0.02) return '\u25B2';
  if (trend < -0.02) return '\u25BC';
  return '\u2014';
}

function trendColor(trend) {
  if (trend == null) return 'var(--text-muted)';
  if (trend > 0.02) return 'var(--signal-human)';
  if (trend < -0.02) return 'var(--signal-agent)';
  return 'var(--text-muted)';
}

const cardStyle = {
  background: 'var(--surface-01)',
  border: '1px solid var(--border-subtle)',
  borderRadius: 'var(--radius-md)',
  padding: 'var(--space-4)',
  display: 'flex',
  flexDirection: 'column',
  minHeight: 260,
};

function Loading({ label }) {
  return (
    <div style={{ ...cardStyle, alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)', fontSize: 'var(--text-sm)' }}>
      {label}
    </div>
  );
}

export function ProtocolLeaderboard({ protocols }) {
  if (!protocols || protocols.length === 0) {
    return <Loading label="Protocol data loading\u2026" />;
  }

  const data = [...protocols]
    .sort((a, b) => b.human_ratio - a.human_ratio)
    .map((p) => ({
      name: p.protocol,
      pct: Math.round(p.human_ratio * 100),
      avg_hps: p.avg_hps,
      trend7d: p.trend_7d,
    }));

  return (
    <div style={cardStyle}>
      <div style={{ fontSize: 'var(--text-md)', fontWeight: 700, color: 'var(--text-primary)' }}>Humanness Leaderboard</div>
      <div className="label-caps" style={{ marginTop: 2, marginBottom: 'var(--space-3)' }}>% activity from real humans</div>
      <div style={{ flex: 1, minHeight: 0 }}>
        <ResponsiveContainer width="100%" height={Math.max(200, data.length * 40)}>
          <BarChart data={data} layout="vertical" margin={{ left: 80, right: 40 }}>
            <XAxis type="number" domain={[0, 100]} tick={{ fill: 'var(--text-muted)', fontSize: 10 }} unit="%" axisLine={false} tickLine={false} />
            <YAxis type="category" dataKey="name" tick={{ fill: 'var(--text-secondary)', fontSize: 10 }} width={80} axisLine={false} tickLine={false} />
            <Tooltip
              cursor={{ fill: 'var(--surface-02)' }}
              formatter={(value) => [`${value}% human`]}
              contentStyle={{ background: 'rgba(8,10,20,0.96)', border: '1px solid var(--border-default)', borderRadius: 'var(--radius-md)', color: '#fff', fontSize: '11px' }}
            />
            <Bar dataKey="pct" radius={[0, 4, 4, 0]} barSize={18}>
              {data.map((entry, i) => {
                const c = colorFor(entry.pct / 100);
                return (
                  <Cell key={i} fill={`url(#barGrad${i})`} />
                );
              })}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 4, marginTop: 4 }}>
        {data.map((entry, i) => (
          <div key={entry.name} style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: 8, fontSize: 'var(--text-2xs)' }}>
            <div style={{
              width: 30, height: 4, borderRadius: 2,
              background: `linear-gradient(90deg, ${dimColor(colorFor(entry.pct / 100))}, ${colorFor(entry.pct / 100)})`,
              boxShadow: `0 0 4px ${colorFor(entry.pct / 100)}44`,
            }} />
            <span style={{
              fontFamily: 'var(--font-mono)',
              fontWeight: 600,
              color: trendColor(entry.trend7d),
              width: 36,
              textAlign: 'right',
            }}>
              {trendArrow(entry.trend7d)}
            </span>
          </div>
        ))}
      </div>
      <defs>
        {data.map((entry, i) => {
          const c = colorFor(entry.pct / 100);
          const dim = dimColor(c);
          return (
            <linearGradient key={i} id={`barGrad${i}`} x1="0" y1="0" x2="1" y2="0">
              <stop offset="0%" stopColor={dim} />
              <stop offset="100%" stopColor={c} />
            </linearGradient>
          );
        })}
      </defs>
    </div>
  );
}
