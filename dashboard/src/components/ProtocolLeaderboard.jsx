import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, LabelList } from 'recharts';

function colorFor(ratio) {
  if (ratio >= 0.70) return 'var(--signal-human)';
  if (ratio >= 0.40) return 'var(--signal-uncertain)';
  return 'var(--signal-agent)';
}

function trendArrow(trend) {
  if (trend == null) return '';
  if (trend > 0.02) return '▲';
  if (trend < -0.02) return '▼';
  return '—';
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
    return <Loading label="Protocol data loading…" />;
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
        <ResponsiveContainer width="100%" height={Math.max(200, data.length * 36)}>
          <BarChart data={data} layout="vertical" margin={{ left: 70, right: 24 }}>
            <XAxis type="number" domain={[0, 100]} tick={{ fill: 'var(--text-muted)', fontSize: 11 }} unit="%" axisLine={false} tickLine={false} />
            <YAxis type="category" dataKey="name" tick={{ fill: 'var(--text-secondary)', fontSize: 11 }} width={80} axisLine={false} tickLine={false} />
            <Tooltip
              cursor={{ fill: 'var(--surface-02)' }}
              formatter={(value, name, props) => [`${value}% human`, `Avg HPS: ${props.payload.avg_hps}`]}
              contentStyle={{ background: 'rgba(20,23,38,0.92)', border: '1px solid var(--border-default)', borderRadius: 8, color: '#fff' }}
            />
            <Bar dataKey="pct" radius={[0, 4, 4, 0]} barSize={16}>
              {data.map((entry, i) => <Cell key={i} fill={colorFor(entry.pct / 100)} />)}
              <LabelList dataKey="trend7d" position="right" formatter={trendArrow} fill="var(--text-tertiary)" fontSize={11} />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
