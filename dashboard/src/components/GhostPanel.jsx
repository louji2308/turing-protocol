import { useState } from 'react';
import { Activity, Zap, Eye, Clock, Copy } from 'lucide-react';
import { EXPLORER_URL } from '../config';

function Skeleton({ ghostAddress, currentHPS, ghostStatus }) {
  return (
    <div className="panel" style={{ animation: 'fade-in-up 400ms var(--ease-out) both' }}>
      <div className="panel-header">
        <div className="panel-title">THE GHOST AGENT</div>
        <div className="panel-subtitle">Loading agent status...</div>
      </div>
      {[1, 2, 3, 4].map((i) => (
        <div key={i} style={{
          height: i <= 2 ? 60 : 40, marginBottom: 8,
          background: 'linear-gradient(90deg, var(--surface-01) 25%, var(--surface-02) 50%, var(--surface-01) 75%)',
          backgroundSize: '200% 100%',
          borderRadius: 'var(--radius-md)',
          animation: 'shimmer 1.5s ease-in-out infinite',
        }} />
      ))}
    </div>
  );
}

export default function GhostPanel({ ghostAddress, currentHPS = 5000, ghostStatus = null, loading = false }) {
  const [copied, setCopied] = useState(false);

  const isRunning = ghostStatus?.running ?? false;
  const cycles = ghostStatus?.cycles ?? '\u2014';
  const trades = ghostStatus?.trades ?? '\u2014';
  const timingState = ghostStatus?.timing_state ?? '\u2014';
  const optimizerGen = ghostStatus?.optimizer?.generation ?? '\u2014';
  const optimizerBestHPS = ghostStatus?.optimizer?.best_hps ?? '\u2014';

  const actions = ghostStatus?.recent_actions ?? [];

  const modules = [
    {
      name: 'Timing Noise',
      icon: Clock,
      state: timingState === 'focused' ? 'FOCUSED' : timingState === 'distracted' ? 'DISTRACTED' : 'ACTIVE',
      color: timingState === 'distracted' ? 'var(--signal-uncertain-text)' : 'var(--signal-human-text)',
      detail: 'Log-normal delays',
    },
    {
      name: 'Gas Selector',
      icon: Zap,
      state: 'ACTIVE',
      color: 'var(--signal-human-text)',
      detail: '30% round prices',
    },
    {
      name: 'Portfolio Bias',
      icon: Activity,
      state: 'ACTIVE',
      color: 'var(--signal-human-text)',
      detail: 'Overconfidence +0.6',
    },
    {
      name: 'Param Optimizer',
      icon: Eye,
      state: optimizerGen !== '\u2014' ? `GEN ${optimizerGen}` : 'ACTIVE',
      color: 'var(--accent-purple)',
      detail: optimizerBestHPS !== '\u2014' ? `Best: ${optimizerBestHPS}` : 'Evolving...',
    },
  ];

  const getActionIcon = (type) => {
    switch (type) {
      case 'swap': return '\u21C4';
      case 'explore': return '\u25CE';
      case 'lp': return '\u2B21';
      case 'news': return '\u25C8';
      default: return '\u25CF';
    }
  };

  const getActionColor = (type) => {
    switch (type) {
      case 'swap': return 'var(--accent-purple)';
      case 'explore': return 'var(--signal-info)';
      case 'lp': return 'var(--signal-uncertain-text)';
      case 'news': return 'var(--signal-agent-text)';
      default: return 'var(--text-muted)';
    }
  };

  const handleCopy = () => {
    if (ghostAddress) {
      navigator.clipboard.writeText(ghostAddress);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  if (loading) {
    return <Skeleton />;
  }

  const SEGMENTS = 10;
  const fillRatio = Math.min(1, currentHPS / 7200);
  const filledSegments = Math.round(fillRatio * SEGMENTS);
  const progressColor = currentHPS >= 7200 ? 'var(--signal-human)' : currentHPS >= 5000 ? 'var(--signal-uncertain)' : 'var(--signal-agent)';

  return (
    <div className="panel" style={{ animation: 'fade-in-up 400ms var(--ease-out) both' }}>
      <div className="panel-header">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div className="panel-title">THE GHOST AGENT</div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            {isRunning && (
              <>
                <div style={{
                  width: 6, height: 6, borderRadius: '50%',
                  background: 'var(--signal-human)',
                  boxShadow: '0 0 6px var(--signal-human)',
                  animation: 'pulse-dot 2s ease-in-out infinite',
                }} />
                <span style={{ fontSize: 'var(--text-2xs)', color: 'var(--signal-human-text)', letterSpacing: '1px', fontWeight: 700 }}>
                  LIVE
                </span>
              </>
            )}
          </div>
        </div>
        <div className="panel-subtitle">
          Adversarial trading agent on Mantle
        </div>
      </div>

      {/* Ghost Avatar */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
        <div style={{
          position: 'relative',
          width: 48, height: 48, flexShrink: 0,
        }}>
          <svg viewBox="0 0 48 48" width={48} height={48}>
            <defs>
              <linearGradient id="ghost-grad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="rgba(139,124,255,0.3)" />
                <stop offset="100%" stopColor="rgba(79,70,229,0.1)" />
              </linearGradient>
            </defs>
            <ellipse cx="24" cy="26" rx="16" ry="18" fill="url(#ghost-grad)" stroke="rgba(139,124,255,0.4)" strokeWidth="1" />
            <circle cx="18" cy="22" r="3" fill="rgba(255,255,255,0.9)" />
            <circle cx="30" cy="22" r="3" fill="rgba(255,255,255,0.9)" />
            <circle cx="18" cy="22" r="1.5" fill="rgba(139,124,255,0.6)" style={{ animation: 'blink 5s ease-in-out infinite' }} />
            <circle cx="30" cy="22" r="1.5" fill="rgba(139,124,255,0.6)" style={{ animation: 'blink 5s ease-in-out infinite 0.3s' }} />
            <path d="M 14 32 Q 18 36 24 32 Q 30 36 34 32" fill="none" stroke="rgba(139,124,255,0.3)" strokeWidth="1" />
          </svg>
          <div style={{
            position: 'absolute', inset: -4,
            borderRadius: '50%',
            boxShadow: '0 0 20px rgba(139,124,255,0.3)',
            pointerEvents: 'none',
            animation: isRunning ? 'border-glow-pulse 3s ease-in-out infinite' : 'none',
          }} />
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: 'var(--text-2xs)', color: 'var(--text-muted)', letterSpacing: '1.5px', textTransform: 'uppercase', fontWeight: 700, marginBottom: 2 }}>
            Wallet
          </div>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--text-xs)' }}>
            <span style={{ color: 'var(--text-primary)' }}>{ghostAddress ? ghostAddress.slice(0, 4) : ''}</span>
            <span style={{ color: 'var(--text-muted)' }}>{ghostAddress ? ghostAddress.slice(4, -6) : 'Not configured'}</span>
            <span style={{ color: 'var(--accent-cyan)' }}>{ghostAddress ? ghostAddress.slice(-6) : ''}</span>
          </div>
        </div>
        <button
          onClick={handleCopy}
          style={{
            background: 'transparent', border: 'none', color: copied ? 'var(--signal-human-text)' : 'var(--text-muted)',
            cursor: 'pointer', padding: 4, borderRadius: 'var(--radius-sm)',
            transition: 'all var(--duration-fast) ease',
            opacity: 0.4,
          }}
          onMouseEnter={(e) => { e.currentTarget.style.opacity = '1'; }}
          onMouseLeave={(e) => { e.currentTarget.style.opacity = '0.4'; }}
          title="Copy address"
        >
          {copied ? (
            <span style={{ fontSize: 'var(--text-2xs)', fontWeight: 600, whiteSpace: 'nowrap' }}>Copied!</span>
          ) : (
            <Copy size={14} />
          )}
        </button>
      </div>

      {/* Wallet Address Card */}
      <div style={{
        background: 'var(--surface-00)',
        border: '1px solid var(--border-subtle)',
        borderRadius: 'var(--radius-md)',
        padding: 'var(--space-3) var(--space-4)',
        fontFamily: 'var(--font-mono)',
        fontSize: 'var(--text-2xs)',
        color: 'var(--text-tertiary)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
      }}>
        <div style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          <span style={{ color: 'var(--text-disabled)' }}>$ </span>
          {ghostAddress || '0x...'}
        </div>
        <a
          href={`${EXPLORER_URL}/address/${ghostAddress}`}
          target="_blank"
          rel="noopener noreferrer"
          style={{
            fontSize: 'var(--text-2xs)', color: 'var(--accent-purple)',
            textDecoration: 'none', padding: '2px 6px',
            borderRadius: 'var(--radius-sm)',
            border: '1px solid var(--accent-purple-border)',
            background: 'var(--accent-purple-glow)',
            flexShrink: 0,
          }}
        >
          Explorer
        </a>
      </div>

      {/* Segmented Progress Bar */}
      <div style={{
        background: 'var(--surface-00)',
        border: '1px solid var(--border-subtle)',
        borderRadius: 'var(--radius-md)',
        padding: 'var(--space-3) var(--space-4)',
      }}>
        <div style={{
          display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8,
        }}>
          <span style={{ fontSize: 'var(--text-2xs)', color: 'var(--text-muted)', letterSpacing: '1.5px', textTransform: 'uppercase', fontWeight: 700 }}>
            Progress to Target
          </span>
          <span style={{ fontSize: 'var(--text-xs)', fontFamily: 'var(--font-mono)',
            color: progressColor, fontWeight: 700,
          }}>
            {currentHPS} / 7200
          </span>
        </div>
        <div style={{ display: 'flex', gap: 3, height: 8 }}>
          {Array.from({ length: SEGMENTS }, (_, i) => (
            <div
              key={i}
              style={{
                flex: 1,
                background: i < filledSegments ? progressColor : 'var(--bg-elevated)',
                borderRadius: 2,
                transition: `background ${200 + i * 20}ms var(--ease-out)`,
                boxShadow: i < filledSegments ? `0 0 8px ${progressColor}` : 'none',
              }}
            />
          ))}
        </div>
        <div style={{ fontSize: 'var(--text-2xs)', color: 'var(--text-tertiary)', marginTop: 6, textAlign: 'right', fontFamily: 'var(--font-mono)' }}>
          {currentHPS >= 7200
            ? '\u2713 Target reached \u2014 POB eligible'
            : `${7200 - currentHPS} points to POB eligibility`}
        </div>
      </div>

      {/* Cycles/Trades */}
      <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
        <div className="stat-card" style={{ flex: 1, padding: 'var(--space-3)' }}>
          <div className="stat-label" style={{ fontSize: '9px' }}>Cycles</div>
          <div className="stat-value" style={{ fontSize: 'var(--text-xl)' }}>
            {typeof cycles === 'number' ? cycles.toLocaleString() : cycles}
          </div>
        </div>
        <div className="stat-card" style={{ flex: 1, padding: 'var(--space-3)' }}>
          <div className="stat-label" style={{ fontSize: '9px' }}>Trades</div>
          <div className="stat-value" style={{ fontSize: 'var(--text-xl)' }}>
            {typeof trades === 'number' ? trades.toLocaleString() : trades}
          </div>
        </div>
      </div>

      {/* Behavioral Modules */}
      <div>
        <div className="label-caps" style={{ marginBottom: 8 }}>Behavioral Modules</div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
          {modules.map((mod) => {
            const Icon = mod.icon;
            return (
              <div key={mod.name} className="data-row" style={{ padding: 'var(--space-2) var(--space-3)' }}>
                <div style={{
                  width: 28, height: 28, borderRadius: '50%',
                  background: `${mod.color}15`,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  flexShrink: 0,
                  transition: 'all var(--duration-fast) ease',
                }}>
                  <Icon size={12} color={mod.color} />
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-secondary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {mod.name}
                  </div>
                  <div style={{ fontSize: 'var(--text-2xs)', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                    {mod.detail}
                  </div>
                </div>
                <span className="badge" style={{
                  background: mod.color === 'var(--accent-purple)' ? 'var(--accent-purple-glow)' : mod.color === 'var(--signal-uncertain-text)' ? 'var(--signal-uncertain-glow)' : 'var(--signal-human-glow)',
                  borderColor: mod.color === 'var(--accent-purple)' ? 'var(--accent-purple-border)' : mod.color === 'var(--signal-uncertain-text)' ? 'var(--signal-uncertain-border)' : 'var(--signal-human-border)',
                  color: mod.color,
                  fontSize: '9px',
                }}>
                  {mod.state}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Recent Activity */}
      <div style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column', gap: 8 }}>
        <div className="label-caps">Recent Activity</div>
        <div className="scroll-area" style={{ flex: 1 }}>
          {actions.length === 0 ? (
            <div style={{
              height: '100%', minHeight: 90, display: 'flex', flexDirection: 'column',
              alignItems: 'center', justifyContent: 'center', gap: 6, textAlign: 'center',
              border: '1px dashed var(--border-subtle)', borderRadius: 'var(--radius-md)',
              padding: 'var(--space-4)',
            }}>
              <Activity size={18} color="var(--text-disabled)" />
              <div style={{ fontSize: 'var(--text-2xs)', color: 'var(--text-muted)', maxWidth: 200, lineHeight: 1.5 }}>
                Live action feed requires the ghost agent telemetry endpoint. On-chain score is tracked above.
              </div>
            </div>
          ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
            {actions.map((action, i) => (
              <div
                key={i}
                className="data-row"
                style={{ padding: 'var(--space-2) var(--space-3)', animation: `slide-in-right ${150 + i * 60}ms var(--ease-out) both` }}
              >
                <span style={{ fontSize: '14px', color: getActionColor(action.type), width: 20, textAlign: 'center', flexShrink: 0 }}>
                  {getActionIcon(action.type)}
                </span>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {action.detail}
                  </div>
                  {action.delay && action.delay !== '\u2014' && (
                    <div style={{ fontSize: 'var(--text-2xs)', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                      delay: {action.delay}
                    </div>
                  )}
                </div>
                <div style={{ textAlign: 'right', flexShrink: 0 }}>
                  <div style={{ fontSize: 'var(--text-2xs)', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                    {action.time}
                  </div>
                  <div style={{ fontSize: 'var(--text-2xs)', color: action.status === 'success' ? 'var(--signal-human-text)' : 'var(--signal-agent-text)' }}>
                    {action.status}
                  </div>
                </div>
              </div>
            ))}
          </div>
          )}
        </div>
      </div>
    </div>
  );
}
