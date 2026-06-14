import { useState, useEffect, useRef } from 'react';
import GhostPanel from './components/GhostPanel';
import InterrogatorPanel from './components/InterrogatorPanel';
import ProofLeaderboard from './components/ProofLeaderboard';
import RealclawTrustPanel from './components/RealclawTrustPanel';
import { WalletChecker } from './components/WalletChecker';
import { EcosystemPanel } from './components/EcosystemPanel';
import { SybilGraph } from './components/SybilGraph';
import ParticleField from './components/ParticleField';
import { useOracleEvents } from './hooks/useOracleEvents';
import { useGhostTelemetry } from './hooks/useGhostTelemetry';
import { useScoreHistory } from './hooks/useScoreHistory';
import { useRealclawTrust } from './hooks/useRealclawTrust';
import { ExternalLink, Github, Zap } from 'lucide-react';
import { GHOST_ADDRESS, NETWORK_NAME, ORACLE_API, EXPLORER_URL, ORACLE_ADDRESS } from './config';

export default function App() {
  const [isLoaded, setIsLoaded] = useState(false);
  const [sybilClusters, setSybilClusters] = useState({});
  const [scrolled, setScrolled] = useState(false);
  const headerRef = useRef(null);

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
    const onScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  useEffect(() => {
    let cancelled = false;
    const loadClusters = async () => {
      try {
        const listResp = await fetch(`${ORACLE_API}/api/v1/intelligence/sybil-clusters`);
        if (!listResp.ok) return;
        const summaries = await listResp.json();
        const list = Array.isArray(summaries) ? summaries : (summaries?.clusters ? Object.values(summaries.clusters) : []);
        const details = await Promise.all(
          list.map(c =>
            fetch(`${ORACLE_API}/api/v1/intelligence/sybil-clusters/${c.cluster_id}`)
              .then(r => (r.ok ? r.json() : null))
              .catch(() => null)
          )
        );
        if (cancelled) return;
        const map = {};
        details.forEach(d => {
          if (d && d.cluster_id) {
            map[d.cluster_id] = {
              members: d.members || [],
              coordinator: d.coordinator,
              sybil_probability: d.sybil_probability,
              risk_level: d.risk_level,
              avg_hps: d.avg_hps,
              size: d.size,
            };
          }
        });
        setSybilClusters(map);
      } catch { /* API not available */ }
    };
    loadClusters();
    return () => { cancelled = true; };
  }, []);

  const hasValidAddress = GHOST_ADDRESS !== '0x0000000000000000000000000000000000000000';
  const isLive = connectionStatus === 'connected';

  return (
    <>
      <ParticleField />
      <div className="ambient-bg" aria-hidden="true">
        <div className="ambient-orb a" />
        <div className="ambient-orb b" />
        <div className="ambient-orb c" />
        <div className="ambient-orb d" />
      </div>

      <div style={{
        maxWidth: 1700,
        margin: '0 auto',
        padding: 'var(--space-5) var(--space-5) 80px',
        display: 'flex',
        flexDirection: 'column',
        gap: 'var(--space-4)',
        boxSizing: 'border-box',
        position: 'relative',
        zIndex: 1,
      }}>

        {/* ─── HEADER ─── */}
        <header
          ref={headerRef}
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            flexWrap: 'wrap',
            gap: 'var(--space-4)',
            padding: 'var(--space-4) var(--space-5)',
            background: scrolled
              ? 'linear-gradient(180deg, rgba(6,8,18,0.92), rgba(6,8,18,0.78))'
              : 'linear-gradient(180deg, rgba(255,255,255,0.046), rgba(255,255,255,0) 30%), var(--bg-panel)',
            borderRadius: 'var(--radius-xl)',
            border: '1px solid rgba(255,255,255,0.10)',
            boxShadow: scrolled
              ? 'var(--shadow-lg), inset 0 1px 0 rgba(255,255,255,0.07)'
              : 'var(--shadow-md), inset 0 1px 0 rgba(255,255,255,0.07)',
            backdropFilter: scrolled
              ? 'blur(32px) saturate(200%)'
              : 'blur(16px) saturate(160%)',
            WebkitBackdropFilter: scrolled
              ? 'blur(32px) saturate(200%)'
              : 'blur(16px) saturate(160%)',
            position: 'sticky',
            top: 'var(--space-3)',
            zIndex: 50,
            animation: 'card-enter 400ms var(--ease-out) both',
            transition: 'background var(--duration-normal) ease, backdrop-filter var(--duration-normal) ease, box-shadow var(--duration-normal) ease',
          }}>
          {/* Logo */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-4)' }}>
            <div style={{
              position: 'relative',
              width: 48, height: 48,
              borderRadius: 14,
              background: 'linear-gradient(135deg, rgba(124,58,237,0.85), rgba(79,70,229,0.95))',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              boxShadow: '0 0 32px rgba(124,58,237,0.55), 0 0 64px rgba(124,58,237,0.22), inset 0 1px 0 rgba(255,255,255,0.22)',
              animation: 'depth-pulse 4s ease-in-out infinite',
            }}>
              <Zap size={22} color="#fff" strokeWidth={2.5} />
            </div>
            <div>
              <div className="gradient-text" style={{ fontSize: 'var(--text-xl)', fontWeight: 800, letterSpacing: '-0.5px', lineHeight: 1 }}>
                TURING PROTOCOL
              </div>
              <div style={{ fontSize: 'var(--text-2xs)', color: 'var(--text-tertiary)', letterSpacing: '2px', textTransform: 'uppercase', marginTop: 4 }}>
                Behavioral Proof of Humanity · {NETWORK_NAME}
              </div>
            </div>
          </div>

          {/* Stats */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-5)', flexWrap: 'wrap' }}>
            {/* LIVE badge */}
            <div style={{
              position: 'relative',
              display: 'flex', alignItems: 'center', gap: 8,
              padding: '6px 14px', borderRadius: 20,
              border: `1px solid ${isLive ? 'var(--signal-human-border)' : 'var(--signal-uncertain-border)'}`,
              background: isLive ? 'var(--signal-human-glow)' : 'var(--signal-uncertain-glow)',
              animation: isLive ? 'border-glow-pulse 3s ease-in-out infinite' : 'none',
            }}>
              <div style={{ position: 'relative', width: 10, height: 10 }}>
                <div style={{
                  position: 'absolute', inset: 0, borderRadius: '50%',
                  background: isLive ? 'var(--signal-human)' : 'var(--signal-agent)',
                  boxShadow: isLive ? '0 0 8px var(--signal-human)' : 'none',
                  animation: isLive ? 'neon-flicker 6s ease-in-out infinite' : 'none',
                }} />
                {isLive && (
                  <div style={{
                    position: 'absolute', top: -2, left: -2, right: -2, bottom: -2,
                    borderRadius: '50%',
                    border: '2px solid var(--signal-human)',
                    opacity: 0.3,
                    animation: 'pulse-ring 2s ease-out infinite',
                  }} />
                )}
              </div>
              <span style={{
                fontSize: 'var(--text-xs)',
                color: isLive ? 'var(--signal-human-text)' : 'var(--signal-uncertain-text)',
                fontFamily: 'var(--font-mono)',
                letterSpacing: '1.5px',
                fontWeight: 700,
              }}>
                ● {isLive ? 'LIVE' : connectionStatus.toUpperCase()}
              </span>
            </div>

            <div style={{ height: 28, width: 1, background: 'linear-gradient(180deg, transparent, var(--border-subtle), transparent)' }} />

            {[
              { label: 'Scored',       value: oracleStats?.total_scored_wallets?.toLocaleString() ?? '—' },
              { label: 'Fresh Proofs', value: totalFreshProofs.toLocaleString() },
              { label: 'Model',        value: modelVersion ? `v${modelVersion}` : '—' },
            ].map(({ label, value }, i) => (
              <div key={label} style={{ textAlign: 'center', animation: `fade-in-up 300ms ${100 + i * 100}ms var(--ease-out) both` }}>
                <div style={{
                  fontSize: '22px', fontWeight: 800, fontFamily: 'var(--font-mono)',
                  color: 'var(--text-primary)', lineHeight: 1, letterSpacing: '-1px',
                }}>
                  {value}
                </div>
                <div style={{ fontSize: '9px', color: 'var(--text-muted)', letterSpacing: '2px', textTransform: 'uppercase', marginTop: 3, fontWeight: 700 }}>
                  {label}
                </div>
              </div>
            ))}
          </div>

          {/* Links */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
            <a
              href={`${EXPLORER_URL}/address/${ORACLE_ADDRESS}`}
              target="_blank" rel="noopener noreferrer"
              className="header-link"
              style={{
                display: 'flex', alignItems: 'center', gap: 6,
                fontSize: 'var(--text-xs)', color: 'var(--text-secondary)',
                textDecoration: 'none', padding: '8px 12px',
                borderRadius: 'var(--radius-sm)',
                border: '1px solid var(--border-default)',
                background: 'var(--surface-01)',
                transition: 'all var(--duration-fast) ease',
              }}
            >
              <ExternalLink size={12} /> Explorer
            </a>
            <a
              href="https://github.com"
              target="_blank" rel="noopener noreferrer"
              className="header-link"
              style={{
                display: 'flex', alignItems: 'center', gap: 6,
                fontSize: 'var(--text-xs)', color: 'var(--text-secondary)',
                textDecoration: 'none', padding: '8px 12px',
                borderRadius: 'var(--radius-sm)',
                border: '1px solid var(--border-default)',
                background: 'var(--surface-01)',
                transition: 'all var(--duration-fast) ease',
              }}
            >
              <Github size={12} /> GitHub
            </a>
          </div>
        </header>

        {/* ─── MAIN GRID ─── */}
        <main style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(12, 1fr)',
          gap: 'var(--space-4)',
          alignItems: 'stretch',
        }}>
          {/* Row 1: four panels */}
          <div style={{ gridColumn: 'span 3', display: 'flex' }}>
            <GhostPanel ghostAddress={GHOST_ADDRESS} currentHPS={ghostScore} ghostStatus={ghostStatus} />
          </div>
          <div style={{ gridColumn: 'span 3', display: 'flex' }}>
            <InterrogatorPanel
              ghostScore={ghostScore}
              previousScore={previousScore}
              scoreHistory={combinedHistory}
              featureContributions={featureContributions}
              lastUpdateTime={lastUpdateTime}
              modelVersion={modelVersion}
              connectionStatus={connectionStatus}
              apiAvailable={apiAvailable}
            />
          </div>
          <div style={{ gridColumn: 'span 3', display: 'flex' }}>
            <RealclawTrustPanel ghostAddress={GHOST_ADDRESS} trust={trust} />
          </div>
          <div style={{ gridColumn: 'span 3', display: 'flex' }}>
            <ProofLeaderboard
              proofs={recentProofs}
              totalFreshProofs={totalFreshProofs}
              totalMinted={totalMinted}
            />
          </div>

          {/* Row 2: Wallet Checker + Ecosystem */}
          <div style={{ gridColumn: 'span 6', display: 'flex' }}>
            <WalletChecker />
          </div>
          <div style={{ gridColumn: 'span 6', display: 'flex' }}>
            <EcosystemPanel />
          </div>

          {/* Row 3: Sybil Map full width */}
          <div style={{ gridColumn: 'span 12' }}>
            <SybilGraph clusters={sybilClusters} />
          </div>
        </main>

        {/* Dev warning */}
        {!hasValidAddress && (
          <div style={{
            position: 'fixed', bottom: 16, left: '50%', transform: 'translateX(-50%)',
            background: 'var(--signal-uncertain-glow)',
            border: '1px solid var(--signal-uncertain-border)',
            borderRadius: 'var(--radius-md)',
            padding: '10px 16px',
            fontSize: 'var(--text-sm)',
            color: 'var(--signal-uncertain-text)',
            backdropFilter: 'blur(16px)',
            fontFamily: 'var(--font-mono)',
            zIndex: 100,
            animation: 'card-enter 500ms var(--ease-out) both',
          }}>
            ⚠ Set VITE_GHOST_ADDRESS in dashboard/.env to connect to live data
          </div>
        )}
      </div>
    </>
  );
}
