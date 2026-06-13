import { useState, useEffect, useCallback, useRef } from 'react';
import { ethers } from 'ethers';
import HPSOracleData from '../abi/HPSOracle.json';
import POBData from '../abi/ProofOfBehavior.json';
import { ORACLE_API, MANTLE_RPC, POLL_INTERVAL_MS } from '../config';

export function useOracleEvents(ghostAddress) {
  const [ghostScore, setGhostScore] = useState(5000);
  const [previousScore, setPreviousScore] = useState(5000);
  const [scoreHistory, setScoreHistory] = useState([]);
  const [latestEvent, setLatestEvent] = useState(null);
  const [recentProofs, setRecentProofs] = useState([]);
  const [totalFreshProofs, setTotalFreshProofs] = useState(0);
  const [totalMinted, setTotalMinted] = useState(0);
  const [oracleStats, setOracleStats] = useState(null);
  const [connectionStatus, setConnectionStatus] = useState('connecting');
  const [lastUpdateTime, setLastUpdateTime] = useState(null);
  const [modelVersion, setModelVersion] = useState(null);

  const providerRef = useRef(null);
  const oracleRef = useRef(null);
  const pobRef = useRef(null);
  const pollIntervalRef = useRef(null);

  const classifyScore = useCallback((score) => {
    if (score >= 8500) return { label: 'DEFINITELY HUMAN', tier: 'human', color: 'var(--signal-human-text)' };
    if (score >= 7000) return { label: 'LIKELY HUMAN', tier: 'human', color: 'var(--signal-human-text)' };
    if (score >= 5500) return { label: 'UNCERTAIN', tier: 'uncertain', color: 'var(--signal-uncertain-text)' };
    if (score >= 3000) return { label: 'LIKELY AGENT', tier: 'agent', color: 'var(--signal-agent-text)' };
    return { label: 'DEFINITELY AGENT', tier: 'agent', color: 'var(--signal-agent-text)' };
  }, []);

  const fetchOracleStats = useCallback(async () => {
    const apiBase = ORACLE_API;
    try {
      const resp = await fetch(`${apiBase}/stats`,         { signal: AbortSignal.timeout(45000) });
      if (resp.ok) {
        const data = await resp.json();
        setOracleStats(data);
        if (data.model_version) setModelVersion(data.model_version);
        if (data.total_fresh_proofs !== undefined) setTotalFreshProofs(data.total_fresh_proofs);
        if (data.total_minted !== undefined) setTotalMinted(data.total_minted);
      }
    } catch {
    }
  }, []);

  const fetchLeaderboard = useCallback(async () => {
    const apiBase = ORACLE_API;
    try {
      const resp = await fetch(`${apiBase}/leaderboard?top_n=20`, { signal: AbortSignal.timeout(45000) });
      if (resp.ok) {
        const data = await resp.json();
        // The deployed API returns a raw array of { wallet, hps, last_updated }.
        // Only entries that represent an actual minted soulbound proof (carry a
        // token_id) belong in the proof leaderboard — ranked-by-score wallets do
        // not. This keeps the "minted proofs" panel honest.
        const list = Array.isArray(data) ? data : (data.leaderboard || []);
        const proofs = list
          .filter((e) => e.token_id !== undefined && e.token_id !== null)
          .map((e) => ({
            wallet: e.wallet,
            wallet_short: e.wallet ? `${e.wallet.slice(0, 6)}...${e.wallet.slice(-4)}` : '',
            token_id: e.token_id,
            score_at_mint: e.score_at_mint ?? e.hps ?? 0,
            current_score: e.current_score ?? e.hps ?? 0,
            is_fresh: e.is_fresh ?? (e.hps ?? 0) >= 7000,
            mint_timestamp: e.mint_timestamp ?? e.last_updated ?? 0,
          }));
        if (proofs.length > 0) setRecentProofs(proofs);
        if (data.total !== undefined) setTotalMinted(data.total);
      }
    } catch {
    }
  }, []);

  const updateScore = useCallback((newScore, label = null) => {
    setGhostScore(prev => {
      setPreviousScore(prev);
      return Number(newScore);
    });

    const now = new Date();
    const entry = {
      time: now.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false }),
      score: Number(newScore),
      label: label || '',
      timestamp: now.getTime(),
    };

    setScoreHistory(prev => {
      const next = [...prev, entry];
      return next.slice(-60);
    });

    setLastUpdateTime(now);
  }, []);

  useEffect(() => {
    if (!ghostAddress || ghostAddress === '0x0000000000000000000000000000000000000000') {
      setConnectionStatus('no-address');
      return;
    }

    let isActive = true;

    const initialize = async () => {
      const rpc = MANTLE_RPC;

      try {
        const provider = new ethers.JsonRpcProvider(rpc);
        providerRef.current = provider;

        await provider.getBlockNumber();

        if (!isActive) return;

        const oracle = new ethers.Contract(
          HPSOracleData.address,
          HPSOracleData.abi,
          provider
        );
        oracleRef.current = oracle;

        const pob = new ethers.Contract(
          POBData.address,
          POBData.abi,
          provider
        );
        pobRef.current = pob;

        const [initialScore, lastUpdated, initialModelVersion, initialTotalMinted] = await Promise.all([
          oracle.getScore(ghostAddress).catch(() => 5000n),
          oracle.lastUpdated(ghostAddress).catch(() => 0n),
          oracle.modelVersion().catch(() => 100n),
          pob.totalMinted().catch(() => 0n),
        ]);

        if (!isActive) return;

        const scoreVal = Number(initialScore);
        setGhostScore(scoreVal);
        setPreviousScore(scoreVal);
        setModelVersion(Number(initialModelVersion));
        setTotalMinted(Number(initialTotalMinted));

        const now = new Date();
        setScoreHistory([{
          time: now.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false }),
          score: scoreVal,
          label: 'Init',
          timestamp: now.getTime(),
        }]);

        if (Number(lastUpdated) > 0) {
          setLastUpdateTime(new Date(Number(lastUpdated) * 1000));
        }

        setConnectionStatus('connected');

        oracle.on('ScoreUpdated', (wallet, oldScore, newScore, timestamp) => {
          if (!isActive) return;
          if (wallet.toLowerCase() === ghostAddress.toLowerCase()) {
            const score = Number(newScore);
            const prev = Number(oldScore);
            const direction = score > prev ? '\u2191' : score < prev ? '\u2193' : '\u2014';
            updateScore(score, direction);
            setLatestEvent({ type: 'ScoreUpdated', wallet, oldScore: prev, newScore: score, timestamp: Number(timestamp) });
          }
        });

        oracle.on('BatchScoresUpdated', (walletCount, timestamp, mv) => {
          if (!isActive) return;
          setModelVersion(Number(mv));
          oracle.getScore(ghostAddress).then(s => {
            if (isActive) updateScore(Number(s), 'Batch');
          }).catch(() => {});
        });

        pob.on('ProofMinted', (wallet, tokenId, score, fingerprint, timestamp) => {
          if (!isActive) return;
          const newProof = {
            wallet: wallet,
            wallet_short: wallet.slice(0, 6) + '...' + wallet.slice(-4),
            token_id: Number(tokenId),
            score_at_mint: Number(score),
            current_score: Number(score),
            is_fresh: true,
            mint_timestamp: Number(timestamp),
            isNew: true,
          };
          setRecentProofs(prev => [newProof, ...prev.slice(0, 19)]);
          setTotalMinted(prev => prev + 1);
          setTotalFreshProofs(prev => prev + 1);
        });

        pob.on('ProofRefreshed', (wallet, tokenId, oldScore, newScore, isFresh, timestamp) => {
          if (!isActive) return;
          setRecentProofs(prev => prev.map(p =>
            p.wallet.toLowerCase() === wallet.toLowerCase()
              ? { ...p, current_score: Number(newScore), is_fresh: isFresh }
              : p
          ));
        });

        pob.on('ProofStaled', (wallet) => {
          if (!isActive) return;
          setRecentProofs(prev => prev.map(p =>
            p.wallet.toLowerCase() === wallet.toLowerCase()
              ? { ...p, is_fresh: false }
              : p
          ));
          setTotalFreshProofs(prev => Math.max(0, prev - 1));
        });

        await Promise.all([fetchOracleStats(), fetchLeaderboard()]);

        const pollInterval = POLL_INTERVAL_MS;
        pollIntervalRef.current = setInterval(async () => {
          if (!isActive) return;
          try {
            const [s, mv] = await Promise.all([
              oracle.getScore(ghostAddress),
              oracle.modelVersion(),
            ]);
            const newScore = Number(s);
            setGhostScore(prev => {
              if (prev !== newScore) {
                setPreviousScore(prev);
                updateScore(newScore, newScore > prev ? '\u2191' : '\u2193');
              }
              return newScore;
            });
            setModelVersion(Number(mv));
            await fetchOracleStats();
          } catch {
          }
        }, pollInterval);

      } catch (err) {
        console.error('Oracle connection failed:', err);
        if (isActive) setConnectionStatus('error');
      }
    };

    initialize();

    return () => {
      isActive = false;
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
      if (oracleRef.current) oracleRef.current.removeAllListeners();
      if (pobRef.current) pobRef.current.removeAllListeners();
    };
  }, [ghostAddress, updateScore, fetchOracleStats, fetchLeaderboard]);

  return {
    ghostScore,
    previousScore,
    scoreHistory,
    latestEvent,
    recentProofs,
    totalFreshProofs,
    totalMinted,
    oracleStats,
    connectionStatus,
    lastUpdateTime,
    modelVersion,
    classifyScore,
  };
}
