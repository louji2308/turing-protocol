import {
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  Area,
  AreaChart,
  CartesianGrid,
} from 'recharts';

export default function ScoreChart({ data = [], height = 160 }) {
  const chartData = data.length >= 2 ? data : [
    { time: '\u2014', score: 5000, label: '' },
    { time: '\u2014', score: 5000, label: '' },
  ];

  const CustomTooltip = ({ active, payload, label }) => {
    if (!active || !payload || !payload.length) return null;
    const score = payload[0].value;
    const getColor = (s) => {
      if (s >= 7000) return 'var(--signal-human-text)';
      if (s >= 5000) return 'var(--signal-uncertain-text)';
      return 'var(--signal-agent-text)';
    };

    return (
      <div style={{
        background: 'var(--bg-elevated)',
        border: '1px solid var(--border-default)',
        borderRadius: '6px',
        padding: '8px 12px',
        fontSize: '11px',
        fontFamily: 'var(--font-mono)',
      }}>
        <div style={{ color: 'var(--text-tertiary)', marginBottom: 4 }}>{label}</div>
        <div style={{ color: getColor(score), fontWeight: 700, fontSize: '14px' }}>
          {score.toLocaleString()}
        </div>
        <div style={{ color: 'var(--text-muted)', fontSize: '10px' }}>
          {(score / 100).toFixed(2)}% human
        </div>
      </div>
    );
  };

  const gradientId = 'scoreGradient';

  return (
    <div style={{ position: 'relative' }}>
      <div style={{
        position: 'absolute',
        right: 0,
        top: 0,
        display: 'flex',
        flexDirection: 'column',
        gap: 4,
        zIndex: 1,
        pointerEvents: 'none',
      }}>
        <span style={{
          fontSize: '9px',
          color: 'var(--signal-human)',
          letterSpacing: '1px',
          fontFamily: 'var(--font-mono)',
          opacity: 0.7,
        }}>
          7000 ─ HUMAN
        </span>
        <span style={{
          fontSize: '9px',
          color: 'var(--signal-uncertain)',
          letterSpacing: '1px',
          fontFamily: 'var(--font-mono)',
          opacity: 0.7,
          marginTop: 8,
        }}>
          5000 ─ UNCERTAIN
        </span>
      </div>

      <ResponsiveContainer width="100%" height={height}>
        <AreaChart data={chartData} margin={{ top: 8, right: 4, bottom: 0, left: -20 }}>
          <defs>
            <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="var(--accent-purple)" stopOpacity={0.3} />
              <stop offset="100%" stopColor="var(--accent-purple)" stopOpacity={0.0} />
            </linearGradient>
          </defs>

          <CartesianGrid
            strokeDasharray="2 6"
            stroke="var(--border-subtle)"
            vertical={false}
          />

          <XAxis
            dataKey="time"
            tick={{ fontSize: 9, fill: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}
            axisLine={false}
            tickLine={false}
            interval="preserveStartEnd"
          />

          <YAxis
            domain={[0, 10000]}
            tick={{ fontSize: 9, fill: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}
            axisLine={false}
            tickLine={false}
            tickCount={5}
            tickFormatter={(v) => v.toLocaleString()}
          />

          <Tooltip content={<CustomTooltip />} />

          <ReferenceLine
            y={7000}
            stroke="var(--signal-human)"
            strokeDasharray="3 5"
            strokeOpacity={0.5}
            strokeWidth={1}
          />

          <ReferenceLine
            y={5000}
            stroke="var(--signal-uncertain)"
            strokeDasharray="3 5"
            strokeOpacity={0.5}
            strokeWidth={1}
          />

          <Area
            type="monotoneX"
            dataKey="score"
            stroke="var(--accent-purple)"
            strokeWidth={2}
            fill={`url(#${gradientId})`}
            dot={false}
            activeDot={{
              r: 4,
              fill: 'var(--accent-purple)',
              stroke: 'var(--bg-void)',
              strokeWidth: 2,
            }}
            animationDuration={300}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
