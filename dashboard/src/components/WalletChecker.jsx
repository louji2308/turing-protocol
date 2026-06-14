import { useState, useRef } from 'react';
import { Search, Sparkles, Download, AlertTriangle, ShieldCheck, ArrowRight, Loader } from 'lucide-react';
import ScoreGauge from './ScoreGauge';
import FeatureWaterfall from './FeatureWaterfall';
import { ORACLE_API as ORACLE_URL, GHOST_ADDRESS } from '../config';

const ADDRESS_RE = /^0x[a-fA-F0-9]{40}$|^[a-zA-Z0-9-]+\.eth$/;

function humanizeError(code) {
  const messages = {
    insufficient_data: "This wallet doesn't have enough transaction history to score yet (minimum 5 transactions).",
    rate_limited: 'Too many requests right now — please wait a moment and try again.',
    invalid_address: 'That address format is not recognized. Use a 0x... address or .eth name.',
  };
  return messages[code] || `Could not score this wallet (${code}).`;
}

export function WalletChecker({ loading: externalLoading = false }) {
  const [address, setAddress] = useState('');
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const inputRef = useRef(null);

  const checkWallet = async (addr) => {
    const target = (addr ?? address).trim();
    if (!ADDRESS_RE.test(target)) {
      setError('Enter a valid 0x... address or .eth name');
      return;
    }
    setAddress(target);
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await fetch(
        `${ORACLE_URL}/score/${encodeURIComponent(target)}?include_explanation=true`,
      );
      const data = await res.json();
      if (data.error) setError(humanizeError(data.error));
      else if (data.detail) setError(humanizeError(data.detail));
      else setResult(data);
    } catch {
      setError('Could not reach the oracle. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const shareImage = async () => {
    const node = document.getElementById('wallet-result-card');
    if (!node) return;
    const html2canvas = (await import('html2canvas')).default;
    const canvas = await html2canvas(node, { backgroundColor: '#0e1019' });
    const link = document.createElement('a');
    link.download = `turing-hps-${address.slice(0, 8)}.png`;
    link.href = canvas.toDataURL('image/png');
    link.click();
  };

  const isLoading = loading || externalLoading;
  const samples = [
    { label: 'Ghost agent', value: GHOST_ADDRESS, color: 'var(--signal-uncertain)' },
    { label: 'Operator', value: '0x8Dca73df43Af5B7982B8bB86f61fC624ced74D89', color: 'var(--accent-purple)' },
  ];

  const hps = result?.hps ?? 0;
  const verdict = hps >= 7000 ? 'LIKELY HUMAN' : hps >= 5000 ? 'UNCERTAIN' : 'LIKELY AGENT';
  const verdictColor = hps >= 7000 ? 'var(--signal-human)' : hps >= 5000 ? 'var(--signal-uncertain)' : 'var(--signal-agent)';

  return (
    <div className="panel" role="form" aria-label="Wallet humanity checker">
      <div className="panel-header">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div className="panel-title">INSTANT TRUST CHECK</div>
          <span className="badge badge-purple"><Sparkles size={10} /> No gas &middot; No wallet</span>
        </div>
        <div style={{ fontSize: 'var(--text-2xl)', fontWeight: 800, letterSpacing: '-0.8px', color: 'var(--text-primary)', marginTop: 8 }}>
          Is this wallet{' '}
          <span className="gradient-text">human</span>?
        </div>
        <div className="panel-subtitle" style={{ marginTop: 4 }}>
          Enter any Mantle wallet address or ENS name. Instant result, fully explained by the model.
        </div>
      </div>

      {/* Input + Button - 52px height matched */}
      <div style={{ display: 'flex', gap: 'var(--space-2)' }} role="group" aria-label="Wallet address input">
        <div style={{ position: 'relative', flex: 1 }}>
          <Search size={16} color="var(--text-muted)" style={{
            position: 'absolute', left: 16, top: '50%', transform: 'translateY(-50%)',
            pointerEvents: 'none',
            transition: 'transform var(--duration-fast) ease',
            ...(isLoading ? { transform: 'translateY(-50%) rotate(15deg)' } : {}),
          }} />
          <input
            ref={inputRef}
            value={address}
            onChange={(e) => {
              setAddress(e.target.value);
              if (result) setResult(null);
              if (error) setError(null);
            }}
            onKeyDown={(e) => e.key === 'Enter' && !isLoading && checkWallet()}
            placeholder="0x... or name.eth"
            aria-label="Wallet address or ENS name"
            autoComplete="off"
            style={{
              width: '100%', height: 52, padding: '0 16px 0 44px',
              background: 'var(--surface-01)', border: '1px solid var(--border-default)',
              borderRadius: 'var(--radius-md)', color: 'var(--text-primary)',
              fontFamily: 'var(--font-mono)', fontSize: 'var(--text-sm)', outline: 'none',
              transition: 'border-color var(--duration-fast) ease, box-shadow var(--duration-fast) ease, background var(--duration-fast) ease',
              boxShadow: 'none',
            }}
            onFocus={(e) => {
              e.target.style.borderColor = 'var(--accent-purple-border)';
              e.target.style.boxShadow = '0 0 0 3px rgba(139,124,255,0.12)';
              e.target.style.background = 'rgba(139,124,255,0.04)';
            }}
            onBlur={(e) => {
              e.target.style.borderColor = 'var(--border-default)';
              e.target.style.boxShadow = 'none';
              e.target.style.background = 'var(--surface-01)';
            }}
          />
        </div>
        <button
          onClick={() => checkWallet()}
          disabled={isLoading}
          aria-label={isLoading ? 'Scoring wallet' : 'Check wallet score'}
          style={{
            display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
            height: 52, padding: '0 28px', borderRadius: 'var(--radius-md)',
            border: 'none',
            background: 'linear-gradient(135deg, var(--accent-purple-dim), var(--accent-purple))',
            color: '#fff', fontSize: 'var(--text-sm)', fontWeight: 700,
            cursor: isLoading ? 'wait' : 'pointer', opacity: isLoading ? 0.7 : 1,
            fontFamily: 'var(--font-sans)', whiteSpace: 'nowrap',
            boxShadow: '0 0 24px rgba(139,124,255,0.3)',
            transition: 'all var(--duration-fast) ease',
            position: 'relative', overflow: 'hidden',
          }}
          className="btn-magnetic"
        >
          {isLoading ? (
            <Loader size={16} style={{ animation: 'spin 800ms linear infinite' }} />
          ) : (
            <>Score <ArrowRight size={16} /></>
          )}
        </button>
      </div>

      {/* Sample Buttons */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
        <span style={{ fontSize: 'var(--text-2xs)', color: 'var(--text-muted)', letterSpacing: '1.5px', textTransform: 'uppercase', fontWeight: 700 }}>Try</span>
        {samples.map((s) => (
          <button
            key={s.value}
            onClick={() => checkWallet(s.value)}
            disabled={isLoading}
            title={s.value}
            style={{
              padding: '4px 12px', borderRadius: 20,
              border: `1px solid ${s.color}44`,
              background: `${s.color}12`,
              color: s.color, fontSize: 'var(--text-2xs)',
              fontFamily: 'var(--font-mono)', cursor: isLoading ? 'wait' : 'pointer',
              fontWeight: 600,
              opacity: isLoading ? 0.5 : 1,
              transition: 'all var(--duration-fast) ease',
            }}
          >
            {s.label}
          </button>
        ))}
      </div>

      {/* Error */}
      {error && (
        <div role="alert" style={{
          display: 'flex', alignItems: 'center', gap: 8,
          padding: 'var(--space-3) var(--space-4)', borderRadius: 'var(--radius-md)',
          border: '1px solid var(--signal-agent-border)', background: 'var(--signal-agent-glow)',
          color: 'var(--signal-agent-text)', fontSize: 'var(--text-sm)',
        }}>
          <AlertTriangle size={15} style={{ flexShrink: 0 }} /> {error}
        </div>
      )}

      {/* Empty State */}
      {!result && !error && (
        <div style={{
          flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center',
          justifyContent: 'center', gap: 10, padding: 'var(--space-8)',
          color: 'var(--text-muted)', textAlign: 'center',
          border: '1px dashed var(--border-subtle)', borderRadius: 'var(--radius-lg)',
        }}>
          <ShieldCheck size={32} color="var(--text-disabled)" />
          <div style={{ fontSize: 'var(--text-sm)', color: 'var(--text-tertiary)' }}>
            Behavioral analysis appears here
          </div>
          <div style={{ fontSize: 'var(--text-2xs)', maxWidth: 320, lineHeight: 1.6, color: 'var(--text-muted)' }}>
            We compute a Human Probability Score (0–10000) from on-chain behavior and surface the exact signals that drove the decision.
          </div>
        </div>
      )}

      {/* Result Card */}
      {result && (
        <div id="wallet-result-card" style={{
          flex: 1, padding: 'var(--space-5)', borderRadius: 'var(--radius-lg)',
          background: 'var(--surface-01)', border: '1px solid var(--border-subtle)',
          display: 'flex', flexDirection: 'column', gap: 'var(--space-4)',
          animation: 'fade-in-scale 300ms var(--ease-out) both',
          position: 'relative',
          overflow: 'hidden',
        }}>
          <div style={{
            position: 'absolute', top: 0, left: 0, right: 0, height: 1,
            background: `linear-gradient(90deg, transparent, ${verdictColor}, transparent)`,
          }} />
          <div style={{ display: 'flex', justifyContent: 'center' }}>
            <ScoreGauge score={result.hps} previousScore={result.hps} size={180} strokeWidth={12} />
          </div>

          {/* Verdict */}
          <div style={{
            textAlign: 'center',
            fontSize: '22px',
            fontWeight: '800',
            fontFamily: 'var(--font-mono)',
            color: verdictColor,
            letterSpacing: '2px',
            textShadow: `0 0 20px ${verdictColor}44`,
            textTransform: 'uppercase',
          }}>
            {verdict}
          </div>

          {result.explanation && result.explanation.length > 0 && (
            <FeatureWaterfall contributions={result.explanation} maxFeatures={8} />
          )}

          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderTop: '1px solid var(--border-subtle)', paddingTop: 'var(--space-3)' }}>
            {result.confidence ? (
              <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>
                Confidence:{' '}
                <span style={{
                  color: result.confidence === 'high' ? 'var(--signal-human-text)' : result.confidence === 'medium' ? 'var(--signal-uncertain-text)' : 'var(--signal-agent-text)',
                  fontWeight: 600,
                }}>
                  {result.confidence}
                </span>
                {result.investable === false && (
                  <span style={{ color: 'var(--signal-agent-text)', marginLeft: 8 }}>⚠ low confidence</span>
                )}
              </div>
            ) : <span />}
            <button
              onClick={shareImage}
              style={{
                display: 'flex', alignItems: 'center', gap: 6,
                fontSize: 'var(--text-xs)', color: 'var(--accent-purple-bright)',
                background: 'transparent', border: 'none', cursor: 'pointer', fontWeight: 600,
                padding: '4px 10px', borderRadius: 20,
                border: '1px solid var(--accent-purple-border)',
                transition: 'all var(--duration-fast) ease',
              }}
            >
              <Download size={12} /> Share
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
