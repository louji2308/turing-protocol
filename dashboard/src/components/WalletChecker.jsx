import { useState } from 'react';
import { Search, Sparkles, Download, AlertTriangle, ShieldCheck } from 'lucide-react';
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
    } catch (e) {
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
    { label: 'Ghost agent', value: GHOST_ADDRESS },
    { label: 'Operator', value: '0x8Dca73df43Af5B7982B8bB86f61fC624ced74D89' },
  ];

  return (
    <div className="panel" role="form" aria-label="Wallet humanity checker">
      <div className="panel-header">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div className="panel-title">INSTANT TRUST CHECK</div>
          <span className="badge badge-purple"><Sparkles size={10} /> No gas · No wallet</span>
        </div>
        <div style={{ fontSize: 'var(--text-2xl)', fontWeight: 800, letterSpacing: '-0.8px', color: 'var(--text-primary)', marginTop: 6 }}>
          Is this wallet <span className="gradient-text">human</span>?
        </div>
        <div className="panel-subtitle" style={{ marginTop: 2 }}>
          Enter any Mantle wallet address or ENS name. Instant result, fully explained by the model.
        </div>
      </div>

      <div style={{ display: 'flex', gap: 'var(--space-2)' }} role="group" aria-label="Wallet address input">
        <div style={{ position: 'relative', flex: 1 }}>
          <Search size={15} color="var(--text-muted)" style={{ position: 'absolute', left: 14, top: '50%', transform: 'translateY(-50%)', pointerEvents: 'none' }} />
          <input
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
              width: '100%', padding: '12px 14px 12px 40px',
              background: 'var(--surface-01)', border: '1px solid var(--border-default)',
              borderRadius: 'var(--radius-md)', color: 'var(--text-primary)',
              fontFamily: 'var(--font-mono)', fontSize: 'var(--text-sm)', outline: 'none',
              transition: 'border-color var(--duration-fast) ease',
            }}
            onFocus={(e) => (e.target.style.borderColor = 'var(--accent-purple-border)')}
            onBlur={(e) => (e.target.style.borderColor = 'var(--border-default)')}
          />
        </div>
        <button
          onClick={() => checkWallet()}
          disabled={isLoading}
          aria-label={isLoading ? 'Scoring wallet' : 'Check wallet score'}
          style={{
            display: 'flex', alignItems: 'center', gap: 7,
            padding: '0 20px', borderRadius: 'var(--radius-md)',
            border: '1px solid var(--accent-purple-border)',
            background: 'linear-gradient(135deg, var(--accent-purple-dim), var(--accent-purple))',
            color: '#fff', fontSize: 'var(--text-sm)', fontWeight: 700,
            cursor: isLoading ? 'wait' : 'pointer', opacity: isLoading ? 0.6 : 1,
            fontFamily: 'var(--font-sans)', whiteSpace: 'nowrap',
            boxShadow: '0 0 20px rgba(139,124,255,0.3)',
            transition: 'all var(--duration-fast) ease',
          }}
        >
          {isLoading ? 'Scoring…' : <>Score <span style={{ fontFamily: 'var(--font-mono)' }}>→</span></>}
        </button>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
        <span style={{ fontSize: 'var(--text-2xs)', color: 'var(--text-muted)', letterSpacing: '1px', textTransform: 'uppercase' }}>Try</span>
        {samples.map((s) => (
          <button
            key={s.value}
            onClick={() => checkWallet(s.value)}
            disabled={isLoading}
            title={s.value}
            style={{
              padding: '3px 10px', borderRadius: 20,
              border: '1px solid var(--border-subtle)', background: 'var(--surface-01)',
              color: 'var(--text-tertiary)', fontSize: 'var(--text-2xs)',
              fontFamily: 'var(--font-mono)', cursor: isLoading ? 'wait' : 'pointer',
              opacity: isLoading ? 0.5 : 1,
              transition: 'all var(--duration-fast) ease',
            }}
          >
            {s.label}
          </button>
        ))}
      </div>

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

      {!result && !error && (
        <div style={{
          flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center',
          justifyContent: 'center', gap: 10, padding: 'var(--space-6)',
          color: 'var(--text-muted)', textAlign: 'center',
          border: '1px dashed var(--border-subtle)', borderRadius: 'var(--radius-lg)',
        }}>
          <ShieldCheck size={28} color="var(--text-disabled)" />
          <div style={{ fontSize: 'var(--text-sm)', color: 'var(--text-tertiary)' }}>
            Behavioral analysis appears here
          </div>
          <div style={{ fontSize: 'var(--text-2xs)', maxWidth: 320, lineHeight: 1.6 }}>
            We compute a Human Probability Score (0–10000) from on-chain behavior and surface the exact signals that drove the decision.
          </div>
        </div>
      )}

      {result && (
        <div id="wallet-result-card" style={{
          flex: 1, padding: 'var(--space-4)', borderRadius: 'var(--radius-lg)',
          background: 'var(--surface-01)', border: '1px solid var(--border-subtle)',
          display: 'flex', flexDirection: 'column', gap: 'var(--space-4)',
          animation: 'fade-in-up 300ms var(--ease-out) both',
        }}>
          <div style={{ display: 'flex', justifyContent: 'center' }}>
            <ScoreGauge score={result.hps} previousScore={result.hps} size={180} strokeWidth={12} />
          </div>
          {result.explanation && result.explanation.length > 0 && (
            <FeatureWaterfall contributions={result.explanation} maxFeatures={8} />
          )}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderTop: '1px solid var(--border-subtle)', paddingTop: 'var(--space-3)' }}>
            {result.confidence ? (
              <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>
                Confidence:{' '}
                <span style={{ color: result.confidence === 'high' ? 'var(--signal-human-text)' : result.confidence === 'medium' ? 'var(--signal-uncertain-text)' : 'var(--signal-agent-text)', fontWeight: 600 }}>
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
              }}
            >
              <Download size={12} /> Share score
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
