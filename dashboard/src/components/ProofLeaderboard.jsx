import { useState } from 'react';
import { Shield, ShieldOff, ExternalLink, Check } from 'lucide-react';

export default function ProofLeaderboard({
  proofs = [],
  totalFreshProofs = 0,
  totalMinted = 0,
}) {
  const [filterFresh, setFilterFresh] = useState(false);

  const displayProofs = filterFresh ? proofs.filter(p => p.is_fresh) : proofs;
  const staleCount = totalMinted - totalFreshProofs;

  const getScoreColor = (score) => {
    if (score >= 8000) return 'var(--signal-human-text)';
    if (score >= 7000) return 'var(--text-secondary)';
    return 'var(--signal-uncertain-text)';
  };

  return (
    <div className="panel" style={{ animation: 'fade-in-up 400ms 200ms var(--ease-out) both' }}>
      <div className="panel-header">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div className="panel-title">PROOF OF BEHAVIOR</div>
          <span className="badge badge-purple">ERC-8004</span>
        </div>
        <div className="panel-subtitle">
          Soulbound behavioral proofs &middot; Mantle mainnet
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 'var(--space-2)' }}>
        <div className="stat-card">
          <div className="stat-label">Total Minted</div>
          <div className="stat-value" style={{ fontSize: 'var(--text-xl)' }}>
            {totalMinted.toLocaleString()}
          </div>
        </div>
        <div className="stat-card" style={{ borderColor: 'var(--signal-human-border)', boxShadow: 'var(--shadow-green)' }}>
          <div className="stat-label">Fresh</div>
          <div className="stat-value" style={{ fontSize: 'var(--text-xl)', color: 'var(--signal-human-text)' }}>
            {totalFreshProofs.toLocaleString()}
          </div>
        </div>
        <div className="stat-card" style={{ borderColor: staleCount > 0 ? 'var(--signal-agent-border)' : 'var(--border-subtle)' }}>
          <div className="stat-label">Stale</div>
          <div className="stat-value" style={{
            fontSize: 'var(--text-xl)',
            color: staleCount > 0 ? 'var(--signal-agent-text)' : 'var(--text-muted)',
          }}>
            {staleCount.toLocaleString()}
          </div>
        </div>
      </div>

      {proofs.length === 0 && (
        <div style={{
          background: 'var(--surface-01)',
          border: '1px solid var(--border-subtle)',
          borderRadius: 'var(--radius-md)',
          padding: 'var(--space-5)',
          display: 'flex', flexDirection: 'column', gap: 12,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <svg width="40" height="40" viewBox="0 0 40 40" fill="none">
              <path d="M20 4 L24 16 L36 16 L26 24 L30 36 L20 28 L10 36 L14 24 L4 16 L16 16 Z" fill="url(#shield-grad)" stroke="rgba(139,124,255,0.4)" strokeWidth="1" />
              <defs>
                <linearGradient id="shield-grad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="rgba(167,139,250,0.4)" />
                  <stop offset="100%" stopColor="rgba(79,70,229,0.1)" />
                </linearGradient>
              </defs>
            </svg>
            <div>
              <div style={{ fontSize: 'var(--text-xs)', lineHeight: 1.5 }}>
                <span style={{ color: 'var(--text-secondary)', fontWeight: 700 }}>How </span>
                <span className="gradient-text" style={{ fontWeight: 800 }}>Proof</span>
                <span style={{ color: 'var(--text-secondary)', fontWeight: 700 }}> of Behavior Works</span>
              </div>
            </div>
          </div>
          <div style={{ fontSize: 'var(--text-2xs)', color: 'var(--text-tertiary)', lineHeight: 1.7 }}>
            Any wallet on Mantle that maintains a Human Probability Score &ge; 7000 for 72+ consecutive hours,
            with a transaction history of at least 50 interactions, qualifies for a soulbound Proof of Behavior NFT.
            The NFT is non-transferable and encodes the wallet&apos;s behavioral fingerprint.
          </div>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 12, padding: 'var(--space-2) 0' }}>
            {['72h Monitoring', 'HPS \u2265 7000', 'Proof Minted'].map((step, i) => (
              <div key={step} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <div style={{
                  width: 20, height: 20, borderRadius: '50%',
                  background: 'var(--accent-purple-glow)',
                  border: '1px solid var(--accent-purple-border)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: '9px', color: 'var(--accent-purple-bright)',
                  fontWeight: 700,
                }}>
                  {i + 1}
                </div>
                <span style={{ fontSize: 'var(--text-2xs)', color: 'var(--text-tertiary)', fontFamily: 'var(--font-mono)' }}>
                  {step}
                </span>
                {i < 2 && <div style={{ width: 16, height: 1, background: 'var(--border-subtle)' }} />}
              </div>
            ))}
          </div>
        </div>
      )}

      {proofs.length > 0 && (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div className="label-caps">
            {displayProofs.length} {filterFresh ? 'fresh' : 'total'} proof{displayProofs.length !== 1 ? 's' : ''}
          </div>
          <button
            onClick={() => setFilterFresh(f => !f)}
            style={{
              display: 'flex', alignItems: 'center', gap: 6,
              padding: '4px 12px',
              border: `1px solid ${filterFresh ? 'var(--signal-human-border)' : 'var(--border-subtle)'}`,
              background: filterFresh ? 'var(--signal-human-glow)' : 'transparent',
              borderRadius: 'var(--radius-sm)',
              color: filterFresh ? 'var(--signal-human-text)' : 'var(--text-muted)',
              fontSize: 'var(--text-xs)', cursor: 'pointer',
              fontFamily: 'var(--font-sans)', fontWeight: filterFresh ? 700 : 400,
              transition: 'all var(--duration-fast) ease',
            }}
          >
            {filterFresh && <Check size={10} />}
            <Shield size={10} />
            Fresh only
          </button>
        </div>
      )}

      <div className="scroll-area" style={{ flex: 1 }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
          {displayProofs.map((proof, idx) => {
            const isNew = proof.isNew;
            const score = proof.current_score ?? proof.score_at_mint ?? 0;

            return (
              <div
                key={proof.token_id || idx}
                style={{
                  padding: 'var(--space-3)',
                  borderRadius: 'var(--radius-md)',
                  border: `1px solid ${
                    isNew ? 'var(--accent-purple-border)' : proof.is_fresh ? 'var(--signal-human-border)' : 'var(--border-subtle)'
                  }`,
                  background: isNew ? 'var(--accent-purple-glow)' : proof.is_fresh ? 'rgba(0,255,163,0.03)' : 'var(--surface-01)',
                  transition: 'all var(--duration-normal) ease',
                  animation: isNew ? 'slide-in-right 400ms var(--ease-out) both' : undefined,
                  position: 'relative',
                  overflow: 'hidden',
                }}
                onMouseEnter={(e) => {
                  const link = e.currentTarget.querySelector('.explorer-link');
                  if (link) link.style.opacity = '1';
                }}
                onMouseLeave={(e) => {
                  const link = e.currentTarget.querySelector('.explorer-link');
                  if (link) link.style.opacity = '0';
                }}
              >
                {isNew && (
                  <div style={{
                    position: 'absolute', inset: 0,
                    border: '2px solid rgba(167,139,250,0.3)',
                    borderRadius: 'var(--radius-md)',
                    animation: 'border-glow-pulse 1s ease-in-out 3',
                    pointerEvents: 'none',
                  }} />
                )}
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{ fontSize: 'var(--text-2xs)', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', width: 28 }}>
                      #{proof.token_id || idx + 1}
                    </span>
                    <span style={{ fontSize: 'var(--text-xs)', fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)' }}>
                      {proof.wallet_short || (proof.wallet ? `${proof.wallet.slice(0, 6)}...${proof.wallet.slice(-4)}` : '0x???')}
                    </span>
                    {isNew && (
                      <span className="badge badge-purple" style={{ fontSize: '8px', padding: '1px 6px' }}>
                        NEW
                      </span>
                    )}
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    {proof.is_fresh ? (
                      <Shield size={12} color="var(--signal-human)" />
                    ) : (
                      <ShieldOff size={12} color="var(--signal-agent)" />
                    )}
                    {proof.wallet && (
                      <a
                        className="explorer-link"
                        href={`${import.meta.env.VITE_EXPLORER_URL || 'https://explorer.testnet.mantle.xyz'}/address/${proof.wallet}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        style={{
                          color: 'var(--accent-purple)',
                          display: 'flex',
                          opacity: 0,
                          transition: 'opacity var(--duration-fast) ease',
                          textDecoration: 'none',
                          fontSize: 'var(--text-2xs)',
                          gap: 3,
                          alignItems: 'center',
                        }}
                      >
                        View <ExternalLink size={9} />
                      </a>
                    )}
                  </div>
                </div>

                {/* Segmented score bar */}
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span style={{
                    fontSize: 'var(--text-xs)', fontFamily: 'var(--font-mono)',
                    color: getScoreColor(score),
                    fontWeight: 700,
                    width: 48, flexShrink: 0,
                  }}>
                    {score.toLocaleString()}
                  </span>
                  <div style={{ flex: 1, display: 'flex', gap: 2, height: 6 }}>
                    {Array.from({ length: 10 }, (_, i) => (
                      <div
                        key={i}
                        style={{
                          flex: 1,
                          borderRadius: 1,
                          background: i < Math.round((score / 10000) * 10)
                            ? getScoreColor(score)
                            : 'var(--bg-elevated)',
                          transition: 'background 300ms ease',
                          boxShadow: i < Math.round((score / 10000) * 10)
                            ? `0 0 4px ${getScoreColor(score)}`
                            : 'none',
                        }}
                      />
                    ))}
                  </div>
                  {proof.score_at_mint && proof.score_at_mint !== score && (
                    <span style={{ fontSize: 'var(--text-2xs)', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', width: 40, textAlign: 'right', flexShrink: 0 }}>
                      @{proof.score_at_mint}
                    </span>
                  )}
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 6 }}>
                  <span style={{ fontSize: 'var(--text-2xs)', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                    {proof.mint_timestamp
                      ? new Date(proof.mint_timestamp * 1000).toLocaleDateString('en-US', {
                          month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
                        })
                      : '\u2014'}
                  </span>
                  <span style={{
                    fontSize: 'var(--text-2xs)',
                    color: proof.is_fresh ? 'var(--signal-human-text)' : 'var(--text-muted)',
                    fontWeight: 600,
                  }}>
                    {proof.is_fresh ? '\u25CF Fresh' : '\u25CB Stale'}
                  </span>
                </div>
              </div>
            );
          })}

          {displayProofs.length === 0 && proofs.length > 0 && (
            <div style={{ textAlign: 'center', padding: 'var(--space-8)', color: 'var(--text-muted)', fontSize: 'var(--text-sm)' }}>
              No fresh proofs at this time.
            </div>
          )}
        </div>
      </div>

      <div style={{ borderTop: '1px solid var(--border-subtle)', paddingTop: 'var(--space-3)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ fontSize: 'var(--text-2xs)', color: 'var(--text-muted)', letterSpacing: '1.5px', fontWeight: 700 }}>
          SOULBOUND &middot; NON-TRANSFERABLE
        </span>
        <a
          href={`${import.meta.env.VITE_EXPLORER_URL || 'https://explorer.testnet.mantle.xyz'}/address/${import.meta.env.VITE_POB_ADDRESS || ''}`}
          target="_blank"
          rel="noopener noreferrer"
          style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 'var(--text-xs)', color: 'var(--accent-purple)', textDecoration: 'none' }}
        >
          Contract
          <ExternalLink size={10} />
        </a>
      </div>
    </div>
  );
}
