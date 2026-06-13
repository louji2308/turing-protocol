import { useEffect, useState } from 'react';
import { LineChart, Line, ResponsiveContainer } from 'recharts';

const ORACLE_URL = import.meta.env.VITE_ORACLE_URL || 'http://localhost:8080';

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

  const trendColor = (protocol.trend_30d ?? 0) >= 0 ? '#22c55e' : '#ef4444';

  return (
    <div className="flex items-center justify-between py-1">
      <span className="text-xs text-slate-300 truncate w-24">{protocol.protocol}</span>
      <div className="w-24 h-8">
        <ResponsiveContainer>
          <LineChart data={history ?? []}>
            <Line type="monotone" dataKey="human_ratio" stroke={trendColor} strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <span className="text-xs text-slate-400 w-12 text-right">
        {protocol.trend_30d != null ? `${(protocol.trend_30d * 100).toFixed(1)}%` : '\u2014'}
      </span>
    </div>
  );
}

export function TrendSparklines({ protocols }) {
  return (
    <div className="bg-slate-800 rounded-xl p-4">
      <h3 className="text-white font-semibold mb-2">30-Day Trends</h3>
      <p className="text-xs text-slate-400 mb-2">Human ratio change over time</p>
      {(!protocols || protocols.length === 0) ? (
        <div className="text-slate-400 text-sm py-4 text-center">Trend data loading...</div>
      ) : (
        protocols.slice(0, 6).map((p) => <Sparkline key={p.address} protocol={p} />)
      )}
    </div>
  );
}
