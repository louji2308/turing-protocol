import { useState } from 'react';
import { Shield, ShieldOff, ExternalLink } from 'lucide-react';

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

  const getScoreBarWidth = (score) => `${Math.min(100, (score / 10000) * 100)}%`;

  return (
    <div className="panel" style={{ animation: 'fade-in-up 400ms 200ms var(--ease-out) both' }}>
      <div className="panel-header">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div className="panel-title">PROOF OF BEHAVIOR</div>
          <span className="badge badge-purple">ERC-8004</span>
        </div>
        <div className="panel-subtitle">
          Soulbound behavioral proofs \u00B7 Mantle mainnet
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 'var(--space-2)' }}>
        <div className="stat-card">
          <div className="stat-label">Total Minted</div>
          <div className="stat-value" style={{ fontSize: 'var(--text-xl)' }}>
            {totalMinted.toLocaleString()}
          </div>
        </div>
        <div className="stat-card" style={{ borderColor: 'var(--signal-human-border)' }}>
          <div className="stat-label">Fresh</div>
          <div className="stat-value" style={{ fontSize: 'var(--text-xl)', color: 'var(--signal-human-text)' }}>
            {totalFreshProofs.toLocaleString()}
          </div>
        </div>
        <div className="stat-card" style={{ borderColor: 'var(--signal-agent-border)' }}>
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
          padding: 'var(--space-4)',
        }}>
          <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-tertiary)', lineHeight: 1.7 }}>
            <p style={{ color: 'var(--text-secondary)', fontWeight: 600, marginBottom: 8 }}>
              How Proof of Behavior works
            </p>
            <p>
              Any wallet on Mantle that maintains a Human Probability Score \u2265 7000 for 72+ consecutive hours,
              with a transaction history of at least 50 interactions, qualifies for a soulbound Proof of Behavior NFT.
            </p>
            <p style={{ marginTop: 8 }}>
              The NFT is non-transferable. It encodes the wallet's behavioral fingerprint \u2014 a SHAP-derived hash of
              the top 10 behavioral signals at the time of certification.
            </p>
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
              padding: '4px 10px',
              border: `1px solid ${filterFresh ? 'var(--signal-human-border)' : 'var(--border-subtle)'}`,
              background: filterFresh ? 'var(--signal-human-glow)' : 'transparent',
              borderRadius: 'var(--radius-sm)',
              color: filterFresh ? 'var(--signal-human-text)' : 'var(--text-muted)',
              fontSize: 'var(--text-xs)', cursor: 'pointer',
              fontFamily: 'var(--font-sans)',
              transition: 'all var(--duration-fast) ease',
            }}
          >
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
                  padding: 'var(--space-3) var(--space-3)',
                  borderRadius: 'var(--radius-md)',
                  border: `1px solid ${
                    isNew ? 'var(--accent-purple-border)' : proof.is_fresh ? 'var(--signal-human-border)' : 'var(--border-subtle)'
                  }`,
                  background: isNew ? 'var(--accent-purple-glow)' : proof.is_fresh ? 'rgba(34, 197, 94, 0.04)' : 'var(--surface-01)',
                  transition: 'all var(--duration-normal) ease',
                  animation: isNew ? 'slide-in-right 400ms var(--ease-out) both' : undefined,
                }}
              >
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
                        href={`${import.meta.env.VITE_EXPLORER_URL || 'https://explorer.testnet.mantle.xyz'}/address/${proof.wallet}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        style={{ color: 'var(--text-muted)', display: 'flex' }}
                      >
                        <ExternalLink size={10} />
                      </a>
                    )}
                  </div>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span style={{ fontSize: 'var(--text-xs)', fontFamily: 'var(--font-mono)', color: getScoreColor(score), width: 40, flexShrink: 0 }}>
                    {score.toLocaleString()}
                  </span>
                  <div style={{ flex: 1, height: 4, background: 'var(--bg-elevated)', borderRadius: 2, overflow: 'hidden' }}>
                    <div style={{
                      height: '100%', width: getScoreBarWidth(score),
                      background: getScoreColor(score), borderRadius: 2,
                      transition: 'width 600ms var(--ease-out)',
                    }} />
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
                    letterSpacing: '0.5px',
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
        <span style={{ fontSize: 'var(--text-2xs)', color: 'var(--text-muted)', letterSpacing: '1px' }}>
          SOULBOUND \u00B7 NON-TRANSFERABLE
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
