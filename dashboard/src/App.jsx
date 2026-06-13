import { useState, useEffect } from 'react';
import GhostPanel from './components/GhostPanel';
import InterrogatorPanel from './components/InterrogatorPanel';
import ProofLeaderboard from './components/ProofLeaderboard';
import RealclawTrustPanel from './components/RealclawTrustPanel';
import { WalletChecker } from './components/WalletChecker';
import { EcosystemPanel } from './components/EcosystemPanel';
import { SybilGraph } from './components/SybilGraph';
import { useOracleEvents } from './hooks/useOracleEvents';
import { useGhostTelemetry } from './hooks/useGhostTelemetry';
import { useScoreHistory } from './hooks/useScoreHistory';
import { useRealclawTrust } from './hooks/useRealclawTrust';
import { ExternalLink, Github, Activity } from 'lucide-react';

const GHOST_ADDRESS = import.meta.env.VITE_GHOST_ADDRESS || '0x0000000000000000000000000000000000000000';
const NETWORK_NAME = import.meta.env.VITE_NETWORK_NAME || 'Mantle Sepolia';

export default function App() {
  const [isLoaded, setIsLoaded] = useState(false);
  const [sybilClusters, setSybilClusters] = useState({});

  const {
    ghostScore,
    previousScore,
    scoreHistory: liveHistory,
    recentProofs,
    totalFreshProofs,
    totalMinted,
    oracleStats,
    connectionStatus,
    lastUpdateTime,
    modelVersion,
  } = useOracleEvents(GHOST_ADDRESS);

  const {
    featureContributions,
    ghostStatus,
    apiAvailable,
  } = useGhostTelemetry(GHOST_ADDRESS);

  const trust = useRealclawTrust(GHOST_ADDRESS);

  const { history: persistedHistory, addPoint } = useScoreHistory(GHOST_ADDRESS);

  useEffect(() => {
    if (liveHistory.length > 0) {
      const latest = liveHistory[liveHistory.length - 1];
      addPoint(latest.score, latest.label);
    }
  }, [liveHistory]);

  const combinedHistory = (() => {
    if (persistedHistory.length === 0 && liveHistory.length === 0) return [];
    if (persistedHistory.length > liveHistory.length) return persistedHistory;
    return liveHistory;
  })();

  useEffect(() => {
    const t = setTimeout(() => setIsLoaded(true), 100);
    return () => clearTimeout(t);
  }, []);

  useEffect(() => {
    const api = import.meta.env.VITE_API_URL || 'http://localhost:8080';
    fetch(`${api}/api/v1/intelligence/sybil-clusters`)
      .then((r) => r.ok ? r.json() : Promise.resolve({}))
      .then((data) => setSybilClusters(data?.clusters ?? {}))
      .catch(() => { /* API not available */ });
  }, []);

  const hasValidAddress = GHOST_ADDRESS !== '0x0000000000000000000000000000000000000000';

  const isLive = connectionStatus === 'connected';

  return (
    <>
      <div className="ambient-bg" aria-hidden="true">
        <div className="ambient-orb a" />
        <div className="ambient-orb b" />
        <div className="ambient-orb c" />
      </div>

      <div style={{
        maxWidth: 1680,
        margin: '0 auto',
        padding: 'var(--space-5) var(--space-5) 64px',
        display: 'flex',
        flexDirection: 'column',
        gap: 'var(--space-4)',
        boxSizing: 'border-box',
      }}>
        <header style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          flexWrap: 'wrap', gap: 'var(--space-4)',
          padding: 'var(--space-4) var(--space-5)',
          background: 'linear-gradient(180deg, rgba(255,255,255,0.04), rgba(255,255,255,0) 30%), var(--bg-panel)',
          borderRadius: 'var(--radius-xl)',
          border: '1px solid var(--border-default)',
          boxShadow: 'var(--shadow-md), inset 0 1px 0 rgba(255,255,255,0.05)',
          backdropFilter: 'blur(20px) saturate(140%)',
          WebkitBackdropFilter: 'blur(20px) saturate(140%)',
          position: 'sticky', top: 'var(--space-3)', zIndex: 50,
          animation: 'fade-in-up 300ms var(--ease-out) both',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-4)' }}>
            <div style={{
              position: 'relative',
              width: 42, height: 42, borderRadius: 12,
              background: 'linear-gradient(135deg, var(--accent-purple-dim), var(--accent-cyan))',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              boxShadow: '0 0 24px rgba(139,124,255,0.45), inset 0 1px 0 rgba(255,255,255,0.3)',
            }}>
              <Activity size={20} color="#fff" strokeWidth={2.4} />
            </div>
            <div>
              <div className="gradient-text" style={{ fontSize: 'var(--text-xl)', fontWeight: 800, letterSpacing: '-0.5px', lineHeight: 1 }}>
                TURING PROTOCOL
              </div>
              <div style={{ fontSize: 'var(--text-2xs)', color: 'var(--text-tertiary)', letterSpacing: '2px', textTransform: 'uppercase', marginTop: 4 }}>
                Behavioral Proof of Humanity {'\u00B7'} {NETWORK_NAME}
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-5)', flexWrap: 'wrap' }}>
            <div style={{
              display: 'flex', alignItems: 'center', gap: 7,
              padding: '5px 12px', borderRadius: 20,
              border: `1px solid ${isLive ? 'var(--signal-human-border)' : 'var(--signal-uncertain-border)'}`,
              background: isLive ? 'var(--signal-human-glow)' : 'var(--signal-uncertain-glow)',
            }}>
              <div style={{
                width: 7, height: 7, borderRadius: '50%',
                background: isLive ? 'var(--signal-human)' : connectionStatus === 'connecting' ? 'var(--signal-uncertain)' : 'var(--signal-agent)',
                boxShadow: isLive ? '0 0 8px var(--signal-human)' : 'none',
                animation: isLive ? 'pulse-dot 2s ease-in-out infinite' : 'none',
              }} />
              <span style={{ fontSize: 'var(--text-xs)', color: isLive ? 'var(--signal-human-text)' : 'var(--signal-uncertain-text)', fontFamily: 'var(--font-mono)', letterSpacing: '1px', fontWeight: 600 }}>
                {isLive ? 'LIVE' : connectionStatus.toUpperCase()}
              </span>
            </div>

            <div style={{ height: 24, width: 1, background: 'var(--border-subtle)' }} />

            {[
              { label: 'Scored', value: oracleStats?.total_scored_wallets?.toLocaleString() ?? '\u2014' },
              { label: 'Fresh Proofs', value: totalFreshProofs.toLocaleString() },
              { label: 'Model', value: modelVersion ? `v${modelVersion}` : '\u2014' },
            ].map(({ label, value }) => (
              <div key={label} style={{ textAlign: 'center' }}>
                <div style={{ fontSize: 'var(--text-lg)', fontWeight: 700, fontFamily: 'var(--font-mono)', color: 'var(--text-primary)', lineHeight: 1 }}>
                  {value}
                </div>
                <div style={{ fontSize: 'var(--text-2xs)', color: 'var(--text-muted)', letterSpacing: '1px', textTransform: 'uppercase', marginTop: 3 }}>
                  {label}
                </div>
              </div>
            ))}
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
            <a
              href={`${import.meta.env.VITE_EXPLORER_URL || 'https://explorer.testnet.mantle.xyz'}/address/${import.meta.env.VITE_ORACLE_ADDRESS || ''}`}
              target="_blank"
              rel="noopener noreferrer"
              className="header-link"
              style={{
                display: 'flex', alignItems: 'center', gap: 6,
                fontSize: 'var(--text-xs)', color: 'var(--text-secondary)',
                textDecoration: 'none', padding: '8px 12px',
                borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-default)',
                background: 'var(--surface-01)',
                transition: 'all var(--duration-fast) ease',
              }}
            >
              <ExternalLink size={12} />
              Explorer
            </a>
            <a
              href="https://github.com"
              target="_blank"
              rel="noopener noreferrer"
              className="header-link"
              style={{
                display: 'flex', alignItems: 'center', gap: 6,
                fontSize: 'var(--text-xs)', color: 'var(--text-secondary)',
                textDecoration: 'none', padding: '8px 12px',
                borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-default)',
                background: 'var(--surface-01)',
                transition: 'all var(--duration-fast) ease',
              }}
            >
              <Github size={12} />
              GitHub
            </a>
          </div>
        </header>

        <main style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(12, 1fr)',
          gap: 'var(--space-4)',
          alignItems: 'stretch',
        }}>
          <div style={{ gridColumn: 'span 3', minHeight: 560, display: 'flex' }}>
            <GhostPanel
              ghostAddress={GHOST_ADDRESS}
              currentHPS={ghostScore}
              ghostStatus={ghostStatus}
            />
          </div>

          <div style={{ gridColumn: 'span 3', minHeight: 560, display: 'flex' }}>
            <InterrogatorPanel
              ghostScore={ghostScore}
              previousScore={previousScore}
              scoreHistory={combinedHistory}
              featureContributions={featureContributions}
              lastUpdateTime={lastUpdateTime}
              modelVersion={modelVersion}
              connectionStatus={connectionStatus}
            />
          </div>

          <div style={{ gridColumn: 'span 3', minHeight: 560, display: 'flex' }}>
            <RealclawTrustPanel
              ghostAddress={GHOST_ADDRESS}
              trust={trust}
            />
          </div>

          <div style={{ gridColumn: 'span 3', minHeight: 560, display: 'flex' }}>
            <ProofLeaderboard
              proofs={recentProofs}
              totalFreshProofs={totalFreshProofs}
              totalMinted={totalMinted}
            />
          </div>

          <div style={{ gridColumn: 'span 6', display: 'flex' }}>
            <WalletChecker />
          </div>
          <div style={{ gridColumn: 'span 6', display: 'flex' }}>
            <EcosystemPanel />
          </div>

          <div style={{ gridColumn: 'span 12' }}>
            <SybilGraph clusters={sybilClusters} />
          </div>
        </main>

        {!hasValidAddress && (
          <div style={{
            position: 'fixed', bottom: 16, left: '50%', transform: 'translateX(-50%)',
            background: 'var(--signal-uncertain-glow)',
            border: '1px solid var(--signal-uncertain-border)',
            borderRadius: 'var(--radius-md)',
            padding: '10px 16px', fontSize: 'var(--text-sm)',
            color: 'var(--signal-uncertain-text)',
            backdropFilter: 'blur(12px)',
            fontFamily: 'var(--font-mono)', zIndex: 100,
          }}>
            {'\u26A0'} Set VITE_GHOST_ADDRESS in dashboard/.env to connect to live data
          </div>
        )}
      </div>
    </>
  );
}
