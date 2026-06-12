import sqlite3
import os
import json
import time
from pathlib import Path
from typing import Optional, Dict, Any
from loguru import logger


DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "oracle_service",
    "scores.db",
)


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.execute(
        "CREATE TABLE IF NOT EXISTS scores ("
        "  wallet TEXT PRIMARY KEY,"
        "  hps INTEGER,"
        "  ml_hps INTEGER,"
        "  probability REAL,"
        "  confidence TEXT,"
        "  ml_weight REAL,"
        "  dim_weight REAL,"
        "  dimension_scores TEXT,"
        "  explanation TEXT,"
        "  fingerprint TEXT,"
        "  computed_at INTEGER,"
        "  computation_ms INTEGER"
        ")"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS model_meta ("
        "  key TEXT PRIMARY KEY,"
        "  value TEXT"
        ")"
    )
    conn.commit()
    return conn


def _row_to_result(row) -> Dict[str, Any]:
    result = {
        "hps": row[0],
        "ml_hps": row[1],
        "probability": row[2],
        "confidence": row[3],
        "ml_weight": row[4],
        "dim_weight": row[5],
        "dimension_scores": json.loads(row[6]) if row[6] else {},
        "computed_at": row[9],
        "computation_ms": row[10],
        "cached": True,
    }
    explanation_json = row[7]
    if explanation_json and explanation_json != "null":
        result["explanation"] = json.loads(explanation_json)
    if row[8]:
        result["fingerprint"] = row[8]
    return result


def get_cached_score(wallet: str, max_age_seconds: int = 3600) -> Optional[Dict[str, Any]]:
    try:
        conn = _get_conn()
        row = conn.execute(
            "SELECT hps, ml_hps, probability, confidence, ml_weight, dim_weight, "
            "dimension_scores, explanation, fingerprint, computed_at, computation_ms "
            "FROM scores WHERE wallet=? AND computed_at > ?",
            (wallet.lower(), int(time.time()) - max_age_seconds),
        ).fetchone()
        conn.close()
        if row:
            return _row_to_result(row)
    except Exception as e:
        logger.debug(f"Cache read error: {e}")
    return None


def get_cached_explanation(wallet: str) -> Optional[list]:
    try:
        conn = _get_conn()
        row = conn.execute(
            "SELECT explanation FROM scores WHERE wallet=?",
            (wallet.lower(),),
        ).fetchone()
        conn.close()
        if row and row[0] and row[0] != "null":
            return json.loads(row[0])
    except Exception:
        pass
    return None


def cache_score(wallet: str, result: Dict[str, Any]):
    try:
        conn = _get_conn()
        conn.execute(
            "INSERT OR REPLACE INTO scores VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                wallet.lower(),
                result.get("hps", 0),
                result.get("ml_hps", 5000),
                result.get("probability", 0.5),
                result.get("confidence", "low"),
                result.get("ml_weight", 0.5),
                result.get("dim_weight", 0.5),
                json.dumps(result.get("dimension_scores", {})),
                json.dumps(result.get("explanation")) if result.get("explanation") else None,
                result.get("fingerprint"),
                result.get("computed_at", int(time.time())),
                result.get("computation_ms", 0),
            ),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        logger.debug(f"Cache write error: {e}")


def get_model_version() -> Optional[int]:
    try:
        conn = _get_conn()
        row = conn.execute(
            "SELECT value FROM model_meta WHERE key='model_version'"
        ).fetchone()
        conn.close()
        return int(row[0]) if row else None
    except Exception:
        return None


def set_model_version(version: int):
    try:
        conn = _get_conn()
        conn.execute(
            "INSERT OR REPLACE INTO model_meta VALUES (?, ?)",
            ("model_version", str(version)),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        logger.debug(f"Model version cache error: {e}")


def clear_expired(max_age_seconds: int = 86400):
    try:
        conn = _get_conn()
        cutoff = int(time.time()) - max_age_seconds
        conn.execute("DELETE FROM scores WHERE computed_at < ?", (cutoff,))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.debug(f"Cache cleanup error: {e}")
