import { useState, useEffect } from 'react';
import GhostPanel from './components/GhostPanel';
import InterrogatorPanel from './components/InterrogatorPanel';
import ProofLeaderboard from './components/ProofLeaderboard';
import RealclawTrustPanel from './components/RealclawTrustPanel';
import { useOracleEvents } from './hooks/useOracleEvents';
import { useGhostTelemetry } from './hooks/useGhostTelemetry';
import { useScoreHistory } from './hooks/useScoreHistory';
import { useRealclawTrust } from './hooks/useRealclawTrust';
import { ExternalLink, Github, Activity } from 'lucide-react';

const GHOST_ADDRESS = import.meta.env.VITE_GHOST_ADDRESS || '0x0000000000000000000000000000000000000000';
const NETWORK_NAME = import.meta.env.VITE_NETWORK_NAME || 'Mantle Sepolia';

export default function App() {
  const [isLoaded, setIsLoaded] = useState(false);

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

  const hasValidAddress = GHOST_ADDRESS !== '0x0000000000000000000000000000000000000000';

  return (
    <div style={{
      display: 'grid',
      gridTemplateRows: 'auto 1fr',
      height: '100vh',
      padding: 'var(--space-4)',
      gap: 'var(--space-4)',
      background: 'var(--bg-void)',
      boxSizing: 'border-box',
      opacity: 1,
    }}>
      <header style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: 'var(--space-3) var(--space-5)',
        background: 'var(--bg-panel)',
        borderRadius: 'var(--radius-xl)',
        border: '1px solid var(--border-default)',
        boxShadow: 'var(--shadow-md)',
        animation: 'fade-in-up 300ms var(--ease-out) both',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-4)' }}>
          <div style={{
            width: 32, height: 32, borderRadius: 8,
            background: 'var(--accent-purple-glow)',
            border: '1px solid var(--accent-purple-border)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>
            <Activity size={16} color="var(--accent-purple)" />
          </div>
          <div>
            <div style={{ fontSize: 'var(--text-lg)', fontWeight: 800, letterSpacing: '-0.5px', color: 'var(--text-primary)', lineHeight: 1 }}>
              TURING PROTOCOL
            </div>
            <div style={{ fontSize: 'var(--text-2xs)', color: 'var(--text-muted)', letterSpacing: '2px', textTransform: 'uppercase', marginTop: 2 }}>
              Behavioral Proof of Humanity \u00B7 {NETWORK_NAME}
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-5)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <div style={{
              width: 7, height: 7, borderRadius: '50%',
              background: connectionStatus === 'connected' ? 'var(--signal-human)' : connectionStatus === 'connecting' ? 'var(--signal-uncertain)' : 'var(--signal-agent)',
              boxShadow: connectionStatus === 'connected' ? '0 0 8px var(--signal-human)' : 'none',
              animation: connectionStatus === 'connected' ? 'pulse-dot 2s ease-in-out infinite' : 'none',
            }} />
            <span style={{ fontSize: 'var(--text-xs)', color: 'var(--text-tertiary)', fontFamily: 'var(--font-mono)', letterSpacing: '1px' }}>
              {connectionStatus === 'connected' ? 'LIVE' : connectionStatus.toUpperCase()}
            </span>
          </div>

          <div style={{ height: 20, width: 1, background: 'var(--border-subtle)' }} />

          {[
            { label: 'Scored', value: oracleStats?.total_scored_wallets?.toLocaleString() ?? '\u2014' },
            { label: 'Fresh Proofs', value: totalFreshProofs.toLocaleString() },
            { label: 'Model', value: modelVersion ? `v${modelVersion}` : '\u2014' },
          ].map(({ label, value }) => (
            <div key={label} style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 'var(--text-md)', fontWeight: 700, fontFamily: 'var(--font-mono)', color: 'var(--text-primary)', lineHeight: 1 }}>
                {value}
              </div>
              <div style={{ fontSize: 'var(--text-2xs)', color: 'var(--text-muted)', letterSpacing: '1px', textTransform: 'uppercase', marginTop: 2 }}>
                {label}
              </div>
            </div>
          ))}
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)' }}>
          <a
            href={`${import.meta.env.VITE_EXPLORER_URL || 'https://explorer.testnet.mantle.xyz'}/address/${import.meta.env.VITE_ORACLE_ADDRESS || ''}`}
            target="_blank"
            rel="noopener noreferrer"
            style={{
              display: 'flex', alignItems: 'center', gap: 5,
              fontSize: 'var(--text-xs)', color: 'var(--text-tertiary)',
              textDecoration: 'none', padding: '6px 10px',
              borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)',
              transition: 'all var(--duration-fast) ease',
            }}
          >
            <ExternalLink size={11} />
            Explorer
          </a>

          <a
            href="https://github.com"
            target="_blank"
            rel="noopener noreferrer"
            style={{
              display: 'flex', alignItems: 'center', gap: 5,
              fontSize: 'var(--text-xs)', color: 'var(--text-tertiary)',
              textDecoration: 'none', padding: '6px 10px',
              borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)',
              transition: 'all var(--duration-fast) ease',
            }}
          >
            <Github size={11} />
            GitHub
          </a>
        </div>
      </header>

      <main style={{
        display: 'grid',
        gridTemplateColumns: '1fr 1.2fr 0.9fr 0.9fr',
        gap: 'var(--space-4)',
        minHeight: 0,
        overflow: 'hidden',
      }}>
        <GhostPanel
          ghostAddress={GHOST_ADDRESS}
          currentHPS={ghostScore}
          ghostStatus={ghostStatus}
        />

        <InterrogatorPanel
          ghostScore={ghostScore}
          previousScore={previousScore}
          scoreHistory={combinedHistory}
          featureContributions={featureContributions}
          lastUpdateTime={lastUpdateTime}
          modelVersion={modelVersion}
          connectionStatus={connectionStatus}
        />

        <RealclawTrustPanel
          ghostAddress={GHOST_ADDRESS}
          trust={trust}
        />

        <ProofLeaderboard
          proofs={recentProofs}
          totalFreshProofs={totalFreshProofs}
          totalMinted={totalMinted}
        />
      </main>

      {!hasValidAddress && (
        <div style={{
          position: 'fixed', bottom: 16, left: '50%', transform: 'translateX(-50%)',
          background: 'var(--signal-uncertain-glow)',
          border: '1px solid var(--signal-uncertain-border)',
          borderRadius: 'var(--radius-md)',
          padding: '10px 16px', fontSize: 'var(--text-sm)',
          color: 'var(--signal-uncertain-text)',
          fontFamily: 'var(--font-mono)', zIndex: 100,
        }}>
          {'\u26A0'} Set VITE_GHOST_ADDRESS in dashboard/.env to connect to live data
        </div>
      )}
    </div>
  );
}
