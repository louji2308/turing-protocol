import { useEffect, useRef, useState } from 'react';
import AnimatedNumber from './AnimatedNumber';

function polarToCartesian(cx, cy, r, angleDeg) {
  const rad = ((angleDeg - 90) * Math.PI) / 180;
  return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) };
}

function describeArc(startDeg, endDeg, r, cx, cy) {
  const start = polarToCartesian(cx, cy, r, endDeg);
  const end = polarToCartesian(cx, cy, r, startDeg);
  const large = endDeg - startDeg > 180 ? 1 : 0;
  return `M ${start.x} ${start.y} A ${r} ${r} 0 ${large} 0 ${end.x} ${end.y}`;
}

export default function ScoreGauge({
  score = 5000,
  previousScore = 5000,
  size = 220,
}) {
  const [animatedScore, setAnimatedScore] = useState(0);
  const prevScoreRef = useRef(previousScore);

  useEffect(() => {
    setAnimatedScore(score);
  }, [score]);

  const cx = size / 2;
  const cy = size / 2;

  const ARC_DEG = 270;
  const START = 135;
  const END = START + ARC_DEG;
  const TRACK_W = 12;
  const rTrack = (size - 20) / 2;

  const fillRatio = Math.max(0, Math.min(1, animatedScore / 10000));
  const fillAngle = fillRatio * ARC_DEG;
  const fillEnd = START + fillAngle;
  const pct = (animatedScore / 100).toFixed(1);

  const getArcColor = (s) => {
    const r = s / 10000;
    if (r >= 0.70) return 'var(--signal-human)';
    if (r >= 0.50) return 'var(--signal-uncertain)';
    return 'var(--signal-agent)';
  };

  const arcColor = getArcColor(score);

  const getLabel = (s) => {
    if (s >= 8500) return 'DEFINITELY HUMAN';
    if (s >= 7000) return 'LIKELY HUMAN';
    if (s >= 5500) return 'UNCERTAIN';
    if (s >= 3000) return 'LIKELY AGENT';
    return 'DEFINITELY AGENT';
  };

  const getLabelColor = (s) => {
    if (s >= 7000) return 'var(--signal-human-text)';
    if (s >= 5000) return 'var(--signal-uncertain-text)';
    return 'var(--signal-agent-text)';
  };

  useEffect(() => {
    prevScoreRef.current = score;
  }, [score]);

  const trackArc = describeArc(START, END, rTrack, cx, cy);
  const filledArc = describeArc(START, fillEnd, rTrack, cx, cy);
  const capStart = polarToCartesian(cx, cy, rTrack, START);
  const capEnd = polarToCartesian(cx, cy, rTrack, END);
  const fillCap = polarToCartesian(cx, cy, rTrack, fillEnd);

  const majorTicks = Array.from({ length: 11 }, (_, i) => {
    const t = i / 10;
    const angle = START + t * ARC_DEG;
    const inner = polarToCartesian(cx, cy, rTrack - 6, angle);
    const outer = polarToCartesian(cx, cy, rTrack - 2, angle);
    const labelPos = polarToCartesian(cx, cy, rTrack + 12, angle);
    return { inner, outer, labelPos, val: Math.round(t * 10000), isFilled: t <= fillRatio };
  });

  return (
    <div style={{ position: 'relative', width: size, height: size, flexShrink: 0 }}>
      <svg
        width={size}
        height={size}
        viewBox={`0 0 ${size} ${size}`}
        style={{ overflow: 'visible' }}
      >
        <defs>
          {/* Glass blur backdrop */}
          <filter id="glass-bg">
            <feGaussianBlur stdDeviation="24" />
          </filter>

          {/* Glass specular highlight filter */}
          <filter id="glass-glow">
            <feGaussianBlur stdDeviation="4" result="blur" />
            <feComposite in="SourceGraphic" in2="blur" operator="over" />
          </filter>

          {/* Soft wave glow */}
          <filter id="wave-glow">
            <feGaussianBlur stdDeviation="8" result="blur" />
            <feComposite in="SourceGraphic" in2="blur" operator="over" />
          </filter>

          {/* Radial gradient for glass backdrop */}
          <radialGradient id="glass-backdrop" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="rgba(139,124,255,0.06)" />
            <stop offset="60%" stopColor="rgba(139,124,255,0.03)" />
            <stop offset="100%" stopColor="rgba(139,124,255,0)" />
          </radialGradient>

          {/* Glass track gradient */}
          <linearGradient id="track-glass" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="rgba(255,255,255,0.06)" />
            <stop offset="50%" stopColor="rgba(255,255,255,0.015)" />
            <stop offset="100%" stopColor="rgba(255,255,255,0.03)" />
          </linearGradient>

          {/* Fill glass gradient */}
          <linearGradient id="fill-glass" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="white" stopOpacity="0.25" />
            <stop offset="30%" stopColor="white" stopOpacity="0.05" />
            <stop offset="70%" stopColor="white" stopOpacity="0" />
            <stop offset="100%" stopColor="white" stopOpacity="0.08" />
          </linearGradient>

          <clipPath id="track-clip">
            <path d={trackArc} fill="none" stroke="white" strokeWidth={TRACK_W + 4} strokeLinecap="round" />
          </clipPath>
        </defs>

        {/* Frosted glass backdrop circle */}
        <circle cx={cx} cy={cy} r={rTrack + 16} fill="url(#glass-backdrop)" />
        <circle cx={cx} cy={cy} r={rTrack + 16} fill="none" stroke="rgba(255,255,255,0.03)" strokeWidth="1" />

        {/* Glass track ring */}
        <path
          d={trackArc}
          fill="none"
          stroke="url(#track-glass)"
          strokeWidth={TRACK_W + 4}
          strokeLinecap="round"
        />
        <path
          d={trackArc}
          fill="none"
          stroke="rgba(255,255,255,0.035)"
          strokeWidth={TRACK_W + 4}
          strokeLinecap="round"
          strokeDasharray="2 6"
        />

        {/* Track inner shadow */}
        <path
          d={describeArc(START, END, rTrack - TRACK_W / 2 - 1, cx, cy)}
          fill="none"
          stroke="rgba(0,0,0,0.3)"
          strokeWidth={1}
        />
        <path
          d={describeArc(START, END, rTrack + TRACK_W / 2 + 1, cx, cy)}
          fill="none"
          stroke="rgba(255,255,255,0.04)"
          strokeWidth={1}
        />

        {/* Under-glow wave - the smooth glass light emission */}
        <path
          d={filledArc}
          fill="none"
          stroke={arcColor}
          strokeWidth={TRACK_W + 16}
          strokeLinecap="round"
          opacity={0.06}
          className="wave-under"
        />
        <path
          d={filledArc}
          fill="none"
          stroke={arcColor}
          strokeWidth={TRACK_W + 8}
          strokeLinecap="round"
          opacity={0.04}
          className="wave-under-delay"
        />

        {/* Main glass fill - the liquid in the tube */}
        <path
          d={filledArc}
          fill="none"
          stroke={arcColor}
          strokeWidth={TRACK_W}
          strokeLinecap="round"
          filter="url(#glass-glow)"
        />

        {/* Glass specular highlight on fill (reflection) */}
        <path
          d={filledArc}
          fill="none"
          stroke="url(#fill-glass)"
          strokeWidth={TRACK_W - 2}
          strokeLinecap="round"
        />

          {/* End cap - glass bead */}
        {fillAngle > 0 && (
          <g filter="url(#glass-glow)">
            <circle cx={fillCap.x} cy={fillCap.y} r={TRACK_W / 2 + 4} fill={arcColor} opacity={0.08} className="wave-halo" />
            <circle cx={fillCap.x} cy={fillCap.y} r={TRACK_W / 2} fill={arcColor} opacity={0.6} />
            <circle cx={fillCap.x} cy={fillCap.y} r={TRACK_W / 2} fill="url(#fill-glass)" opacity={0.8} />
            <circle cx={fillCap.x - 2} cy={fillCap.y - 2} r={3} fill="white" opacity={0.6} />
          </g>
        )}

        {/* Track end dots */}
        <circle cx={capStart.x} cy={capStart.y} r={2} fill="rgba(255,255,255,0.1)" />
        <circle cx={capEnd.x} cy={capEnd.y} r={2} fill="rgba(255,255,255,0.1)" />

        {/* Tick marks */}
        {majorTicks.map((tick, i) => (
          <g key={i}>
            <line
              x1={tick.inner.x} y1={tick.inner.y}
              x2={tick.outer.x} y2={tick.outer.y}
              stroke={tick.isFilled ? arcColor : 'rgba(255,255,255,0.06)'}
              strokeWidth={1.2}
              opacity={tick.isFilled ? 0.7 : 0.3}
            />
            <text
              x={tick.labelPos.x}
              y={tick.labelPos.y + 3}
              textAnchor="middle"
              fill="var(--text-disabled)"
              fontSize="7"
              fontFamily="var(--font-mono)"
              fontWeight={600}
            >
              {tick.val.toLocaleString()}
            </text>
          </g>
        ))}

        {/* Center label */}
        <text
          x={cx}
          y={cy - 30}
          textAnchor="middle"
          fill="var(--text-muted)"
          fontSize="9"
          fontFamily="var(--font-mono)"
          letterSpacing="4"
          fontWeight="700"
        >
          P(HUMAN)
        </text>

        <foreignObject x={cx - 64} y={cy - 28} width={128} height={54}>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            height: '100%',
          }}>
            <AnimatedNumber
              value={animatedScore}
              duration={800}
              style={{
                fontSize: '52px',
                fontWeight: 800,
                fontFamily: 'var(--font-mono)',
                color: arcColor,
                letterSpacing: '-4px',
                lineHeight: 1,
                transition: 'color 400ms ease',
                filter: `drop-shadow(0 0 16px ${arcColor}66)`,
              }}
            />
          </div>
        </foreignObject>

        <text
          x={cx}
          y={cy + 34}
          textAnchor="middle"
          fill="var(--text-tertiary)"
          fontSize="9"
          fontFamily="var(--font-mono)"
          letterSpacing="1"
        >
          / 10000
        </text>

        <text
          x={cx}
          y={cy + 50}
          textAnchor="middle"
          fill={arcColor}
          fontSize="11"
          fontFamily="var(--font-mono)"
          fontWeight="700"
          opacity={0.6}
        >
          {pct}%
        </text>
      </svg>

      <div style={{
        position: 'absolute',
        bottom: -4,
        left: 0,
        right: 0,
        textAlign: 'center',
        fontSize: '10px',
        letterSpacing: '3px',
        fontWeight: '700',
        color: getLabelColor(score),
        fontFamily: 'var(--font-mono)',
        textTransform: 'uppercase',
        transition: 'color 400ms ease',
        textShadow: `0 0 24px ${getLabelColor(score)}44, 0 0 48px ${getLabelColor(score)}11`,
      }}>
        {getLabel(score)}
      </div>
    </div>
  );
}
