import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, LabelList } from 'recharts';

function colorFor(ratio) {
  if (ratio >= 0.70) return '#22c55e';
  if (ratio >= 0.40) return '#f59e0b';
  return '#ef4444';
}

function trendArrow(trend) {
  if (trend == null) return '';
  if (trend > 0.02) return '\u25B2';
  if (trend < -0.02) return '\u25BC';
  return '\u2014';
}

export function ProtocolLeaderboard({ protocols }) {
  if (!protocols || protocols.length === 0) {
    return (
      <div className="bg-slate-800 rounded-xl p-4 flex items-center justify-center text-slate-400 text-sm h-[260px]">
        Protocol data loading...
      </div>
    );
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
    <div className="bg-slate-800 rounded-xl p-4">
      <h3 className="text-white font-semibold mb-2">Protocol Humanness Leaderboard</h3>
      <p className="text-xs text-slate-400 mb-2">% of Activity from Real Humans</p>
      <ResponsiveContainer width="100%" height={Math.max(200, data.length * 36)}>
        <BarChart data={data} layout="vertical" margin={{ left: 80 }}>
          <XAxis type="number" domain={[0, 100]} tick={{ fill: '#94a3b8', fontSize: 12 }} unit="%" />
          <YAxis type="category" dataKey="name" tick={{ fill: '#e2e8f0', fontSize: 12 }} width={90} />
          <Tooltip
            formatter={(value, name, props) => [`${value}% human`, `Avg HPS: ${props.payload.avg_hps}`]}
            contentStyle={{ background: '#1e293b', border: 'none', color: '#fff' }}
          />
          <Bar dataKey="pct" radius={[0, 4, 4, 0]}>
            {data.map((entry, i) => <Cell key={i} fill={colorFor(entry.pct / 100)} />)}
            <LabelList
              dataKey="trend7d"
              position="right"
              formatter={trendArrow}
              fill="#cbd5e1"
            />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
