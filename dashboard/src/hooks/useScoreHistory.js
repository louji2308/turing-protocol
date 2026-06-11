import { useState, useEffect, useCallback } from 'react';

const STORAGE_KEY = 'turing_score_history_v1';
const MAX_STORED_POINTS = 500;

export function useScoreHistory(ghostAddress) {
  const [history, setHistory] = useState([]);

  useEffect(() => {
    if (!ghostAddress) return;
    try {
      const stored = localStorage.getItem(`${STORAGE_KEY}_${ghostAddress}`);
      if (stored) {
        const parsed = JSON.parse(stored);
        if (Array.isArray(parsed)) {
          const cutoff = Date.now() - 24 * 60 * 60 * 1000;
          const recent = parsed.filter(p => p.timestamp > cutoff);
          setHistory(recent);
        }
      }
    } catch {
    }
  }, [ghostAddress]);

  useEffect(() => {
    if (!ghostAddress || history.length === 0) return;
    try {
      const toStore = history.slice(-MAX_STORED_POINTS);
      localStorage.setItem(
        `${STORAGE_KEY}_${ghostAddress}`,
        JSON.stringify(toStore)
      );
    } catch {
    }
  }, [history, ghostAddress]);

  const addPoint = useCallback((score, label = '') => {
    const point = {
      time: new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false }),
      score: Number(score),
      label,
      timestamp: Date.now(),
    };
    setHistory(prev => [...prev.slice(-MAX_STORED_POINTS + 1), point]);
  }, []);

  const clearHistory = useCallback(() => {
    setHistory([]);
    if (ghostAddress) {
      localStorage.removeItem(`${STORAGE_KEY}_${ghostAddress}`);
    }
  }, [ghostAddress]);

  return { history, addPoint, clearHistory };
}
