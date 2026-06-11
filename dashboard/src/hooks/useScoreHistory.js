import { useState, useEffect, useCallback } from 'react';

const DB_NAME = 'TuringProtocolDB';
const STORE_NAME = 'scoreHistory';
const DB_VERSION = 1;
const MAX_STORED_POINTS = 500;

function openDB() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);
    request.onupgradeneeded = (event) => {
      const db = event.target.result;
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        db.createObjectStore(STORE_NAME, { keyPath: 'id' });
      }
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

async function loadHistory(ghostAddress) {
  try {
    const db = await openDB();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE_NAME, 'readonly');
      const store = tx.objectStore(STORE_NAME);
      const request = store.get(ghostAddress);
      request.onsuccess = () => {
        const cutoff = Date.now() - 30 * 24 * 60 * 60 * 1000;
        const data = request.result?.data || [];
        const recent = data.filter(p => p.timestamp > cutoff);
        resolve(recent);
      };
      request.onerror = () => reject(request.error);
      db.close();
    });
  } catch {
    return [];
  }
}

async function saveHistory(ghostAddress, history) {
  try {
    const db = await openDB();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE_NAME, 'readwrite');
      const store = tx.objectStore(STORE_NAME);
      const toStore = history.slice(-MAX_STORED_POINTS);
      store.put({ id: ghostAddress, data: toStore });
      tx.oncomplete = () => resolve();
      tx.onerror = () => reject(tx.error);
      db.close();
    });
  } catch {
  }
}

async function clearHistoryDB(ghostAddress) {
  try {
    const db = await openDB();
    const tx = db.transaction(STORE_NAME, 'readwrite');
    tx.objectStore(STORE_NAME).delete(ghostAddress);
    db.close();
  } catch {
  }
}

export function useScoreHistory(ghostAddress) {
  const [history, setHistory] = useState([]);

  useEffect(() => {
    if (!ghostAddress) return;
    let mounted = true;
    loadHistory(ghostAddress).then(data => {
      if (mounted) setHistory(data);
    });
    return () => { mounted = false; };
  }, [ghostAddress]);

  useEffect(() => {
    if (!ghostAddress || history.length === 0) return;
    saveHistory(ghostAddress, history);
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
      clearHistoryDB(ghostAddress);
    }
  }, [ghostAddress]);

  return { history, addPoint, clearHistory };
}
