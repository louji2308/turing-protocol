import { useState } from 'react';
import { ScoreGauge } from './ScoreGauge';
import { FeatureWaterfall } from './FeatureWaterfall';

const ORACLE_URL = import.meta.env.VITE_ORACLE_URL || 'http://localhost:8080';
const ADDRESS_RE = /^0x[a-fA-F0-9]{40}$|^[a-zA-Z0-9-]+\.eth$/;

function humanizeError(code) {
  const messages = {
    insufficient_data: "This wallet doesn't have enough transaction history to score yet (minimum 5 transactions).",
    rate_limited: 'Too many requests right now \u2014 please wait a moment and try again.',
    invalid_address: 'That address format is not recognized. Use a 0x... address or .eth name.',
  };
  return messages[code] || `Could not score this wallet (${code}).`;
}

export function WalletChecker() {
  const [address, setAddress] = useState('');
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const checkWallet = async () => {
    if (!ADDRESS_RE.test(address.trim())) {
      setError('Enter a valid 0x... address or .eth name');
      return;
    }
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await fetch(
        `${ORACLE_URL}/score/${encodeURIComponent(address.trim())}?include_explanation=true`,
      );
      const data = await res.json();
      if (data.error) {
        setError(humanizeError(data.error));
      } else if (data.detail) {
        setError(humanizeError(data.detail));
      } else {
        setResult(data);
      }
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
    const canvas = await html2canvas(node, { backgroundColor: '#0f172a' });
    const link = document.createElement('a');
    link.download = `turing-hps-${address.slice(0, 8)}.png`;
    link.href = canvas.toDataURL('image/png');
    link.click();
  };

  return (
    <div className="checker-hero bg-gradient-to-br from-slate-900 to-slate-800 p-8 rounded-xl">
      <h2 className="text-2xl font-bold text-white mb-2">Is this wallet human?</h2>
      <p className="text-slate-400 mb-6">
        Enter any Mantle wallet address or ENS name. No gas. No wallet connection.
        Instant result, fully explained.
      </p>
      <div className="flex gap-3">
        <input
          className="flex-1 bg-slate-700 text-white rounded-lg px-4 py-3 font-mono text-sm"
          placeholder="0x... or name.eth"
          value={address}
          onChange={(e) => setAddress(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && checkWallet()}
        />
        <button
          onClick={checkWallet}
          disabled={loading}
          className="bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white px-6 py-3 rounded-lg font-semibold"
        >
          {loading ? 'Scoring...' : 'Score \u2192'}
        </button>
      </div>
      {error && <p className="text-red-400 text-sm mt-3">{error}</p>}
      {result && (
        <div id="wallet-result-card" className="mt-6 bg-slate-900 rounded-lg p-6">
          <ScoreGauge hps={result.hps} />
          {result.explanation && <FeatureWaterfall explanation={result.explanation} />}
          {result.confidence && (
            <div className="mt-3 text-xs text-slate-400">
              Confidence: <span className={
                result.confidence === 'high' ? 'text-green-400' :
                result.confidence === 'medium' ? 'text-amber-400' : 'text-red-400'
              }>{result.confidence}</span>
              {result.investable === false && (
                <span className="text-red-400 ml-2">\u26A0 Not investable - low confidence</span>
              )}
            </div>
          )}
          <button
            onClick={shareImage}
            className="mt-4 text-sm text-blue-400 hover:text-blue-300 underline"
          >
            Share Your Score
          </button>
        </div>
      )}
    </div>
  );
}
