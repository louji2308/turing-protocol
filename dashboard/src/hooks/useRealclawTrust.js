import { useState, useEffect, useCallback, useRef } from 'react';

const TRUST_TIERS = {
  lenient: 3000,
  standard: 7000,
  strict: 8000,
};

export function useRealclawTrust(ghostAddress) {
  const [checks, setChecks] = useState([]);
  const [activeTab, setActiveTab] = useState('check');
  const [handshakeResult, setHandshakeResult] = useState(null);
  const [auditResults, setAuditResults] = useState([]);
  const [auditAddresses, setAuditAddresses] = useState([]);
  const [isChecking, setIsChecking] = useState(false);
  const [currentOp, setCurrentOp] = useState(null);
  const [error, setError] = useState(null);
  const [tier, setTier] = useState('standard');
  const [includeNarrative, setIncludeNarrative] = useState(true);

  const apiBase = import.meta.env.VITE_ORACLE_API || 'http://localhost:8080';
  const checksRef = useRef(checks);
  checksRef.current = checks;

  const getScoreColor = (s) => {
    if (s >= 8000) return 'var(--signal-human)';
    if (s >= 7000) return 'var(--signal-human-dim)';
    if (s >= 5000) return 'var(--signal-uncertain)';
    if (s >= 3000) return 'var(--signal-agent-dim)';
    return 'var(--signal-agent)';
  };

  const getRecommendationColor = (rec) => {
    switch (rec) {
      case 'proceed': return 'var(--signal-human)';
      case 'proceed_with_caution': return 'var(--signal-uncertain)';
      case 'reject': return 'var(--signal-agent)';
      default: return 'var(--text-muted)';
    }
  };

  const getRecommendationLabel = (rec) => {
    switch (rec) {
      case 'proceed': return 'PROCEED';
      case 'proceed_with_caution': return 'CAUTION';
      case 'reject': return 'REJECT';
      case 'insufficient_data': return 'NO DATA';
      default: return rec?.toUpperCase() || 'UNKNOWN';
    }
  };

  const classifyScore = (s) => {
    if (s === null || s === undefined) return { label: 'UNKNOWN', tier: 'unknown' };
    if (s >= 8500) return { label: 'DEFINITELY HUMAN', tier: 'human' };
    if (s >= 7000) return { label: 'LIKELY HUMAN', tier: 'human' };
    if (s >= 5500) return { label: 'UNCERTAIN', tier: 'uncertain' };
    if (s >= 3000) return { label: 'LIKELY AGENT', tier: 'agent' };
    return { label: 'DEFINITELY AGENT', tier: 'agent' };
  };

  const checkWallet = useCallback(async (address, options = {}) => {
    if (!address || !address.match(/^0x[a-fA-F0-9]{40}$/)) {
      setError('Invalid Ethereum address');
      return null;
    }

    setCurrentOp('check');
    setIsChecking(true);
    setError(null);

    const effectiveTier = options.tier || tier;
    const threshold = TRUST_TIERS[effectiveTier] || 7000;

    const entry = {
      address,
      tier: effectiveTier,
      threshold,
      status: 'checking',
      timestamp: Date.now(),
    };
    setChecks(prev => [entry, ...prev.slice(0, 9)]);

    try {
      const resp = await fetch(
        `${apiBase}/score/${address}?include_explanation=true`,
        { signal: AbortSignal.timeout(45000) }
      );

      if (!resp.ok) {
        let msg = `API returned ${resp.status}`;
        try { const body = await resp.json(); if (body.detail) msg = body.detail; } catch {}
        throw new Error(msg);
      }

      const data = await resp.json();
      const hps = data.hps ?? data.score ?? 0;
      const explanation = data.explanation || [];
      const dimensions = data.details || {};

      const trusted = hps >= threshold;
      const isLowConfidence = hps > 0 && hps < threshold * 0.8;
      let recommendation = 'insufficient_data';
      if (hps === 0) {
        recommendation = 'insufficient_data';
      } else if (trusted) {
        recommendation = isLowConfidence ? 'proceed_with_caution' : 'proceed';
      } else {
        recommendation = 'reject';
      }

      const classification = classifyScore(hps);
      const sortedExplanation = Array.isArray(explanation)
        ? [...explanation].sort((a, b) => Math.abs(b.contribution || b.shap || 0) - Math.abs(a.contribution || a.shap || 0))
        : [];

      const result = {
        address,
        tier: effectiveTier,
        threshold,
        hps,
        trusted,
        recommendation,
        classification: classification.label,
        classificationTier: classification.tier,
        explanation: sortedExplanation,
        dimensions,
        source: 'oracle_api',
        timestamp: Date.now(),
      };

      setChecks(prev => prev.map(c =>
        c.address.toLowerCase() === address.toLowerCase() && c.status === 'checking'
          ? { ...result, status: 'complete' }
          : c
      ));

      return result;
    } catch (err) {
      const errorResult = {
        address,
        tier: effectiveTier,
        threshold,
        hps: null,
        trusted: false,
        recommendation: 'error',
        error: err.message,
        status: 'error',
        timestamp: Date.now(),
      };
      setChecks(prev => prev.map(c =>
        c.address.toLowerCase() === address.toLowerCase() && c.status === 'checking'
          ? errorResult
          : c
      ));
      setError(err.message);
      return null;
    } finally {
      setCurrentOp(null);
      setIsChecking(false);
    }
  }, [apiBase, tier]);

  const runHandshake = useCallback(async (addressA, addressB, options = {}) => {
    setCurrentOp('handshake');
    setIsChecking(true);
    setError(null);

    const effectiveTier = options.tier || tier;
    const threshold = TRUST_TIERS[effectiveTier] || 7000;

    try {
      const [respA, respB] = await Promise.all([
        fetch(`${apiBase}/score/${addressA}`, { signal: AbortSignal.timeout(45000) }),
        fetch(`${apiBase}/score/${addressB}`, { signal: AbortSignal.timeout(45000) }),
      ]);

      if (!respA.ok || !respB.ok) {
        const failA = !respA.ok;
        const failB = !respB.ok;
        let extra = '';
        try {
          if (failA) { const b = await respA.json(); if (b.detail) extra = ` A: ${b.detail}`; }
          if (failB) { const b = await respB.json(); if (b.detail) extra += ` B: ${b.detail}`; }
        } catch {}
        throw new Error(`Handshake failed${extra}`);
      }

      const dataA = await respA.json();
      const dataB = await respB.json();

      const hpsA = dataA.hps ?? dataA.score ?? 0;
      const hpsB = dataB.hps ?? dataB.score ?? 0;
      const dealConfidence = Math.min(hpsA, hpsB);

      let rec, frac, slipDelta;
      if (dealConfidence >= threshold) {
        rec = 'proceed'; frac = 1.0; slipDelta = 0;
      } else if (dealConfidence >= threshold * 0.7) {
        rec = 'proceed_with_caution'; frac = 0.5; slipDelta = 25;
      } else {
        rec = 'reject'; frac = 0.0; slipDelta = 0;
      }

      const result = {
        addressA,
        addressB,
        hpsA,
        hpsB,
        dealConfidence,
        threshold,
        tier: effectiveTier,
        recommendation: rec,
        suggestedAdjustments: {
          maxTradeFraction: frac,
          slippageBpsDelta: slipDelta,
        },
      };

      setHandshakeResult(result);
      return result;
    } catch (err) {
      setError(err.message);
      return null;
    } finally {
      setCurrentOp(null);
      setIsChecking(false);
    }
  }, [apiBase, tier]);

  const runSelfAudit = useCallback(async (addresses) => {
    if (!addresses || addresses.length === 0) {
      setError('No addresses provided');
      return;
    }

    setCurrentOp('audit');
    setIsChecking(true);
    setError(null);
    setAuditAddresses(addresses);

    const results = [];
    try {
      for (const addr of addresses) {
        try {
          const resp = await fetch(
            `${apiBase}/score/${addr}`,
            { signal: AbortSignal.timeout(45000) }
          );
          if (resp.ok) {
            const data = await resp.json();
            const hps = data.hps ?? data.score ?? 0;
            const dims = data.details || {};
            const weakDims = Object.entries(dims)
              .filter(([k, v]) => v !== null && v < 30 && !['ip_fingerprint', 'cross_chain'].includes(k))
              .map(([k, v]) => ({ dimension: k, score: v }));
            results.push({ address: addr, hps, weakDims, flag: hps < 5000 || weakDims.length > 0 });
          } else {
            let detail = `HTTP ${resp.status}`;
            try { const b = await resp.json(); if (b.detail) detail = b.detail; } catch {}
            results.push({ address: addr, hps: null, weakDims: [], flag: false, error: detail });
          }
        } catch {
          results.push({ address: addr, hps: null, weakDims: [], flag: false, error: 'fetch_failed' });
        }
      }

      setAuditResults(results);
      return results;
    } finally {
      setCurrentOp(null);
      setIsChecking(false);
    }
  }, [apiBase]);

  return {
    checks,
    activeTab,
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
    includeNarrative,
    setIncludeNarrative,
    checkWallet,
    runHandshake,
    runSelfAudit,
    getScoreColor,
    getRecommendationColor,
    getRecommendationLabel,
    classifyScore,
    TRUST_TIERS,
  };
}
