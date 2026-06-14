import {
  XAxis, YAxis, Tooltip, ResponsiveContainer,
  ReferenceLine, Area, AreaChart, CartesianGrid,
} from 'recharts';

function getScoreColor(s) {
  if (s >= 7000) return 'var(--signal-human)';
  if (s >= 5000) return 'var(--signal-uncertain)';
  return 'var(--signal-agent)';
}

export default function ScoreChart({ data = [], height = 280 }) {
  const chartData = data.length >= 2 ? data : [
    { time: '—', score: 5000, label: '' },
    { time: '—', score: 5000, label: '' },
  ];

  const latestScore = chartData[chartData.length - 1]?.score ?? 5000;
  const accentColor = getScoreColor(latestScore);
  const gradientId  = 'scoreGradElite';
  const glowId      = 'scoreGlowElite';

  const CustomTooltip = ({ active, payload, label }) => {
    if (!active || !payload || !payload.length) return null;
    const score = payload[0].value;
    const sColor = getScoreColor(score);
    return (
      <div style={{
        background: 'rgba(6,8,18,0.97)',
        border: `1px solid ${sColor}44`,
        borderRadius: 'var(--radius-md)',
        padding: '10px 14px',
        fontSize: '11px',
        fontFamily: 'var(--font-mono)',
        backdropFilter: 'blur(20px)',
        boxShadow: `var(--shadow-md), 0 0 30px ${sColor}22`,
      }}>
        <div style={{ color: 'var(--text-tertiary)', marginBottom: 4, fontSize: '10px' }}>{label}</div>
        <div style={{
          color: sColor,
          fontWeight: 700,
          fontSize: '20px',
          letterSpacing: '-1px',
          textShadow: `0 0 14px ${sColor}55`,
          animation: 'count-pop 300ms var(--ease-spring) both',
        }}>
          {score.toLocaleString()}
        </div>
        <div style={{ color: 'var(--text-muted)', fontSize: '10px', marginTop: 2 }}>
          {(score / 100).toFixed(2)}% human
        </div>
      </div>
    );
  };

  return (
    <div style={{
      position: 'relative',
      background: 'linear-gradient(180deg, rgba(255,255,255,0.018) 0%, rgba(0,0,0,0.2) 100%)',
      borderRadius: 'var(--radius-md)',
      border: '1px solid var(--border-subtle)',
      padding: '8px 0 4px',
      overflow: 'hidden',
    }}>
      {/* Top gradient accent line */}
      <div style={{
        position: 'absolute', top: 0, left: 0, right: 0, height: 1,
        background: `linear-gradient(90deg, transparent, ${accentColor}55, transparent)`,
      }} />

      {/* Legend */}
      <div style={{
        position: 'absolute', right: 12, top: 10,
        display: 'flex', flexDirection: 'column', gap: 5,
        zIndex: 1, pointerEvents: 'none',
      }}>
        {[
          { label: '7000 HUMAN',     color: 'var(--signal-human)' },
          { label: '5000 UNCERTAIN', color: 'var(--signal-uncertain)' },
        ].map(({ label, color }) => (
          <div key={label} style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
            <div style={{ width: 14, height: 1, background: color, opacity: 0.55 }} />
            <span style={{ fontSize: '8px', color, fontFamily: 'var(--font-mono)', opacity: 0.65, fontWeight: 700 }}>
              {label}
            </span>
          </div>
        ))}
      </div>

      <ResponsiveContainer width="100%" height={height}>
        <AreaChart data={chartData} margin={{ top: 14, right: 10, bottom: 0, left: -24 }}>
          <defs>
            <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%"   stopColor={accentColor} stopOpacity={0.40} />
              <stop offset="40%"  stopColor={accentColor} stopOpacity={0.14} />
              <stop offset="100%" stopColor={accentColor} stopOpacity={0.00} />
            </linearGradient>
            <filter id={glowId} x="-20%" y="-20%" width="140%" height="140%">
              <feGaussianBlur in="SourceGraphic" stdDeviation="3" result="blur" />
              <feComposite in="SourceGraphic" in2="blur" operator="over" />
            </filter>
          </defs>

          <CartesianGrid strokeDasharray="2 10" stroke="rgba(255,255,255,0.038)" vertical={false} />

          <XAxis
            dataKey="time"
            tick={{ fontSize: 9, fill: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}
            axisLine={false} tickLine={false}
            interval="preserveStartEnd"
          />
          <YAxis
            domain={[0, 10000]}
            tick={{ fontSize: 9, fill: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}
            axisLine={false} tickLine={false}
            tickCount={5}
            tickFormatter={v => v.toLocaleString()}
          />

          <Tooltip content={<CustomTooltip />} />

          <ReferenceLine
            y={7000}
            stroke="var(--signal-human)"
            strokeDasharray="3 6" strokeOpacity={0.42} strokeWidth={1}
          />
          <ReferenceLine
            y={5000}
            stroke="var(--signal-uncertain)"
            strokeDasharray="3 6" strokeOpacity={0.42} strokeWidth={1}
          />

          <Area
            type="monotoneX"
            dataKey="score"
            stroke={accentColor}
            strokeWidth={2.5}
            fill={`url(#${gradientId})`}
            dot={false}
            activeDot={{
              r: 5,
              fill: '#ffffff',
              stroke: accentColor,
              strokeWidth: 2.5,
              filter: `url(#${glowId})`,
            }}
            animationDuration={600}
            style={{ filter: `drop-shadow(0 0 6px ${accentColor}55)` }}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
