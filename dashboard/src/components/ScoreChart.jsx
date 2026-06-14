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

function getScoreColor(s) {
  if (s >= 7000) return 'var(--signal-human)';
  if (s >= 5000) return 'var(--signal-uncertain)';
  return 'var(--signal-agent)';
}

export default function ScoreChart({ data = [], height = 200 }) {
  const chartData = data.length >= 2 ? data : [
    { time: '\u2014', score: 5000, label: '' },
    { time: '\u2014', score: 5000, label: '' },
  ];

  const latestScore = chartData[chartData.length - 1]?.score ?? 5000;
  const accentColor = getScoreColor(latestScore);

  const CustomTooltip = ({ active, payload, label }) => {
    if (!active || !payload || !payload.length) return null;
    const score = payload[0].value;
    return (
      <div style={{
        background: 'var(--bg-panel-solid)',
        border: `1px solid var(--border-default)`,
        borderRadius: 'var(--radius-md)',
        padding: '10px 14px',
        fontSize: '11px',
        fontFamily: 'var(--font-mono)',
        backdropFilter: 'blur(16px)',
        boxShadow: 'var(--shadow-md)',
      }}>
        <div style={{ color: 'var(--text-tertiary)', marginBottom: 4, fontSize: '10px' }}>{label}</div>
        <div style={{
          color: getScoreColor(score),
          fontWeight: 700,
          fontSize: '18px',
          letterSpacing: '-1px',
          textShadow: `0 0 12px ${getScoreColor(score)}44`,
        }}>
          {score.toLocaleString()}
        </div>
        <div style={{ color: 'var(--text-muted)', fontSize: '10px', marginTop: 2 }}>
          {(score / 100).toFixed(2)}% human
        </div>
      </div>
    );
  };

  const gradientId = 'scoreGradientEnhanced';

  return (
    <div style={{ position: 'relative' }}>
      <div style={{
        position: 'absolute',
        right: 0,
        top: 0,
        display: 'flex',
        flexDirection: 'column',
        gap: 6,
        zIndex: 1,
        pointerEvents: 'none',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          <div style={{ width: 12, height: 1, background: 'var(--signal-human)', opacity: 0.5 }} />
          <span style={{
            fontSize: '8px',
            color: 'var(--signal-human)',
            letterSpacing: '1px',
            fontFamily: 'var(--font-mono)',
            opacity: 0.6,
            fontWeight: 700,
          }}>
            7000 HUMAN
          </span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          <div style={{ width: 12, height: 1, background: 'var(--signal-uncertain)', opacity: 0.5 }} />
          <span style={{
            fontSize: '8px',
            color: 'var(--signal-uncertain)',
            letterSpacing: '1px',
            fontFamily: 'var(--font-mono)',
            opacity: 0.6,
            fontWeight: 700,
          }}>
            5000 UNCERTAIN
          </span>
        </div>
      </div>

      <ResponsiveContainer width="100%" height={height}>
        <AreaChart data={chartData} margin={{ top: 12, right: 8, bottom: 0, left: -24 }}>
          <defs>
            <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={accentColor} stopOpacity={0.3} />
              <stop offset="100%" stopColor={accentColor} stopOpacity={0} />
            </linearGradient>
          </defs>

          <CartesianGrid
            strokeDasharray="2 8"
            stroke="rgba(255,255,255,0.04)"
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
            strokeOpacity={0.4}
            strokeWidth={1}
            label={{
              value: 'HUMAN',
              position: 'insideTopLeft',
              fontSize: 9,
              fill: 'var(--signal-human)',
              fontFamily: 'var(--font-mono)',
            }}
          />

          <ReferenceLine
            y={5000}
            stroke="var(--signal-uncertain)"
            strokeDasharray="3 5"
            strokeOpacity={0.4}
            strokeWidth={1}
            label={{
              value: 'UNCERTAIN',
              position: 'insideTopLeft',
              fontSize: 9,
              fill: 'var(--signal-uncertain)',
              fontFamily: 'var(--font-mono)',
            }}
          />

          <Area
            type="monotoneX"
            dataKey="score"
            stroke={accentColor}
            strokeWidth={2}
            fill={`url(#${gradientId})`}
            dot={false}
            activeDot={{
              r: 5,
              fill: '#ffffff',
              stroke: accentColor,
              strokeWidth: 2,
            }}
            animationDuration={300}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
