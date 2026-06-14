import { useState, useEffect, useRef, useCallback } from 'react';
import ScoreGauge from './ScoreGauge';
import ScoreChart from './ScoreChart';
import FeatureWaterfall from './FeatureWaterfall';

function Skeleton() {
  return (
    <div className="panel" style={{ animation: 'fade-in-up 400ms 100ms var(--ease-out) both' }}>
      <div className="panel-header">
        <div className="panel-title">THE INTERROGATOR</div>
        <div className="panel-subtitle">Loading classifier...</div>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 16, padding: 24 }}>
        <div style={{ width: 200, height: 200, borderRadius: '50%', background: 'var(--surface-01)', animation: 'shimmer 1.5s ease-in-out infinite' }} />
        {[1, 2, 3].map((i) => (
          <div key={i} style={{ height: 20, width: `${60 + i * 10}%`, background: 'var(--surface-01)', borderRadius: 'var(--radius-sm)', animation: 'shimmer 1.5s ease-in-out infinite' }} />
        ))}
      </div>
    </div>
  );
}

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

  useEffect(() => {
    if (prevScoreRef.current !== ghostScore) {
      const direction = ghostScore > prevScoreRef.current ? 'up' : 'down';
      setScoreFlash(direction);
      prevScoreRef.current = ghostScore;
      const t = setTimeout(() => setScoreFlash(null), 1500);
      return () => clearTimeout(t);
    }
  }, [ghostScore]);

  const formatCountdown = (seconds) => {
    if (seconds === null) return '\u2014';
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m}:${String(s).padStart(2, '0')}`;
  };

  const getConnectionBadge = () => {
    switch (connectionStatus) {
      case 'connected':
        return { label: 'LIVE', bg: 'var(--signal-human-glow)', border: 'var(--signal-human-border)', color: 'var(--signal-human-text)' };
      case 'connecting':
        return { label: 'CONNECTING', bg: 'var(--signal-uncertain-glow)', border: 'var(--signal-uncertain-border)', color: 'var(--signal-uncertain-text)' };
      case 'error':
        return { label: 'OFFLINE', bg: 'var(--signal-agent-glow)', border: 'var(--signal-agent-border)', color: 'var(--signal-agent-text)' };
      default:
        return { label: connectionStatus.toUpperCase(), bg: 'var(--surface-01)', border: 'var(--border-subtle)', color: 'var(--text-muted)' };
    }
  };

  const connBadge = getConnectionBadge();

  if (loading) {
    return <Skeleton />;
  }

  return (
    <div className="panel" style={{ animation: 'fade-in-up 400ms 100ms var(--ease-out) both' }}>
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
        <div className="panel-header">
          <div className="panel-title">THE INTERROGATOR</div>
          <div className="panel-subtitle">XGBoost &middot; SHAP explainer</div>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 6 }}>
          <span className="badge" style={{ background: connBadge.bg, borderColor: connBadge.border, color: connBadge.color }}>
            {connectionStatus === 'connected' && (
              <span style={{ width: 5, height: 5, borderRadius: '50%', background: 'currentColor', animation: 'pulse-dot 2s ease-in-out infinite', display: 'inline-block' }} />
            )}
            {connBadge.label}
          </span>
          <span className="badge badge-purple" style={{ fontSize: '9px', padding: '2px 8px' }}>
            MODEL v{modelVersion || '?'}
          </span>
        </div>
      </div>

      {/* Score Section */}
      <div style={{
        background: 'var(--bg-elevated)',
        border: '1px solid var(--border-subtle)',
        borderRadius: 'var(--radius-lg)',
        padding: 'var(--space-4) var(--space-4) var(--space-5)',
        display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 'var(--space-3)',
        position: 'relative',
        overflow: 'hidden',
      }}>
        <div style={{
          position: 'absolute', top: 0, left: 0, right: 0, height: 1,
          background: 'linear-gradient(90deg, transparent, rgba(139,124,255,0.3), transparent)',
        }} />
        <ScoreGauge score={ghostScore} previousScore={previousScore} size={200} strokeWidth={14} />

        <div style={{ display: 'flex', gap: 0, width: '100%', maxWidth: 280, marginTop: 4 }}>
          <div style={{ flex: 1, textAlign: 'center', padding: 'var(--space-2) 0' }}>
            <div style={{ fontSize: '22px', fontWeight: '800', fontFamily: 'var(--font-mono)', color: 'var(--signal-human-text)', letterSpacing: '-1px' }}>
              {(ghostScore / 100).toFixed(1)}%
            </div>
            <div style={{ fontSize: 'var(--text-2xs)', color: 'var(--text-muted)', letterSpacing: '1.5px', textTransform: 'uppercase', fontWeight: 700, marginTop: 2 }}>
              P(Human)
            </div>
          </div>
          <div style={{ width: 1, background: 'linear-gradient(180deg, transparent, var(--border-subtle), transparent)', alignSelf: 'stretch' }} />
          <div style={{ flex: 1, textAlign: 'center', padding: 'var(--space-2) 0' }}>
            <div style={{ fontSize: '22px', fontWeight: '800', fontFamily: 'var(--font-mono)', color: 'var(--signal-agent-text)', letterSpacing: '-1px' }}>
              {((10000 - ghostScore) / 100).toFixed(1)}%
            </div>
            <div style={{ fontSize: 'var(--text-2xs)', color: 'var(--text-muted)', letterSpacing: '1.5px', textTransform: 'uppercase', fontWeight: 700, marginTop: 2 }}>
              P(Agent)
            </div>
          </div>
          <div style={{ width: 1, background: 'linear-gradient(180deg, transparent, var(--border-subtle), transparent)', alignSelf: 'stretch' }} />
          <div style={{ flex: 1, textAlign: 'center', padding: 'var(--space-2) 0' }}>
            <div style={{
              fontSize: '22px', fontWeight: '800', fontFamily: 'var(--font-mono)',
              color: nextUpdateCountdown !== null && nextUpdateCountdown < 30 ? 'var(--signal-uncertain-text)' : 'var(--text-secondary)',
              letterSpacing: '-1px',
              animation: nextUpdateCountdown !== null && nextUpdateCountdown < 30 ? 'pulse-dot 1s ease-in-out infinite' : 'none',
            }}>
              {formatCountdown(nextUpdateCountdown)}
            </div>
            <div style={{ fontSize: 'var(--text-2xs)', color: 'var(--text-muted)', letterSpacing: '1.5px', textTransform: 'uppercase', fontWeight: 700, marginTop: 2 }}>
              Next Update
            </div>
          </div>
        </div>
      </div>

      {/* Sliding Tab Switcher */}
      <div ref={tabContainerRef} style={{
        position: 'relative',
        background: 'var(--surface-00)',
        borderRadius: 'var(--radius-md)',
        padding: 3,
        border: '1px solid var(--border-subtle)',
      }}>
        <div style={{
          position: 'absolute',
          top: 3, bottom: 3,
          borderRadius: 'var(--radius-sm)',
          background: 'linear-gradient(135deg, rgba(139,124,255,0.15), rgba(139,124,255,0.05))',
          border: '1px solid var(--border-accent)',
          boxShadow: '0 0 12px rgba(139,124,255,0.1)',
          transition: 'transform 250ms cubic-bezier(0.22, 1, 0.36, 1), width 250ms cubic-bezier(0.22, 1, 0.36, 1)',
          ...tabIndicatorStyle,
        }} />
        {[
          { key: 'waterfall', label: 'SHAP Analysis' },
          { key: 'chart', label: 'Score History' },
        ].map(({ key, label }) => (
          <button
            key={key}
            ref={(el) => { tabRefs.current[key] = el; }}
            onClick={() => setActiveTab(key)}
            style={{
              flex: 1, padding: '7px 16px', borderRadius: 'var(--radius-sm)',
              border: 'none', position: 'relative', zIndex: 1,
              background: 'transparent',
              color: activeTab === key ? 'var(--accent-purple-bright)' : 'var(--text-muted)',
              fontSize: 'var(--text-xs)', fontWeight: activeTab === key ? '700' : '500',
              fontFamily: 'var(--font-sans)', cursor: 'pointer', letterSpacing: '0.5px',
              transition: 'color var(--duration-fast) ease',
              width: '50%',
            }}
          >
            {label}
          </button>
        ))}
      </div>

      <div style={{ flex: 1, minHeight: 0, overflow: 'hidden' }}>
        {activeTab === 'waterfall' ? (
          <div className="scroll-area" style={{ height: '100%' }}>
            <FeatureWaterfall contributions={featureContributions} maxFeatures={12} apiAvailable={apiAvailable} />
          </div>
        ) : (
          <div style={{ height: '100%', display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
            <ScoreChart data={scoreHistory} height={200} />
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 'var(--space-2)' }}>
              {[
                {
                  label: 'All-time High',
                  value: scoreHistory.length > 0 ? Math.max(...scoreHistory.map(p => p.score)).toLocaleString() : '\u2014',
                  color: 'var(--signal-human-text)',
                },
                {
                  label: 'All-time Low',
                  value: scoreHistory.length > 0 ? Math.min(...scoreHistory.map(p => p.score)).toLocaleString() : '\u2014',
                  color: 'var(--signal-agent-text)',
                },
                {
                  label: 'Data Points',
                  value: scoreHistory.length.toString(),
                  color: 'var(--text-secondary)',
                },
              ].map(({ label, value, color }) => (
                <div key={label} className="stat-card">
                  <div className="stat-label">{label}</div>
                  <div style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--text-lg)', fontWeight: '700', color }}>
                    {value}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
