import { useEffect, useRef, useState } from 'react';

export default function ScoreGauge({
  score = 5000,
  previousScore = 5000,
  size = 220,
  strokeWidth = 12,
}) {
  const [displayScore, setDisplayScore] = useState(score);
  const [isAnimating, setIsAnimating] = useState(false);
  const animRef = useRef(null);
  const startRef = useRef(score);
  const startTimeRef = useRef(null);

  useEffect(() => {
    if (animRef.current) cancelAnimationFrame(animRef.current);
    startRef.current = displayScore;
    startTimeRef.current = null;
    setIsAnimating(true);

    const DURATION = 800;
    const target = score;
    const start = startRef.current;

    const animate = (timestamp) => {
      if (!startTimeRef.current) startTimeRef.current = timestamp;
      const elapsed = timestamp - startTimeRef.current;
      const progress = Math.min(elapsed / DURATION, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      const current = Math.round(start + (target - start) * eased);
      setDisplayScore(current);

      if (progress < 1) {
        animRef.current = requestAnimationFrame(animate);
      } else {
        setIsAnimating(false);
      }
    };

    animRef.current = requestAnimationFrame(animate);
    return () => { if (animRef.current) cancelAnimationFrame(animRef.current); };
  }, [score]);

  const center = size / 2;
  const radius = (size - strokeWidth * 2) / 2;
  const circumference = 2 * Math.PI * radius;

  const ARC_DEGREES = 270;
  const START_ANGLE = 135;
  const arcLength = (ARC_DEGREES / 360) * circumference;

  const fillRatio = Math.max(0, Math.min(1, score / 10000));
  const fillLength = fillRatio * arcLength;
  const dashOffset = arcLength - fillLength;

  const getArcColor = (s) => {
    const ratio = s / 10000;
    if (ratio >= 0.70) return 'var(--signal-human)';
    if (ratio >= 0.50) return 'var(--signal-uncertain)';
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

  const polarToCartesian = (cx, cy, r, angleDeg) => {
    const rad = ((angleDeg - 90) * Math.PI) / 180;
    return {
      x: cx + r * Math.cos(rad),
      y: cy + r * Math.sin(rad),
    };
  };

  const makeArc = (startDeg, endDeg, r) => {
    const start = polarToCartesian(center, center, r, endDeg);
    const end = polarToCartesian(center, center, r, startDeg);
    const largeArcFlag = endDeg - startDeg <= 180 ? '0' : '1';
    return `M ${start.x} ${start.y} A ${r} ${r} 0 ${largeArcFlag} 0 ${end.x} ${end.y}`;
  };

  const arcPath = makeArc(START_ANGLE, START_ANGLE + ARC_DEGREES, radius);

  const ticks = [0, 0.25, 0.5, 0.75, 1.0].map(t => {
    const angle = START_ANGLE + t * ARC_DEGREES;
    const inner = polarToCartesian(center, center, radius - 8, angle);
    const outer = polarToCartesian(center, center, radius + 4, angle);
    return { inner, outer, t };
  });

  const scoreChanged = score !== previousScore;
  const scoreIncreased = score > previousScore;

  return (
    <div style={{ position: 'relative', width: size, height: size, flexShrink: 0 }}>
      <svg
        width={size}
        height={size}
        viewBox={`0 0 ${size} ${size}`}
        style={{ overflow: 'visible' }}
      >
        <path
          d={arcPath}
          fill="none"
          stroke="var(--bg-elevated)"
          strokeWidth={strokeWidth}
          strokeLinecap="round"
        />

        <path
          d={arcPath}
          fill="none"
          stroke={arcColor}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={`${fillLength} ${circumference}`}
          style={{
            transition: 'stroke-dasharray 600ms cubic-bezier(0.16, 1, 0.3, 1), stroke 400ms ease',
            filter: `drop-shadow(0 0 6px ${arcColor})`,
          }}
        />

        <path
          d={arcPath}
          fill="none"
          stroke={arcColor}
          strokeWidth={strokeWidth * 2.5}
          strokeLinecap="round"
          strokeDasharray={`${fillLength} ${circumference}`}
          style={{
            opacity: 0.12,
            transition: 'stroke-dasharray 600ms cubic-bezier(0.16, 1, 0.3, 1)',
          }}
        />

        {ticks.map(({ inner, outer, t }) => (
          <line
            key={t}
            x1={inner.x} y1={inner.y}
            x2={outer.x} y2={outer.y}
            stroke="var(--border-default)"
            strokeWidth={t === 0 || t === 1 ? 2 : 1}
          />
        ))}

        <text
          x={center}
          y={center - 28}
          textAnchor="middle"
          fill="var(--text-tertiary)"
          fontSize="11"
          fontFamily="var(--font-mono)"
          letterSpacing="1"
        >
          P(HUMAN)
        </text>

        <text
          x={center}
          y={center + 16}
          textAnchor="middle"
          fill={arcColor}
          fontSize="48"
          fontFamily="var(--font-mono)"
          fontWeight="700"
          letterSpacing="-2"
          style={{
            transition: 'fill 400ms ease',
            filter: isAnimating ? `drop-shadow(0 0 12px ${arcColor})` : 'none',
          }}
        >
          {displayScore.toLocaleString()}
        </text>

        <text
          x={center}
          y={center + 34}
          textAnchor="middle"
          fill="var(--text-muted)"
          fontSize="10"
          fontFamily="var(--font-mono)"
        >
          / 10000
        </text>
      </svg>

      <div style={{
        position: 'absolute',
        bottom: -8,
        left: 0,
        right: 0,
        textAlign: 'center',
        fontSize: '10px',
        letterSpacing: '2px',
        fontWeight: '600',
        color: getLabelColor(score),
        fontFamily: 'var(--font-mono)',
        textTransform: 'uppercase',
        transition: 'color 400ms ease',
      }}>
        {getLabel(score)}
      </div>

      {scoreChanged && (
        <div style={{
          position: 'absolute',
          top: 8,
          right: 8,
          fontSize: '18px',
          color: scoreIncreased ? 'var(--signal-human)' : 'var(--signal-agent)',
          animation: 'slide-in-right 300ms ease both',
        }}>
          {scoreIncreased ? '\u2191' : '\u2193'}
        </div>
      )}
    </div>
  );
}
