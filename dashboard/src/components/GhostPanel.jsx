import { useState } from 'react';
import { Activity, Zap, Eye, Clock, Copy } from 'lucide-react';
import { EXPLORER_URL } from '../config';

function Skeleton() {
  return (
    <div className="panel" style={{ animation: 'card-enter 400ms var(--ease-out) both' }}>
      <div className="panel-header">
        <div className="panel-title">THE GHOST AGENT</div>
        <div className="panel-subtitle">Loading agent status...</div>
      </div>
      {[1, 2, 3, 4].map(i => (
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

  const isRunning     = ghostStatus?.running ?? false;
  const cycles        = ghostStatus?.cycles ?? '—';
  const trades        = ghostStatus?.trades ?? '—';
  const timingState   = ghostStatus?.timing_state ?? '—';
  const optimizerGen  = ghostStatus?.optimizer?.generation ?? '—';
  const optimizerBest = ghostStatus?.optimizer?.best_hps ?? '—';
  const actions       = ghostStatus?.recent_actions ?? [];

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
      state: optimizerGen !== '—' ? `GEN ${optimizerGen}` : 'ACTIVE',
      color: 'var(--accent-purple)',
      detail: optimizerBest !== '—' ? `Best: ${optimizerBest}` : 'Evolving...',
    },
  ];

  const getActionIcon  = t => ({ swap: '⇄', explore: '◉', lp: '⬡', news: '◈' }[t] || '●');
  const getActionColor = t => ({ swap: 'var(--accent-purple)', explore: 'var(--signal-info)', lp: 'var(--signal-uncertain-text)', news: 'var(--signal-agent-text)' }[t] || 'var(--text-muted)');

  const handleCopy = () => {
    if (ghostAddress) {
      navigator.clipboard.writeText(ghostAddress);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  if (loading) return <Skeleton />;

  const SEGMENTS    = 10;
  const fillRatio   = Math.min(1, currentHPS / 7200);
  const filled      = Math.round(fillRatio * SEGMENTS);
  const progressColor = currentHPS >= 7200 ? 'var(--signal-human)' : currentHPS >= 5000 ? 'var(--signal-uncertain)' : 'var(--signal-agent)';

  return (
    <div className="panel" style={{ animation: 'card-enter 400ms var(--ease-out) both', '--shine-delay': '0s' }}>
      {/* Header */}
      <div className="panel-header">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div className="panel-title">THE GHOST AGENT</div>
          {isRunning && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <div style={{
                width: 6, height: 6, borderRadius: '50%',
                background: 'var(--signal-human)',
                boxShadow: '0 0 8px var(--signal-human)',
                animation: 'pulse-dot 2s ease-in-out infinite',
              }} />
              <span style={{ fontSize: 'var(--text-2xs)', color: 'var(--signal-human-text)', letterSpacing: '1px', fontWeight: 700 }}>
                LIVE
              </span>
            </div>
          )}
        </div>
        <div className="panel-subtitle">Adversarial trading agent on Mantle</div>
      </div>

      {/* Ghost Avatar + Address */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
        <div style={{ position: 'relative', width: 48, height: 48, flexShrink: 0 }}>
          <svg viewBox="0 0 48 48" width={48} height={48}>
            <defs>
              <linearGradient id="ghost-grad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%"   stopColor="rgba(139,124,255,0.35)" />
                <stop offset="100%" stopColor="rgba(79,70,229,0.12)" />
              </linearGradient>
            </defs>
            <ellipse cx="24" cy="26" rx="16" ry="18" fill="url(#ghost-grad)" stroke="rgba(139,124,255,0.45)" strokeWidth="1" />
            <circle cx="18" cy="22" r="3"   fill="rgba(255,255,255,0.92)" />
            <circle cx="30" cy="22" r="3"   fill="rgba(255,255,255,0.92)" />
            <circle cx="18" cy="22" r="1.5" fill="rgba(139,124,255,0.65)" style={{ animation: 'blink 5s ease-in-out infinite' }} />
            <circle cx="30" cy="22" r="1.5" fill="rgba(139,124,255,0.65)" style={{ animation: 'blink 5s ease-in-out infinite 0.3s' }} />
            <path d="M 14 32 Q 18 36 24 32 Q 30 36 34 32" fill="none" stroke="rgba(139,124,255,0.35)" strokeWidth="1" />
          </svg>
          <div style={{
            position: 'absolute', inset: -4,
            borderRadius: '50%',
            boxShadow: '0 0 24px rgba(139,124,255,0.32)',
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
          title="Copy address"
          style={{
            background: 'transparent', border: 'none',
            color: copied ? 'var(--signal-human-text)' : 'var(--text-muted)',
            cursor: 'pointer', padding: 4,
            borderRadius: 'var(--radius-sm)',
            transition: 'all var(--duration-fast) ease',
            opacity: 0.45,
          }}
          onMouseEnter={e => { e.currentTarget.style.opacity = '1'; }}
          onMouseLeave={e => { e.currentTarget.style.opacity = '0.45'; }}
        >
          {copied ? <span style={{ fontSize: 'var(--text-2xs)', fontWeight: 600 }}>Copied!</span> : <Copy size={14} />}
        </button>
      </div>

      {/* Explorer terminal card */}
      <div className="glass-card" style={{ padding: 'var(--space-3) var(--space-4)', fontFamily: 'var(--font-mono)', fontSize: 'var(--text-2xs)', color: 'var(--text-tertiary)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          <span style={{ color: 'var(--text-disabled)' }}>$ </span>
          {ghostAddress || '0x...'}
        </div>
        <a
          href={`${EXPLORER_URL}/address/${ghostAddress}`}
          target="_blank" rel="noopener noreferrer"
          style={{
            fontSize: 'var(--text-2xs)', color: 'var(--accent-purple)',
            textDecoration: 'none', padding: '2px 8px',
            borderRadius: 'var(--radius-sm)',
            border: '1px solid var(--accent-purple-border)',
            background: 'var(--accent-purple-glow)',
            flexShrink: 0,
            transition: 'all var(--duration-fast) ease',
          }}
        >
          Explorer
        </a>
      </div>

      {/* Segmented progress bar */}
      <div className="glass-card" style={{ padding: 'var(--space-3) var(--space-4)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
          <span style={{ fontSize: 'var(--text-2xs)', color: 'var(--text-muted)', letterSpacing: '1.5px', textTransform: 'uppercase', fontWeight: 700 }}>
            Progress to Target
          </span>
          <span style={{ fontSize: 'var(--text-xs)', fontFamily: 'var(--font-mono)', color: progressColor, fontWeight: 700 }}>
            {currentHPS.toLocaleString()} / 7,200
          </span>
        </div>
        <div style={{ display: 'flex', gap: 3, height: 9 }}>
          {Array.from({ length: SEGMENTS }, (_, i) => (
            <div key={i} style={{
              flex: 1,
              background: i < filled ? progressColor : 'var(--bg-elevated)',
              borderRadius: 3,
              transition: `background ${200 + i * 25}ms var(--ease-out)`,
              boxShadow: i < filled ? `0 0 10px ${progressColor}80` : 'none',
            }} />
          ))}
        </div>
        <div style={{ fontSize: 'var(--text-2xs)', color: 'var(--text-tertiary)', marginTop: 8, textAlign: 'right', fontFamily: 'var(--font-mono)' }}>
          {currentHPS >= 7200 ? '✓ Target reached — POB eligible' : `${(7200 - currentHPS).toLocaleString()} points to POB eligibility`}
        </div>
      </div>

      {/* Cycles / Trades */}
      <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
        {[
          { label: 'Cycles', value: typeof cycles === 'number' ? cycles.toLocaleString() : cycles },
          { label: 'Trades', value: typeof trades === 'number' ? trades.toLocaleString() : trades },
        ].map(({ label, value }, i) => (
          <div key={label} className="stat-card" style={{ flex: 1, padding: 'var(--space-3)', animation: `card-enter ${300 + i * 80}ms var(--ease-out) both` }}>
            <div className="stat-label" style={{ fontSize: '9px' }}>{label}</div>
            <div className="stat-value" style={{ fontSize: 'var(--text-xl)' }}>{value}</div>
          </div>
        ))}
      </div>

      {/* Behavioral modules */}
      <div>
        <div className="label-caps" style={{ marginBottom: 8 }}>Behavioral Modules</div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
          {modules.map((mod, i) => {
            const Icon = mod.icon;
            const badgeBg     = mod.color === 'var(--accent-purple)' ? 'var(--accent-purple-glow)' : mod.color === 'var(--signal-uncertain-text)' ? 'var(--signal-uncertain-glow)' : 'var(--signal-human-glow)';
            const badgeBorder = mod.color === 'var(--accent-purple)' ? 'var(--accent-purple-border)' : mod.color === 'var(--signal-uncertain-text)' ? 'var(--signal-uncertain-border)' : 'var(--signal-human-border)';
            return (
              <div
                key={mod.name}
                className="data-row"
                style={{
                  padding: 'var(--space-2) var(--space-3)',
                  animation: `data-stream ${200 + i * 60}ms var(--ease-out) both`,
                  '--row-delay': `${i * 60}`,
                }}
              >
                <div style={{
                  width: 30, height: 30, borderRadius: '50%',
                  background: `${mod.color}18`,
                  border: `1px solid ${mod.color}33`,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  flexShrink: 0,
                  boxShadow: `0 0 12px ${mod.color}25`,
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
                <span className="badge" style={{ background: badgeBg, borderColor: badgeBorder, color: mod.color, fontSize: '9px' }}>
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
              minHeight: 90, display: 'flex', flexDirection: 'column',
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
                  style={{ padding: 'var(--space-2) var(--space-3)', animation: `slide-in-right ${150 + i * 55}ms var(--ease-out) both` }}
                >
                  <span style={{ fontSize: 14, color: getActionColor(action.type), width: 20, textAlign: 'center', flexShrink: 0 }}>
                    {getActionIcon(action.type)}
                  </span>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {action.detail}
                    </div>
                    {action.delay && action.delay !== '—' && (
                      <div style={{ fontSize: 'var(--text-2xs)', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                        delay: {action.delay}
                      </div>
                    )}
                  </div>
                  <div style={{ textAlign: 'right', flexShrink: 0 }}>
                    <div style={{ fontSize: 'var(--text-2xs)', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>{action.time}</div>
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
