import { useState, useEffect, useRef, useMemo } from 'react';
import { Search, Shield, Shuffle, Users, ExternalLink, ChevronRight, AlertTriangle, CheckCircle, XCircle, Clock, Info } from 'lucide-react';

const FEATURE_LABELS = {
  'temp_4_cv': 'Timing variability (CV)',
  'temp_7_hour_gini': 'Hourly activity Gini',
  'gas_0_price_cv': 'Gas price variability',
  'consist_4_failure_rate': 'TX failure rate',
  'div_3_protocol_hhi': 'Protocol concentration',
  'temp_5_fast_reaction_ratio': 'Fast reaction rate',
  'port_0_size_cv': 'Trade size variability',
  'gas_1_round_fraction': 'Round gas prices',
  'gas_4_overpay_ratio': 'Gas overpayment rate',
  'event_0_burstiness': 'Activity burstiness',
  'net_1_top1_concentration': 'Top-1 concentration',
  'net_5_contract_ratio': 'Contract call ratio',
};

function MiniGauge({ score, size = 80 }) {
  const [displayScore, setDisplayScore] = useState(5000);
  const animRef = useRef(null);

  useEffect(() => {
    if (animRef.current) cancelAnimationFrame(animRef.current);
    const start = displayScore;
    const target = score || 0;
    const duration = 1000;
    const startTime = performance.now();

    const animate = (ts) => {
      const elapsed = ts - startTime;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setDisplayScore(Math.round(start + (target - start) * eased));
      if (progress < 1) animRef.current = requestAnimationFrame(animate);
    };
    animRef.current = requestAnimationFrame(animate);
    return () => { if (animRef.current) cancelAnimationFrame(animRef.current); };
  }, [score]);

  const center = size / 2;
  const radius = (size - 16) / 2;
  const circumference = 2 * Math.PI * radius;
  const fillRatio = Math.max(0, Math.min(1, (score || 0) / 10000));
  const fillLength = fillRatio * circumference * 0.75;

  const arcColor = score >= 7000 ? 'var(--signal-human)' : score >= 5000 ? 'var(--signal-uncertain)' : score >= 3000 ? 'var(--signal-agent-dim)' : 'var(--signal-agent)';

  const polarToCartesian = (cx, cy, r, angleDeg) => {
    const rad = ((angleDeg - 90) * Math.PI) / 180;
    return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) };
  };

  const startAngle = 135;
  const endAngle = 405;
  const start = polarToCartesian(center, center, radius, endAngle);
  const end = polarToCartesian(center, center, radius, startAngle);
  const arcPath = `M ${start.x} ${start.y} A ${radius} ${radius} 0 1 0 ${end.x} ${end.y}`;

  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} style={{ overflow: 'visible', flexShrink: 0 }}>
      <path d={arcPath} fill="none" stroke="var(--bg-elevated)" strokeWidth={6} strokeLinecap="round" />
      <path d={arcPath} fill="none" stroke={arcColor} strokeWidth={6} strokeLinecap="round"
        strokeDasharray={`${fillLength} ${circumference}`}
        style={{ transition: 'stroke-dasharray 800ms cubic-bezier(0.16, 1, 0.3, 1)', filter: `drop-shadow(0 0 4px ${arcColor})` }} />
      <text x={center} y={center + 4} textAnchor="middle" fill={arcColor} fontSize="18" fontFamily="var(--font-mono)" fontWeight="700">
        {displayScore.toLocaleString()}
      </text>
    </svg>
  );
}

