import { useState, useEffect } from 'react';
import { Activity, Zap, Eye, Clock } from 'lucide-react';
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
  const [recentActions, setRecentActions] = useState([]);
  const [tick, setTick] = useState(0);

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

  if (loading) {
    return <Skeleton />;
  }

  const getActionColor = (type) => {
    switch (type) {
      case 'swap': return 'var(--accent-purple)';
      case 'explore': return 'var(--signal-info)';
      case 'lp': return 'var(--signal-uncertain-text)';
      case 'news': return 'var(--signal-agent-text)';
      default: return 'var(--text-muted)';
    }
  };

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
                <span style={{ fontSize: 'var(--text-2xs)', color: 'var(--signal-human-text)', letterSpacing: '1px' }}>
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

      <div style={{
        background: 'var(--surface-01)',
        border: '1px solid var(--border-subtle)',
        borderRadius: 'var(--radius-md)',
        padding: 'var(--space-3) var(--space-4)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
      }}>
        <div>
          <div style={{ fontSize: 'var(--text-2xs)', color: 'var(--text-muted)', letterSpacing: '1px', textTransform: 'uppercase', marginBottom: 3 }}>
            Wallet
          </div>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--text-xs)', color: 'var(--text-secondary)' }}>
            {ghostAddress
              ? `${ghostAddress.slice(0, 8)}...${ghostAddress.slice(-6)}`
              : 'Not configured'}
          </div>
        </div>
        <a
          href={`${EXPLORER_URL}/address/${ghostAddress}`}
          target="_blank"
          rel="noopener noreferrer"
          style={{
            display: 'flex', alignItems: 'center', gap: 4,
            fontSize: 'var(--text-xs)', color: 'var(--accent-purple)',
            textDecoration: 'none', padding: '4px 8px',
            borderRadius: 'var(--radius-sm)',
            border: '1px solid var(--accent-purple-border)',
            background: 'var(--accent-purple-glow)',
          }}
        >
          Explorer
        </a>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-2)' }}>
        <div className="stat-card">
          <div className="stat-label">Cycles</div>
          <div className="stat-value" style={{ fontSize: 'var(--text-xl)' }}>
            {typeof cycles === 'number' ? cycles.toLocaleString() : cycles}
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Trades</div>
          <div className="stat-value" style={{ fontSize: 'var(--text-xl)' }}>
            {typeof trades === 'number' ? trades.toLocaleString() : trades}
          </div>
        </div>
      </div>

      <div style={{
        background: 'var(--surface-01)',
        border: '1px solid var(--border-subtle)',
        borderRadius: 'var(--radius-md)',
        padding: 'var(--space-3) var(--space-4)',
      }}>
        <div style={{
          display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8,
        }}>
          <span style={{ fontSize: 'var(--text-2xs)', color: 'var(--text-muted)', letterSpacing: '1px', textTransform: 'uppercase' }}>
            Progress to Target
          </span>
          <span style={{ fontSize: 'var(--text-xs)', fontFamily: 'var(--font-mono)',
            color: currentHPS >= 7200 ? 'var(--signal-human-text)' : 'var(--signal-uncertain-text)',
          }}>
            {currentHPS} / 7200
          </span>
        </div>
        <div style={{ height: 6, background: 'var(--bg-elevated)', borderRadius: 3, overflow: 'hidden' }}>
          <div style={{
            height: '100%',
            width: `${Math.min(100, (currentHPS / 7200) * 100)}%`,
            background: currentHPS >= 7200 ? 'var(--signal-human)' : 'var(--signal-uncertain)',
            borderRadius: 3, transition: 'width 600ms var(--ease-out)',
            boxShadow: currentHPS >= 7200 ? '0 0 8px var(--signal-human)' : '0 0 8px var(--signal-uncertain)',
          }} />
        </div>
        <div style={{ fontSize: 'var(--text-2xs)', color: 'var(--text-muted)', marginTop: 6, textAlign: 'right' }}>
          {currentHPS >= 7200
            ? '\u2713 Target reached \u2014 POB eligible'
            : `${7200 - currentHPS} points to POB eligibility`}
        </div>
      </div>

      <div>
        <div className="label-caps" style={{ marginBottom: 8 }}>Behavioral Modules</div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
          {modules.map((mod) => {
            const Icon = mod.icon;
            return (
              <div key={mod.name} className="data-row" style={{ padding: 'var(--space-2) var(--space-3)' }}>
                <Icon size={12} color={mod.color} style={{ flexShrink: 0 }} />
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-secondary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {mod.name}
                  </div>
                  <div style={{ fontSize: 'var(--text-2xs)', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                    {mod.detail}
                  </div>
                </div>
                <span className="badge badge-green" style={{
                  background: mod.color === 'var(--accent-purple)' ? 'var(--accent-purple-glow)' : mod.color === 'var(--signal-uncertain-text)' ? 'var(--signal-uncertain-glow)' : 'var(--signal-human-glow)',
                  borderColor: mod.color === 'var(--accent-purple)' ? 'var(--accent-purple-border)' : mod.color === 'var(--signal-uncertain-text)' ? 'var(--signal-uncertain-border)' : 'var(--signal-human-border)',
                  color: mod.color,
                }}>
                  {mod.state}
                </span>
              </div>
            );
          })}
        </div>
      </div>

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
