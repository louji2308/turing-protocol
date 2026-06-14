import { useState, useEffect, useRef, useCallback } from 'react';
import { UserCheck, Bot, Timer } from 'lucide-react';
import ScoreGauge from './ScoreGauge';
import ScoreChart from './ScoreChart';
import FeatureWaterfall from './FeatureWaterfall';

/* ── OutputTab — three equal-height vertical glass metric cards ── */
function OutputTab({ ghostScore, nextUpdateCountdown, formatCountdown }) {
  const humanPct   = (ghostScore / 100).toFixed(1);
  const agentPct   = ((10000 - ghostScore) / 100).toFixed(1);
  const countdown  = formatCountdown(nextUpdateCountdown);
  const updateFill = nextUpdateCountdown != null ? Math.max(0, Math.min(100, ((60 - nextUpdateCountdown) / 60) * 100)) : 0;

  const metrics = [
    {
      id: 'human',
      label: 'HUMAN',
      sublabel: 'Probability Score',
      value: `${humanPct}%`,
      fillPct: parseFloat(humanPct),
      icon: UserCheck,
      accentColor: 'var(--signal-human)',
      borderColor: 'var(--signal-human-border)',
      glowColor: 'rgba(0,255,163,0.18)',
      textColor: 'var(--signal-human-text)',
      bgGradient: 'linear-gradient(135deg, rgba(0,255,163,0.10) 0%, rgba(0,255,163,0.04) 50%, rgba(6,8,18,0.7) 100%)',
      barGradient: 'linear-gradient(90deg, rgba(0,255,163,0.6), #00ffa3)',
    },
    {
      id: 'agent',
      label: 'AGENT',
      sublabel: 'Probability Score',
      value: `${agentPct}%`,
      fillPct: parseFloat(agentPct),
      icon: Bot,
      accentColor: 'var(--signal-agent)',
      borderColor: 'var(--signal-agent-border)',
      glowColor: 'rgba(255,51,85,0.18)',
      textColor: 'var(--signal-agent-text)',
      bgGradient: 'linear-gradient(135deg, rgba(255,51,85,0.10) 0%, rgba(255,51,85,0.04) 50%, rgba(6,8,18,0.7) 100%)',
      barGradient: 'linear-gradient(90deg, rgba(255,51,85,0.6), #ff3355)',
    },
    {
      id: 'timer',
      label: 'NEXT UPDATE',
      sublabel: 'Time Remaining',
      value: countdown,
      fillPct: updateFill,
      icon: Timer,
      accentColor: 'var(--accent-purple)',
      borderColor: 'var(--accent-purple-border)',
      glowColor: 'rgba(139,124,255,0.18)',
      textColor: 'var(--accent-purple-bright)',
      bgGradient: 'linear-gradient(135deg, rgba(139,124,255,0.10) 0%, rgba(139,124,255,0.04) 50%, rgba(6,8,18,0.7) 100%)',
      barGradient: 'linear-gradient(90deg, rgba(139,124,255,0.6), var(--accent-purple))',
    },
  ];

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      gap: 'var(--space-3)',
      height: '100%',
      paddingTop: 'var(--space-1)',
    }}>
      <div style={{
        fontSize: 'var(--text-2xs)',
        color: 'var(--text-muted)',
        letterSpacing: '3px',
        textTransform: 'uppercase',
        fontWeight: 700,
        paddingLeft: 2,
        marginBottom: 'var(--space-1)',
      }}>
        Agent Classification
      </div>

      {metrics.map((m, i) => {
        const Icon = m.icon;
        return (
          <div
            key={m.id}
            className="output-metric-card"
            style={{
              flex: 1,
              background: m.bgGradient,
              borderColor: m.borderColor,
              boxShadow: `inset 0 1px 0 rgba(255,255,255,0.09), 0 4px 20px rgba(0,0,0,0.45), 0 0 40px ${m.glowColor}`,
              animation: `card-enter ${320 + i * 100}ms var(--ease-out) both`,
              animationDelay: `${i * 80}ms`,
            }}
            onMouseEnter={e => {
              e.currentTarget.style.transform = 'translateY(-3px) scale(1.010)';
              e.currentTarget.style.boxShadow = `inset 0 1px 0 rgba(255,255,255,0.12), 0 12px 36px rgba(0,0,0,0.6), 0 0 60px ${m.glowColor}`;
            }}
            onMouseLeave={e => {
              e.currentTarget.style.transform = 'translateY(0) scale(1)';
              e.currentTarget.style.boxShadow = `inset 0 1px 0 rgba(255,255,255,0.09), 0 4px 20px rgba(0,0,0,0.45), 0 0 40px ${m.glowColor}`;
            }}
          >
            {/* Top chromatic line */}
            <div style={{
              position: 'absolute', top: 0, left: 0, right: 0, height: 1,
              background: `linear-gradient(90deg, transparent, ${m.accentColor}55, transparent)`,
              zIndex: 2,
            }} />

            {/* Icon bubble */}
            <div
              className="output-metric-icon"
              style={{
                background: `linear-gradient(135deg, ${m.glowColor}, rgba(0,0,0,0.3))`,
                border: `1px solid ${m.borderColor}`,
                boxShadow: `0 0 24px ${m.glowColor}, inset 0 1px 0 rgba(255,255,255,0.1)`,
                color: m.textColor,
              }}
            >
              <Icon size={22} strokeWidth={1.8} />
            </div>

            {/* Content */}
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{
                fontSize: 'var(--text-2xs)',
                color: 'var(--text-muted)',
                letterSpacing: '2.5px',
                textTransform: 'uppercase',
                fontWeight: 700,
                marginBottom: 2,
              }}>
                {m.label}
              </div>
              <div style={{
                fontSize: 'var(--text-xs)',
                color: 'var(--text-tertiary)',
                marginBottom: 'var(--space-2)',
                lineHeight: 1.3,
              }}>
                {m.sublabel}
              </div>

              {/* Large value */}
              <div
                className="output-metric-value"
                style={{
                  fontSize: '30px',
                  color: m.textColor,
                  textShadow: `0 0 28px ${m.accentColor}60, 0 0 56px ${m.accentColor}28`,
                  animation: `count-pop 700ms ${i * 80}ms var(--ease-spring) both`,
                }}
              >
                {m.value}
              </div>

              {/* Progress bar */}
              <div
                className="output-metric-bar-track"
                style={{ marginTop: 'var(--space-3)' }}
              >
                <div
                  className="output-metric-bar-fill"
                  style={{
                    width: `${m.fillPct}%`,
                    background: m.barGradient,
                    boxShadow: `0 0 10px ${m.accentColor}60`,
                    animationDelay: `${i * 80 + 200}ms`,
                  }}
                />
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

/* ── Skeleton ── */
function Skeleton() {
  return (
    <div className="panel" style={{ animation: 'fade-in-up 400ms 100ms var(--ease-out) both' }}>
      <div className="panel-header">
        <div className="panel-title">THE INTERROGATOR</div>
        <div className="panel-subtitle">Loading classifier...</div>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 16, padding: 24 }}>
        <div style={{
          width: 200, height: 200, borderRadius: '50%',
          background: 'linear-gradient(90deg, var(--surface-01) 25%, var(--surface-02) 50%, var(--surface-01) 75%)',
          backgroundSize: '200% 100%',
          animation: 'shimmer 1.5s ease-in-out infinite',
        }} />
        {[1, 2, 3].map(i => (
          <div key={i} style={{
            height: 20,
            width: `${60 + i * 10}%`,
            background: 'linear-gradient(90deg, var(--surface-01) 25%, var(--surface-02) 50%, var(--surface-01) 75%)',
            backgroundSize: '200% 100%',
            borderRadius: 'var(--radius-sm)',
            animation: 'shimmer 1.5s ease-in-out infinite',
          }} />
        ))}
      </div>
    </div>
  );
}

/* ── Main Component ── */
export default function InterrogatorPanel({
  ghostScore = 5000,
  previousScore = 5000,
  scoreHistory = [],
  featureContributions = [],
  lastUpdateTime = null,
  modelVersion = null,
  connectionStatus = 'connecting',
  loading = false,
  apiAvailable = true,
}) {
  const [activeTab, setActiveTab] = useState('waterfall');
  const [nextUpdateCountdown, setNextUpdateCountdown] = useState(null);
  const [scoreFlash, setScoreFlash] = useState(null);
  const [tabIndicatorStyle, setTabIndicatorStyle] = useState({});
  const prevScoreRef = useRef(ghostScore);
  const tabRefs = useRef({});
  const tabContainerRef = useRef(null);

  /* Tab indicator sliding underline */
  const updateTabIndicator = useCallback(() => {
    const el = tabRefs.current[activeTab];
    const container = tabContainerRef.current;
    if (el && container) {
      const containerRect = container.getBoundingClientRect();
      const elRect = el.getBoundingClientRect();
      setTabIndicatorStyle({
        width: elRect.width,
        transform: `translateX(${elRect.left - containerRect.left}px)`,
      });
    }
  }, [activeTab]);

  useEffect(() => {
    updateTabIndicator();
    window.addEventListener('resize', updateTabIndicator);
    return () => window.removeEventListener('resize', updateTabIndicator);
  }, [updateTabIndicator]);

  /* Countdown timer */
  useEffect(() => {
    if (!lastUpdateTime) return;
    const UPDATE_INTERVAL = 60;
    const tick = () => {
      const secondsSinceUpdate = Math.floor((Date.now() - lastUpdateTime.getTime()) / 1000);
      const remaining = UPDATE_INTERVAL - (secondsSinceUpdate % UPDATE_INTERVAL);
      setNextUpdateCountdown(remaining);
    };
    tick();
    const interval = setInterval(tick, 1000);
    return () => clearInterval(interval);
  }, [lastUpdateTime]);

  /* Score flash on change */
  useEffect(() => {
    if (prevScoreRef.current !== ghostScore) {
      const direction = ghostScore > prevScoreRef.current ? 'up' : 'down';
      setScoreFlash(direction);
      prevScoreRef.current = ghostScore;
      const t = setTimeout(() => setScoreFlash(null), 1500);
      return () => clearTimeout(t);
    }
  }, [ghostScore]);

  const formatCountdown = seconds => {
    if (seconds === null) return '—';
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m}:${String(s).padStart(2, '0')}`;
  };

  const getConnectionBadge = () => {
    switch (connectionStatus) {
      case 'connected':    return { label: 'LIVE',       bg: 'var(--signal-human-glow)',     border: 'var(--signal-human-border)',     color: 'var(--signal-human-text)' };
      case 'connecting':   return { label: 'CONNECTING', bg: 'var(--signal-uncertain-glow)', border: 'var(--signal-uncertain-border)', color: 'var(--signal-uncertain-text)' };
      case 'error':        return { label: 'OFFLINE',    bg: 'var(--signal-agent-glow)',     border: 'var(--signal-agent-border)',     color: 'var(--signal-agent-text)' };
      default:             return { label: connectionStatus.toUpperCase(), bg: 'var(--surface-01)', border: 'var(--border-subtle)', color: 'var(--text-muted)' };
    }
  };
  const connBadge = getConnectionBadge();

  /* Tabs — Score History removed, Output added */
  const tabs = [
    { key: 'waterfall', label: 'SHAP Analysis' },
    { key: 'output',    label: 'Output' },
  ];

  if (loading) return <Skeleton />;

  return (
    <div className="panel" style={{ animation: 'card-enter 400ms 100ms var(--ease-out) both', '--shine-delay': '2s' }}>

      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
        <div className="panel-header">
          <div className="panel-title">THE INTERROGATOR</div>
          <div className="panel-subtitle">XGBoost · SHAP Explainer</div>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 6 }}>
          <span className="badge" style={{ background: connBadge.bg, borderColor: connBadge.border, color: connBadge.color }}>
            {connectionStatus === 'connected' && (
              <span style={{
                width: 5, height: 5, borderRadius: '50%',
                background: 'currentColor',
                display: 'inline-block',
                animation: 'pulse-dot 2s ease-in-out infinite',
              }} />
            )}
            {connBadge.label}
          </span>
          <span className="badge badge-purple" style={{ fontSize: '9px', padding: '2px 8px' }}>
            MODEL v{modelVersion || '?'}
          </span>
        </div>
      </div>

      {/* Score Gauge Section */}
      <div style={{
        background: 'var(--bg-elevated)',
        border: '1px solid var(--border-subtle)',
        borderRadius: 'var(--radius-lg)',
        padding: 'var(--space-4) var(--space-4) var(--space-5)',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: 'var(--space-3)',
        position: 'relative',
        overflow: 'hidden',
        transition: 'box-shadow var(--duration-normal) ease',
        boxShadow: scoreFlash === 'up'
          ? '0 0 0 1px var(--signal-human-border), 0 0 40px rgba(0,255,163,0.15)'
          : scoreFlash === 'down'
          ? '0 0 0 1px var(--signal-agent-border), 0 0 40px rgba(255,51,85,0.15)'
          : 'none',
      }}>
        {/* Top highlight */}
        <div style={{
          position: 'absolute', top: 0, left: 0, right: 0, height: 1,
          background: 'linear-gradient(90deg, transparent, rgba(139,124,255,0.38), transparent)',
        }} />

        <ScoreGauge score={ghostScore} previousScore={previousScore} size={200} strokeWidth={14} />

        {/* Mini stats row below gauge */}
        <div style={{ display: 'flex', gap: 0, width: '100%', maxWidth: 290, marginTop: 4 }}>
          {[
            { label: 'P(Human)',    value: `${(ghostScore / 100).toFixed(1)}%`,         color: 'var(--signal-human-text)' },
            { label: 'P(Agent)',    value: `${((10000 - ghostScore) / 100).toFixed(1)}%`, color: 'var(--signal-agent-text)' },
            {
              label: 'Next Update',
              value: formatCountdown(nextUpdateCountdown),
              color: nextUpdateCountdown !== null && nextUpdateCountdown < 30 ? 'var(--signal-uncertain-text)' : 'var(--text-secondary)',
            },
          ].map(({ label, value, color }, i) => (
            <div key={label} style={{ flex: 1, textAlign: 'center', padding: 'var(--space-2) 0', position: 'relative' }}>
              {i > 0 && (
                <div style={{
                  position: 'absolute', left: 0, top: '15%', bottom: '15%', width: 1,
                  background: 'linear-gradient(180deg, transparent, var(--border-subtle), transparent)',
                }} />
              )}
              <div style={{
                fontSize: '20px', fontWeight: 800, fontFamily: 'var(--font-mono)',
                color, letterSpacing: '-1px',
                animation: `count-pop 600ms ${i * 100}ms var(--ease-spring) both`,
              }}>
                {value}
              </div>
              <div style={{
                fontSize: 'var(--text-2xs)', color: 'var(--text-muted)',
                letterSpacing: '1.5px', textTransform: 'uppercase', fontWeight: 700, marginTop: 2,
              }}>
                {label}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* ── TAB SWITCHER ── */}
      <div
        ref={tabContainerRef}
        style={{
          position: 'relative',
          background: 'var(--surface-00)',
          borderRadius: 'var(--radius-md)',
          padding: 3,
          border: '1px solid var(--border-subtle)',
          display: 'flex',
        }}
      >
        {/* Sliding glass indicator */}
        <div style={{
          position: 'absolute',
          top: 3, bottom: 3,
          borderRadius: 'var(--radius-sm)',
          background: 'linear-gradient(135deg, rgba(139,124,255,0.18), rgba(139,124,255,0.06))',
          border: '1px solid var(--border-accent)',
          boxShadow: '0 0 16px rgba(139,124,255,0.14)',
          transition: 'transform 260ms cubic-bezier(0.22, 1, 0.36, 1), width 260ms cubic-bezier(0.22, 1, 0.36, 1)',
          ...tabIndicatorStyle,
        }} />

        {tabs.map(({ key, label }) => (
          <button
            key={key}
            ref={el => { tabRefs.current[key] = el; }}
            onClick={() => setActiveTab(key)}
            style={{
              flex: 1,
              padding: '7px 16px',
              borderRadius: 'var(--radius-sm)',
              border: 'none',
              position: 'relative',
              zIndex: 1,
              background: 'transparent',
              color: activeTab === key ? 'var(--accent-purple-bright)' : 'var(--text-muted)',
              fontSize: 'var(--text-xs)',
              fontWeight: activeTab === key ? 700 : 500,
              fontFamily: 'var(--font-sans)',
              cursor: 'pointer',
              letterSpacing: '0.5px',
              transition: 'color var(--duration-fast) ease',
            }}
          >
            {label}
          </button>
        ))}
      </div>

      {/* ── TAB CONTENT ── */}
      <div style={{ flex: 1, minHeight: 0, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>

        {/* SHAP Analysis Tab */}
        {activeTab === 'waterfall' && (
          <div className="scroll-area" style={{ flex: 1, height: '100%' }}>
            <FeatureWaterfall
              contributions={featureContributions}
              maxFeatures={12}
              apiAvailable={apiAvailable}
            />
          </div>
        )}

        {/* Output Tab — 3 equal-height vertical cards */}
        {activeTab === 'output' && (
          <div style={{ flex: 1, height: '100%', display: 'flex', flexDirection: 'column' }}>
            <OutputTab
              ghostScore={ghostScore}
              nextUpdateCountdown={nextUpdateCountdown}
              formatCountdown={formatCountdown}
            />
          </div>
        )}

      </div>
    </div>
  );
}