function TrustResultCard({ result, onClose, onHandshake }) {
  if (!result || result.status === 'checking') {
    return (
      <div style={{ padding: 'var(--space-8)', textAlign: 'center', color: 'var(--text-muted)' }}>
        <div style={{ fontSize: 32, marginBottom: 8, animation: 'pulse-dot 1s ease-in-out infinite' }}>◉</div>
        <div style={{ fontSize: 'var(--text-sm)', fontFamily: 'var(--font-mono)' }}>Analyzing wallet behavior...</div>
      </div>
    );
  }

  if (result.status === 'error' || !result.hps && result.hps !== 0) {
    const errFriendly = result.error === 'insufficient transaction history'
      ? 'This wallet has no transaction history on this network. No score can be computed.'
      : result.error === 'fetch_failed'
      ? 'Could not reach the oracle service. Make sure it is running.'
      : result.error || 'Wallet may be unscored or RPC unreachable';
    return (
      <div style={{ padding: 'var(--space-4)', textAlign: 'center' }}>
        <AlertTriangle size={24} color="var(--signal-uncertain)" style={{ marginBottom: 8 }} />
        <div style={{ fontSize: 'var(--text-sm)', color: 'var(--text-secondary)' }}>Score unavailable</div>
        <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', marginTop: 4 }}>
          {errFriendly}
        </div>
      </div>
    );
  }

  const hps = result.hps;
  const isTrusted = result.trusted;
  const recColor = result.recommendation === 'proceed' ? 'var(--signal-human)' : result.recommendation === 'proceed_with_caution' ? 'var(--signal-uncertain)' : result.recommendation === 'reject' ? 'var(--signal-agent)' : 'var(--text-muted)';
  const recLabel = result.recommendation === 'proceed' ? 'PROCEED' : result.recommendation === 'proceed_with_caution' ? 'PROCEED WITH CAUTION' : result.recommendation === 'reject' ? 'REJECT' : 'INSUFFICIENT DATA';

  return (
    <div style={{ animation: 'fade-in-up 300ms var(--ease-out) both' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <MiniGauge score={hps} size={72} />
          <div>
            <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
              {result.address.slice(0, 8)}...{result.address.slice(-6)}
            </div>
            <div style={{ fontSize: 'var(--text-2xs)', color: 'var(--text-tertiary)', fontFamily: 'var(--font-mono)' }}>
              Tier: {result.tier} · Threshold: {result.threshold}
            </div>
          </div>
        </div>
        <a href={`${import.meta.env.VITE_EXPLORER_URL || 'https://explorer.testnet.mantle.xyz'}/address/${result.address}`} target="_blank" rel="noopener noreferrer" style={{ color: 'var(--text-muted)', display: 'flex' }}>
          <ExternalLink size={12} />
        </a>
      </div>

      <div style={{
        padding: 'var(--space-3) var(--space-4)',
        borderRadius: 'var(--radius-md)',
        border: `1px solid ${recColor}44`,
        background: `${recColor}08`,
        marginBottom: 12,
        position: 'relative',
        overflow: 'hidden',
      }}>
        <div style={{
          position: 'absolute', inset: 0,
          background: `radial-gradient(circle at 50% 0%, ${recColor}11, transparent 70%)`,
          pointerEvents: 'none',
        }} />
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', position: 'relative' }}>
          <div>
            <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-secondary)', marginBottom: 2 }}>Trust Decision</div>
            <div style={{ fontSize: 'var(--text-2xl)', fontWeight: '800', color: recColor, letterSpacing: '-1px', fontFamily: 'var(--font-mono)' }}>
              {recLabel}
            </div>
          </div>
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>P(Human)</div>
            <div style={{ fontSize: 'var(--text-lg)', fontWeight: '700', color: recColor, fontFamily: 'var(--font-mono)' }}>
              {(hps / 100).toFixed(1)}%
            </div>
          </div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-2)', marginBottom: 12 }}>
        <div className="stat-card" style={{ padding: 'var(--space-3)' }}>
          <div className="stat-label">Score</div>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--text-md)', fontWeight: 700, color: hps >= 7000 ? 'var(--signal-human-text)' : 'var(--text-primary)' }}>
            {hps.toLocaleString()}
          </div>
        </div>
        <div className="stat-card" style={{ padding: 'var(--space-3)' }}>
          <div className="stat-label">Status</div>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--text-md)', fontWeight: 700, color: isTrusted ? 'var(--signal-human-text)' : 'var(--signal-agent-text)' }}>
            {isTrusted ? 'TRUSTED' : 'UNTRUSTED'}
          </div>
        </div>
      </div>

      {result.explanation && result.explanation.length > 0 && (
        <div style={{ marginBottom: 12 }}>
          <div className="label-caps" style={{ marginBottom: 6 }}>Key Signals</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            {result.explanation.slice(0, 5).map((feat, i) => {
              const contrib = feat.contribution || feat.shap || 0;
              const isHumanSignal = contrib > 0;
              const label = FEATURE_LABELS[feat.feature || feat.name] || (feat.feature || feat.name || '').replace(/_/g, ' ');
              return (
                <div key={i} className="data-row" style={{ padding: '4px 8px', animation: `fade-in-up ${200 + i * 50}ms var(--ease-out) both` }}>
                  <div style={{ flex: 1, fontSize: 'var(--text-2xs)', color: 'var(--text-tertiary)', fontFamily: 'var(--font-mono)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{label}</div>
                  <div style={{
                    fontSize: 'var(--text-2xs)', fontFamily: 'var(--font-mono)', fontWeight: 600,
                    color: isHumanSignal ? 'var(--signal-human-text)' : 'var(--signal-agent-text)',
                  }}>
                    {isHumanSignal ? '+' : ''}{(contrib * 100).toFixed(1)}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
        {onHandshake && (
          <button onClick={() => onHandshake(result.address)} style={{
            flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
            padding: '8px 12px', borderRadius: 'var(--radius-sm)',
            border: '1px solid var(--accent-purple-border)',
            background: 'var(--accent-purple-glow)', color: 'var(--accent-purple)',
            fontSize: 'var(--text-xs)', fontWeight: 600, cursor: 'pointer',
            fontFamily: 'var(--font-sans)',
            transition: 'all var(--duration-fast) ease',
          }}>
            <Shuffle size={12} /> Handshake
          </button>
        )}
      </div>
    </div>
  );
}

function HandshakeVisualization({ result, ghostAddress }) {
  if (!result) return null;

  const { addressA, addressB, hpsA, hpsB, dealConfidence, threshold, recommendation, suggestedAdjustments } = result;
  const recColor = recommendation === 'proceed' ? 'var(--signal-human)' : recommendation === 'proceed_with_caution' ? 'var(--signal-uncertain)' : 'var(--signal-agent)';
  const recLabel = recommendation === 'proceed' ? 'PROCEED' : recommendation === 'proceed_with_caution' ? 'PROCEED WITH CAUTION' : 'REJECT';

  return (
    <div style={{ animation: 'fade-in-up 400ms var(--ease-out) both' }}>
      <div className="label-caps" style={{ marginBottom: 12, textAlign: 'center' }}>Mutual Trust Handshake</div>

      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8, marginBottom: 16 }}>
        <div style={{ textAlign: 'center', flex: 1 }}>
          <MiniGauge score={hpsA} size={64} />
          <div style={{ fontSize: 'var(--text-2xs)', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', marginTop: 4, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: 80 }}>
            {addressA.slice(0, 6)}...
          </div>
          <div style={{ fontSize: 'var(--text-xs)', fontWeight: 700, color: hpsA >= threshold ? 'var(--signal-human-text)' : 'var(--signal-agent-text)', fontFamily: 'var(--font-mono)' }}>
            {hpsA.toLocaleString()}
          </div>
        </div>

        <div style={{ textAlign: 'center', flex: 0.6 }}>
          <div style={{ fontSize: 20, color: 'var(--text-muted)', marginBottom: 4 }}>⟷</div>
          <div style={{
            padding: '4px 10px', borderRadius: 20,
            background: `${recColor}15`,
            border: `1px solid ${recColor}33`,
            fontSize: 'var(--text-2xs)', fontFamily: 'var(--font-mono)', fontWeight: 700,
            color: recColor,
          }}>
            {recLabel}
          </div>
        </div>

        <div style={{ textAlign: 'center', flex: 1 }}>
          <MiniGauge score={hpsB} size={64} />
          <div style={{ fontSize: 'var(--text-2xs)', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', marginTop: 4, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: 80 }}>
            {addressB.slice(0, 6)}...
          </div>
          <div style={{ fontSize: 'var(--text-xs)', fontWeight: 700, color: hpsB >= threshold ? 'var(--signal-human-text)' : 'var(--signal-agent-text)', fontFamily: 'var(--font-mono)' }}>
            {hpsB.toLocaleString()}
          </div>
        </div>
      </div>

      <div style={{
        padding: 'var(--space-3) var(--space-4)',
        borderRadius: 'var(--radius-md)',
        border: `1px solid ${recColor}33`,
        background: `${recColor}08`,
        marginBottom: 12,
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
          <span style={{ fontSize: 'var(--text-2xs)', color: 'var(--text-muted)', letterSpacing: '1px', textTransform: 'uppercase' }}>Deal Confidence</span>
          <span style={{ fontSize: 'var(--text-md)', fontWeight: 700, fontFamily: 'var(--font-mono)', color: recColor }}>
            {dealConfidence.toLocaleString()}
          </span>
        </div>
        <div style={{ height: 6, background: 'var(--bg-elevated)', borderRadius: 3, overflow: 'hidden' }}>
          <div style={{
            height: '100%', width: `${Math.min(100, (dealConfidence / 10000) * 100)}%`,
            background: recColor, borderRadius: 3,
            transition: 'width 800ms var(--ease-out)',
            boxShadow: `0 0 8px ${recColor}`,
          }} />
        </div>
      </div>

      {suggestedAdjustments && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-2)' }}>
          <div className="stat-card" style={{ padding: 'var(--space-3)' }}>
            <div className="stat-label">Max Trade Size</div>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--text-md)', fontWeight: 700, color: suggestedAdjustments.maxTradeFraction >= 1 ? 'var(--signal-human-text)' : 'var(--signal-uncertain-text)' }}>
              {(suggestedAdjustments.maxTradeFraction * 100).toFixed(0)}%
            </div>
          </div>
          <div className="stat-card" style={{ padding: 'var(--space-3)' }}>
            <div className="stat-label">Slippage Delta</div>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--text-md)', fontWeight: 700, color: suggestedAdjustments.slippageBpsDelta > 0 ? 'var(--signal-uncertain-text)' : 'var(--text-primary)' }}>
              +{suggestedAdjustments.slippageBpsDelta} bps
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function SelfAuditView({ results, addresses, onCheck }) {
  if (results.length === 0 && addresses.length === 0) {
    return (
      <div style={{ padding: 'var(--space-6)', textAlign: 'center', color: 'var(--text-muted)' }}>
        <Users size={24} style={{ marginBottom: 8, opacity: 0.5 }} />
        <div style={{ fontSize: 'var(--text-sm)', color: 'var(--text-secondary)' }}>Run a self-audit on your agent fleet</div>
        <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-tertiary)', marginTop: 4 }}>Enter addresses separated by commas</div>
      </div>
    );
  }

  if (results.length === 0 && addresses.length > 0 && results.length === 0) {
    return (
      <div style={{ padding: 'var(--space-6)', textAlign: 'center', color: 'var(--text-muted)' }}>
        <div style={{ fontSize: 24, marginBottom: 8, animation: 'pulse-dot 1s ease-in-out infinite' }}>◉</div>
        <div>Scanning fleet...</div>
      </div>
    );
  }

  const flagged = results.filter(r => r.flag);
  const meanHps = results.length > 0 ? results.reduce((s, r) => s + (r.hps || 0), 0) / results.length : 0;
  const clusterRisk = flagged.length > results.length / 2 ? 'high' : flagged.length > 0 ? 'moderate' : 'low';
  const riskColor = clusterRisk === 'high' ? 'var(--signal-agent)' : clusterRisk === 'moderate' ? 'var(--signal-uncertain)' : 'var(--signal-human)';

  return (
    <div style={{ animation: 'fade-in-up 300ms var(--ease-out) both' }}>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 'var(--space-2)', marginBottom: 12 }}>
        <div className="stat-card" style={{ padding: 'var(--space-3)' }}>
          <div className="stat-label">Fleet Size</div>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--text-lg)', fontWeight: 700 }}>
            {results.length}
          </div>
        </div>
        <div className="stat-card" style={{ padding: 'var(--space-3)' }}>
          <div className="stat-label">Mean HPS</div>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--text-lg)', fontWeight: 700, color: meanHps >= 7000 ? 'var(--signal-human-text)' : meanHps >= 5000 ? 'var(--signal-uncertain-text)' : 'var(--signal-agent-text)' }}>
            {meanHps.toFixed(0)}
          </div>
        </div>
        <div className="stat-card" style={{ padding: 'var(--space-3)', borderColor: riskColor }}>
          <div className="stat-label">Cluster Risk</div>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--text-lg)', fontWeight: 700, color: riskColor }}>
            {clusterRisk.toUpperCase()}
          </div>
        </div>
      </div>

      <div className="scroll-area" style={{ maxHeight: 200 }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          {results.map((r, i) => (
            <div key={i} className="data-row" style={{
              padding: 'var(--space-2) var(--space-3)',
              borderColor: r.flag ? 'var(--signal-agent-border)' : 'transparent',
              background: r.flag ? 'var(--signal-agent-glow)' : 'transparent',
              animation: `fade-in-up ${100 + i * 30}ms var(--ease-out) both`,
            }}>
              <div style={{ flex: 1, fontSize: 'var(--text-2xs)', fontFamily: 'var(--font-mono)', color: 'var(--text-tertiary)' }}>
                {r.address.slice(0, 8)}...{r.address.slice(-6)}
              </div>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--text-xs)', fontWeight: 600, color: r.hps >= 7000 ? 'var(--signal-human-text)' : r.hps >= 5000 ? 'var(--signal-uncertain-text)' : 'var(--signal-agent-text)' }}>
                {r.hps?.toLocaleString() || '—'}
              </div>
              {r.weakDims?.length > 0 && (
                <div style={{ fontSize: 'var(--text-2xs)', color: 'var(--signal-agent-text)', fontFamily: 'var(--font-mono)' }}>
                  ⚠ {r.weakDims.map(d => d.dimension).join(', ')}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {flagged.length > 0 && (
        <div style={{
          marginTop: 8, padding: 'var(--space-3)',
          borderRadius: 'var(--radius-sm)',
          border: '1px solid var(--signal-uncertain-border)',
          background: 'var(--signal-uncertain-glow)',
          fontSize: 'var(--text-2xs)', color: 'var(--signal-uncertain-text)',
          fontFamily: 'var(--font-mono)', lineHeight: 1.6,
        }}>
          ▶ {flagged.length} wallet{flagged.length > 1 ? 's' : ''} flagged. Run NetworkTopologyModule-style EOA peer transfers and diversify funding sources.
        </div>
      )}
    </div>
  );
}

function TrustNarrative({ result }) {
  if (!result || !result.hps) return null;

  const { hps, recommendation, trusted } = result;
  const parts = [];

  parts.push(`This wallet has a Human Probability Score of ${hps.toLocaleString()}/10000.`);

  if (recommendation === 'proceed') parts.push('It clears the requested trust threshold with high confidence.');
  else if (recommendation === 'proceed_with_caution') parts.push('It clears the threshold, but extra caution is advised.');
  else if (recommendation === 'reject') parts.push('It falls below the requested trust threshold.');
  else parts.push('There is not enough data to make a confident trust decision.');

  if (result.explanation?.length > 0) {
    const top = result.explanation.slice(0, 3);
    const signals = top.map(f => {
      const label = FEATURE_LABELS[f.feature || f.name] || (f.feature || f.name || '').replace(/_/g, ' ');
      return label;
    });
    parts.push('Key signals: ' + signals.join('; ') + '.');
  }

  const narrative = parts.join(' ');

  return (
    <div style={{
      marginTop: 8, padding: 'var(--space-3)',
      borderRadius: 'var(--radius-sm)',
      border: '1px solid var(--border-subtle)',
      background: 'var(--surface-01)',
      fontSize: 'var(--text-xs)', color: 'var(--text-secondary)',
      lineHeight: 1.7,
      position: 'relative',
      overflow: 'hidden',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6 }}>
        <Info size={10} color="var(--accent-purple)" />
        <span style={{ fontSize: 'var(--text-2xs)', color: 'var(--accent-purple)', letterSpacing: '1px', fontWeight: 600, textTransform: 'uppercase' }}>Trust Narrative</span>
      </div>
      {narrative}
    </div>
  );
}

export default function RealclawTrustPanel({
  ghostAddress,
  trust,
}) {
  const [inputAddress, setInputAddress] = useState('');
  const [activeTab, setActiveTabLocal] = useState('check');
  const [auditInput, setAuditInput] = useState('');
  const [lastResult, setLastResult] = useState(null);
  const [showNarrative, setShowNarrative] = useState(true);
  const [handshakeA, setHandshakeA] = useState('');
  const [handshakeB, setHandshakeB] = useState('');

  const {
    checks,
    setActiveTab,
    handshakeResult,
    setHandshakeResult,
    auditResults,
    auditAddresses,
    isChecking,
    currentOp,
    error,
    tier,
    setTier,
    checkWallet,
    runHandshake,
    runSelfAudit,
    getScoreColor,
    getRecommendationColor,
    getRecommendationLabel,
  } = trust;

  const handleCheck = async () => {
    if (!inputAddress || isChecking) return;
    const result = await checkWallet(inputAddress);
    if (result) {
      setLastResult(result);
      setActiveTabLocal('check');
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') handleCheck();
  };

  const handleHandshake = async (counterparty) => {
    if (!ghostAddress || !counterparty) return;
    await runHandshake(ghostAddress, counterparty);
    setActiveTabLocal('handshake');
  };

  const handleSelfAudit = () => {
    const addresses = auditInput
      .split(/[\s,]+/)
      .filter(a => a.match(/^0x[a-fA-F0-9]{40}$/));
    if (addresses.length > 0) {
      runSelfAudit(addresses);
    }
  };

  const handleQuickCheck = (addr) => {
    setInputAddress(addr);
    checkWallet(addr).then(r => { if (r) setLastResult(r); });
  };

  const tabs = [
    { key: 'check', label: 'Check Wallet', icon: Search },
    { key: 'handshake', label: 'Handshake', icon: Shuffle },
    { key: 'audit', label: 'Self-Audit', icon: Users },
  ];

  const latestCheck = checks.find(c => c.status === 'complete') || lastResult;

  return (
    <div className="panel" style={{
      animation: 'fade-in-up 400ms 100ms var(--ease-out) both',
      position: 'relative',
      overflow: 'hidden',
    }}>
      <div style={{
        position: 'absolute', top: -100, right: -100, width: 200, height: 200,
        borderRadius: '50%',
        background: 'radial-gradient(circle, rgba(167, 139, 250, 0.04), transparent 70%)',
        pointerEvents: 'none',
      }} />

      <div className="panel-header">
        <div className="panel-title">TURING TRUST LAYER</div>
        <div className="panel-subtitle">RealClaw Skill · Proof-of-Humanity gate</div>
      </div>

      <div style={{
        display: 'flex', gap: 0,
        background: 'var(--surface-01)',
        borderRadius: 'var(--radius-md)', padding: 3,
        border: '1px solid var(--border-subtle)',
      }}>
        {tabs.map(({ key, label, icon: Icon }) => (
          <button key={key}
            onClick={() => { setActiveTabLocal(key); setActiveTab(key); }}
            style={{
              flex: 1, padding: '6px 8px', borderRadius: 'var(--radius-sm)',
              border: 'none',
              display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 5,
              background: activeTab === key ? 'var(--bg-elevated)' : 'transparent',
              color: activeTab === key ? 'var(--text-primary)' : 'var(--text-muted)',
              fontSize: 'var(--text-2xs)', fontWeight: activeTab === key ? '600' : '400',
              cursor: 'pointer', letterSpacing: '0.5px',
              transition: 'all var(--duration-fast) ease',
            }}>
            <Icon size={11} />
            {label}
          </button>
        ))}
      </div>

      {/* Tier selector */}
      <div style={{ display: 'flex', gap: 4 }}>
        {['lenient', 'standard', 'strict'].map(t => (
          <button key={t} onClick={() => setTier(t)} style={{
            flex: 1, padding: '3px 6px', borderRadius: 'var(--radius-sm)',
            border: `1px solid ${tier === t ? 'var(--accent-purple-border)' : 'var(--border-subtle)'}`,
            background: tier === t ? 'var(--accent-purple-glow)' : 'transparent',
            color: tier === t ? 'var(--accent-purple)' : 'var(--text-muted)',
            fontSize: 'var(--text-2xs)', fontWeight: tier === t ? 700 : 400,
            fontFamily: 'var(--font-mono)', cursor: 'pointer',
            textTransform: 'uppercase', letterSpacing: '1px',
            transition: 'all var(--duration-fast) ease',
          }}>
            {t} {(t === 'lenient' ? '3000' : t === 'standard' ? '7000' : '8000')}
          </button>
        ))}
      </div>

      {/* Check Wallet Tab */}
      {activeTab === 'check' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {currentOp && currentOp !== 'check' && (
            <div style={{ padding: 'var(--space-3)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--signal-uncertain-border)', background: 'var(--signal-uncertain-glow)', fontSize: 'var(--text-2xs)', color: 'var(--signal-uncertain-text)', fontFamily: 'var(--font-mono)', textAlign: 'center' }}>
              {currentOp === 'handshake' ? '⟳ Handshake evaluation in progress...' : '⟳ Fleet audit in progress...'}
            </div>
          )}
          <div style={{ display: 'flex', gap: 6 }}>
            <input
              value={inputAddress}
              onChange={e => setInputAddress(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="0x... wallet address"
              style={{
                flex: 1, padding: '8px 12px',
                background: 'var(--bg-elevated)',
                border: '1px solid var(--border-default)',
                borderRadius: 'var(--radius-sm)',
                color: 'var(--text-primary)',
                fontSize: 'var(--text-xs)',
                fontFamily: 'var(--font-mono)',
                outline: 'none',
              }}
            />
            <button onClick={handleCheck} disabled={isChecking || !inputAddress} style={{
              padding: '8px 14px',
              background: 'var(--accent-purple-glow)',
              border: '1px solid var(--accent-purple-border)',
              borderRadius: 'var(--radius-sm)',
              color: 'var(--accent-purple)',
              cursor: isChecking ? 'wait' : 'pointer',
              fontSize: 'var(--text-xs)', fontWeight: 600,
              fontFamily: 'var(--font-sans)',
              opacity: isChecking || !inputAddress ? 0.5 : 1,
            }}>
              {currentOp === 'check' ? 'Checking...' : 'Check'}
            </button>
          </div>

          <div style={{
            display: 'flex', flexWrap: 'wrap', gap: 4,
            padding: 'var(--space-2) var(--space-3)',
            background: 'var(--surface-01)',
            borderRadius: 'var(--radius-sm)',
            border: '1px solid var(--border-subtle)',
          }}>
            <span style={{ fontSize: 'var(--text-2xs)', color: 'var(--text-muted)', marginRight: 4 }}>Quick:</span>
            <button onClick={() => handleQuickCheck('0xE0E216283eef00895b6ABAa73848448596B85724')} style={{
              fontSize: 'var(--text-2xs)', fontFamily: 'var(--font-mono)', color: 'var(--accent-purple)',
              background: 'transparent', border: 'none', cursor: 'pointer', padding: '1px 4px',
            }}>amankrisz.eth</button>
            <button onClick={() => handleQuickCheck(ghostAddress)} style={{
              fontSize: 'var(--text-2xs)', fontFamily: 'var(--font-mono)', color: 'var(--signal-uncertain)',
              background: 'transparent', border: 'none', cursor: 'pointer', padding: '1px 4px',
            }}>ghost</button>
            <button onClick={() => handleQuickCheck('0x8080AC2cDf955d82B0B6670f1538DD1029ad1329')} style={{
              fontSize: 'var(--text-2xs)', fontFamily: 'var(--font-mono)', color: 'var(--signal-agent)',
              background: 'transparent', border: 'none', cursor: 'pointer', padding: '1px 4px',
            }}>sybil</button>
          </div>

          {error && (
            <div style={{
              padding: 'var(--space-2) var(--space-3)',
              borderRadius: 'var(--radius-sm)',
              border: '1px solid var(--signal-agent-border)',
              background: 'var(--signal-agent-glow)',
              fontSize: 'var(--text-2xs)', color: 'var(--signal-agent-text)',
              fontFamily: 'var(--font-mono)',
            }}>
              {error}
            </div>
          )}

          <div className="scroll-area" style={{ flex: 1, minHeight: 0 }}>
            {latestCheck && (
              <div>
                <TrustResultCard result={latestCheck} onHandshake={handleHandshake} />
                {showNarrative && <TrustNarrative result={latestCheck} />}
              </div>
            )}
            {!latestCheck && (
              <div style={{ padding: 'var(--space-6)', textAlign: 'center', color: 'var(--text-muted)' }}>
                <Shield size={28} style={{ marginBottom: 8, opacity: 0.3 }} />
                <div style={{ fontSize: 'var(--text-sm)', color: 'var(--text-tertiary)' }}>Enter a wallet address to check trust</div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Handshake Tab */}
      {activeTab === 'handshake' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {currentOp && currentOp !== 'handshake' && (
            <div style={{ padding: 'var(--space-3)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--signal-uncertain-border)', background: 'var(--signal-uncertain-glow)', fontSize: 'var(--text-2xs)', color: 'var(--signal-uncertain-text)', fontFamily: 'var(--font-mono)', textAlign: 'center' }}>
              {currentOp === 'check' ? '⟳ Wallet check in progress...' : '⟳ Fleet audit in progress...'}
            </div>
          )}
          {error && (
            <div style={{
              padding: 'var(--space-2) var(--space-3)',
              borderRadius: 'var(--radius-sm)',
              border: '1px solid var(--signal-agent-border)',
              background: 'var(--signal-agent-glow)',
              fontSize: 'var(--text-2xs)', color: 'var(--signal-agent-text)',
              fontFamily: 'var(--font-mono)',
            }}>
              {error}
            </div>
          )}
          {!handshakeResult && !isChecking && (
            <div style={{ textAlign: 'center', color: 'var(--text-muted)' }}>
              <Shuffle size={24} style={{ marginBottom: 8, opacity: 0.3 }} />
              <div style={{ fontSize: 'var(--text-sm)', color: 'var(--text-tertiary)' }}>Enter two addresses to evaluate mutual trust</div>
              <div style={{ display: 'flex', gap: 6, marginTop: 12, minWidth: 0 }}>
                <input
                  value={handshakeA}
                  onChange={e => { setHandshakeA(e.target.value); setError(null); }}
                  placeholder="Address A (me)"
                  style={{ flex: 1, minWidth: 0, padding: '8px 10px', background: 'var(--bg-elevated)', border: '1px solid var(--border-default)', borderRadius: 'var(--radius-sm)', color: 'var(--text-primary)', fontSize: 'var(--text-xs)', fontFamily: 'var(--font-mono)', outline: 'none', textOverflow: 'ellipsis', overflow: 'hidden', whiteSpace: 'nowrap' }}
                />
                <input
                  value={handshakeB}
                  onChange={e => { setHandshakeB(e.target.value); setError(null); }}
                  placeholder="Address B"
                  style={{ flex: 1, minWidth: 0, padding: '8px 10px', background: 'var(--bg-elevated)', border: '1px solid var(--border-default)', borderRadius: 'var(--radius-sm)', color: 'var(--text-primary)', fontSize: 'var(--text-xs)', fontFamily: 'var(--font-mono)', outline: 'none', textOverflow: 'ellipsis', overflow: 'hidden', whiteSpace: 'nowrap' }}
                />
              </div>
              <button onClick={() => runHandshake(handshakeA, handshakeB)} disabled={!handshakeA.match(/^0x[a-fA-F0-9]{40}$/) || !handshakeB.match(/^0x[a-fA-F0-9]{40}$/)} style={{
                marginTop: 12, padding: '8px 14px', width: '100%',
                background: 'var(--accent-purple-glow)',
                border: '1px solid var(--accent-purple-border)',
                borderRadius: 'var(--radius-sm)',
                color: 'var(--accent-purple)',
                cursor: 'pointer',
                fontSize: 'var(--text-xs)', fontWeight: 600,
                fontFamily: 'var(--font-sans)',
                opacity: !handshakeA.match(/^0x[a-fA-F0-9]{40}$/) || !handshakeB.match(/^0x[a-fA-F0-9]{40}$/) ? 0.5 : 1,
              }}>
                Evaluate Handshake
              </button>
            </div>
          )}
          {currentOp === 'handshake' && (
            <div style={{ padding: 'var(--space-8)', textAlign: 'center', color: 'var(--text-muted)' }}>
              <div style={{ fontSize: 24, marginBottom: 8, animation: 'pulse-dot 1s ease-in-out infinite' }}>◉</div>
              <div style={{ fontSize: 'var(--text-sm)', fontFamily: 'var(--font-mono)' }}>Evaluating handshake...</div>
              <div style={{ fontSize: 'var(--text-2xs)', color: 'var(--text-tertiary)', marginTop: 4, fontFamily: 'var(--font-mono)' }}>
                {handshakeA.slice(0, 8)}... ⟷ {handshakeB.slice(0, 8)}...
              </div>
            </div>
          )}
          {handshakeResult && (
            <div>
              <HandshakeVisualization result={handshakeResult} ghostAddress={ghostAddress} />
              <button onClick={() => { setHandshakeResult(null); setError(null); }} style={{
                marginTop: 8, width: '100%', padding: '6px',
                background: 'transparent', border: '1px solid var(--border-subtle)',
                borderRadius: 'var(--radius-sm)', color: 'var(--text-muted)',
                fontSize: 'var(--text-2xs)', cursor: 'pointer',
              }}>
                New Handshake
              </button>
            </div>
          )}
        </div>
      )}

      {/* Self-Audit Tab */}
      {activeTab === 'audit' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {currentOp && currentOp !== 'audit' && (
            <div style={{ padding: 'var(--space-3)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--signal-uncertain-border)', background: 'var(--signal-uncertain-glow)', fontSize: 'var(--text-2xs)', color: 'var(--signal-uncertain-text)', fontFamily: 'var(--font-mono)', textAlign: 'center' }}>
              {currentOp === 'check' ? '⟳ Wallet check in progress...' : '⟳ Handshake evaluation in progress...'}
            </div>
          )}
          <div style={{ display: 'flex', gap: 6 }}>
            <input
              value={auditInput}
              onChange={e => setAuditInput(e.target.value)}
              placeholder="0x..., 0x..., 0x... (comma separated)"
              style={{
                flex: 1, padding: '8px 12px',
                background: 'var(--bg-elevated)',
                border: '1px solid var(--border-default)',
                borderRadius: 'var(--radius-sm)',
                color: 'var(--text-primary)',
                fontSize: 'var(--text-xs)',
                fontFamily: 'var(--font-mono)',
                outline: 'none',
              }}
            />
            <button onClick={handleSelfAudit} disabled={isChecking || !auditInput} style={{
              padding: '8px 14px',
              background: 'var(--signal-uncertain-glow)',
              border: '1px solid var(--signal-uncertain-border)',
              borderRadius: 'var(--radius-sm)',
              color: 'var(--signal-uncertain-text)',
              cursor: isChecking ? 'wait' : 'pointer',
              fontSize: 'var(--text-xs)', fontWeight: 600,
              opacity: isChecking || !auditInput ? 0.5 : 1,
            }}>
              {currentOp === 'audit' ? 'Auditing...' : 'Audit'}
            </button>
          </div>
          <SelfAuditView results={auditResults} addresses={auditAddresses} />
        </div>
      )}

      <div style={{
        borderTop: '1px solid var(--border-subtle)',
        paddingTop: 'var(--space-2)',
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
      }}>
        <span style={{ fontSize: 'var(--text-2xs)', color: 'var(--text-muted)', letterSpacing: '1px' }}>
          READ-ONLY · NON-CUSTODIAL
        </span>
        <label style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 'var(--text-2xs)', color: 'var(--text-muted)', cursor: 'pointer' }}>
          <input type="checkbox" checked={showNarrative} onChange={e => setShowNarrative(e.target.checked)}
            style={{ accentColor: 'var(--accent-purple)' }} />
          Narrative
        </label>
      </div>
    </div>
  );
}
