import sqlite3
import os
import json
import time
from typing import Optional, Dict, Any, List
from loguru import logger


DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "oracle_service",
    "scores.db",
)


class ScoreCache:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        conn = self._get_conn()
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
        conn.execute(
            "CREATE TABLE IF NOT EXISTS protocol_health ("
            "  protocol_address TEXT NOT NULL,"
            "  protocol_name TEXT NOT NULL,"
            "  wallets_sampled INTEGER NOT NULL,"
            "  human_ratio REAL NOT NULL,"
            "  avg_hps INTEGER NOT NULL,"
            "  median_hps INTEGER NOT NULL,"
            "  hps_p25 INTEGER NOT NULL,"
            "  hps_p75 INTEGER NOT NULL,"
            "  bot_heavy_count INTEGER NOT NULL,"
            "  genuine_human_count INTEGER NOT NULL,"
            "  computed_at INTEGER NOT NULL,"
            "  PRIMARY KEY (protocol_address, computed_at)"
            ")"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_ph_addr_time "
            "  ON protocol_health(protocol_address, computed_at DESC)"
        )
        conn.execute(
            "CREATE TABLE IF NOT EXISTS smart_money_flows ("
            "  protocol_address TEXT NOT NULL,"
            "  protocol_name TEXT NOT NULL,"
            "  period_days INTEGER NOT NULL,"
            "  inflow_mnt REAL NOT NULL,"
            "  outflow_mnt REAL NOT NULL,"
            "  unique_smart_wallets INTEGER NOT NULL,"
            "  net_flow_mnt REAL NOT NULL,"
            "  computed_at INTEGER NOT NULL,"
            "  PRIMARY KEY (protocol_address, period_days, computed_at)"
            ")"
        )
        conn.execute(
            "CREATE TABLE IF NOT EXISTS smart_money_alerts ("
            "  id INTEGER PRIMARY KEY AUTOINCREMENT,"
            "  alert_type TEXT NOT NULL,"
            "  wallet_or_protocol TEXT NOT NULL,"
            "  detail_json TEXT NOT NULL,"
            "  detected_at INTEGER NOT NULL"
            ")"
        )
        conn.execute(
            "CREATE TABLE IF NOT EXISTS emerging_protocols ("
            "  protocol_address TEXT NOT NULL,"
            "  protocol_name TEXT NOT NULL,"
            "  lookback_days INTEGER NOT NULL,"
            "  recent_human_count INTEGER NOT NULL,"
            "  prior_human_count INTEGER NOT NULL,"
            "  human_growth_pct REAL NOT NULL,"
            "  signal TEXT NOT NULL,"
            "  computed_at INTEGER NOT NULL,"
            "  PRIMARY KEY (protocol_address, computed_at)"
            ")"
        )
        conn.execute(
            "CREATE TABLE IF NOT EXISTS sybil_clusters ("
            "  cluster_id TEXT PRIMARY KEY,"
            "  size INTEGER NOT NULL,"
            "  avg_hps INTEGER NOT NULL,"
            "  sybil_probability REAL NOT NULL,"
            "  coordinator TEXT,"
            "  risk_level TEXT NOT NULL,"
            "  members_json TEXT NOT NULL,"
            "  computed_at INTEGER NOT NULL"
            ")"
        )
        conn.execute(
            "CREATE TABLE IF NOT EXISTS previous_smart_wallet_set ("
            "  key TEXT PRIMARY KEY,"
            "  wallets_json TEXT NOT NULL"
            ")"
        )
        conn.commit()
        conn.close()

    def get_cached_score(self, wallet: str, max_age_seconds: int = 3600) -> Optional[Dict[str, Any]]:
        try:
            conn = self._get_conn()
            conn.row_factory = None
            row = conn.execute(
                "SELECT hps, ml_hps, probability, confidence, ml_weight, dim_weight, "
                "dimension_scores, explanation, fingerprint, computed_at, computation_ms "
                "FROM scores WHERE wallet=? AND computed_at > ?",
                (wallet.lower(), int(time.time()) - max_age_seconds),
            ).fetchone()
            conn.close()
            if row:
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
        except Exception as e:
            logger.debug(f"Cache read error: {e}")
        return None

    def cache_score(self, wallet: str, result: Dict[str, Any]):
        try:
            conn = self._get_conn()
            conn.row_factory = None
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

    def get_model_version(self) -> Optional[int]:
        try:
            conn = self._get_conn()
            conn.row_factory = None
            row = conn.execute(
                "SELECT value FROM model_meta WHERE key='model_version'"
            ).fetchone()
            conn.close()
            return int(row[0]) if row else None
        except Exception:
            return None

    def set_model_version(self, version: int):
        try:
            conn = self._get_conn()
            conn.row_factory = None
            conn.execute(
                "INSERT OR REPLACE INTO model_meta VALUES (?, ?)",
                ("model_version", str(version)),
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.debug(f"Model version cache error: {e}")

    def mark_intelligence_cycle_completed(self):
        try:
            conn = self._get_conn()
            conn.row_factory = None
            conn.execute(
                "INSERT OR REPLACE INTO model_meta VALUES (?, ?)",
                ("intelligence_cycle_completed_at", str(int(time.time()))),
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.debug(f"mark_intelligence_cycle_completed error: {e}")

    def get_intelligence_cycle_completed_at(self) -> Optional[int]:
        try:
            conn = self._get_conn()
            conn.row_factory = None
            row = conn.execute(
                "SELECT value FROM model_meta WHERE key='intelligence_cycle_completed_at'"
            ).fetchone()
            conn.close()
            return int(row[0]) if row else None
        except Exception:
            return None

    def clear_expired(self, max_age_seconds: int = 86400):
        try:
            conn = self._get_conn()
            conn.row_factory = None
            cutoff = int(time.time()) - max_age_seconds
            conn.execute("DELETE FROM scores WHERE computed_at < ?", (cutoff,))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.debug(f"Cache cleanup error: {e}")

    def get_wallets_above_threshold(self, threshold: int) -> List[str]:
        try:
            conn = self._get_conn()
            conn.row_factory = None
            rows = conn.execute(
                "SELECT DISTINCT wallet FROM scores WHERE hps >= ? ORDER BY hps DESC",
                (threshold,),
            ).fetchall()
            conn.close()
            return [r[0] for r in rows]
        except Exception as e:
            logger.debug(f"get_wallets_above_threshold error: {e}")
            return []

    def get_top_wallets_by_hps(self, limit: int = 50, min_hps: int = 0) -> List[dict]:
        try:
            conn = self._get_conn()
            conn.row_factory = None
            rows = conn.execute(
                "SELECT wallet, hps, computed_at FROM scores WHERE hps >= ? ORDER BY hps DESC LIMIT ?",
                (min_hps, limit),
            ).fetchall()
            conn.close()
            return [{"address": r[0], "hps": r[1], "last_updated": r[2]} for r in rows]
        except Exception as e:
            logger.debug(f"get_top_wallets_by_hps error: {e}")
            return []

    def get_all_scored_wallets(self, min_hps: int = 0) -> List[str]:
        try:
            conn = self._get_conn()
            conn.row_factory = None
            rows = conn.execute(
                "SELECT wallet FROM scores WHERE hps >= ? ORDER BY computed_at DESC",
                (min_hps,),
            ).fetchall()
            conn.close()
            return [r[0] for r in rows]
        except Exception as e:
            logger.debug(f"get_all_scored_wallets error: {e}")
            return []

    def upsert_protocol_health(self, protocol_address: str, protocol_name: str,
                                wallets_sampled: int, human_ratio: float,
                                avg_hps: int, median_hps: int, hps_p25: int, hps_p75: int,
                                bot_heavy_count: int, genuine_human_count: int,
                                computed_at: int):
        try:
            conn = self._get_conn()
            conn.row_factory = None
            conn.execute(
                "INSERT OR REPLACE INTO protocol_health "
                "(protocol_address, protocol_name, wallets_sampled, human_ratio, "
                "avg_hps, median_hps, hps_p25, hps_p75, bot_heavy_count, "
                "genuine_human_count, computed_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (protocol_address, protocol_name, wallets_sampled, human_ratio,
                 avg_hps, median_hps, hps_p25, hps_p75, bot_heavy_count,
                 genuine_human_count, computed_at),
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.debug(f"upsert_protocol_health error: {e}")

    def get_latest_protocol_health(self, address: Optional[str] = None) -> List[dict]:
        try:
            conn = self._get_conn()
            if address:
                row = conn.execute(
                    "SELECT * FROM protocol_health WHERE protocol_address=? "
                    "ORDER BY computed_at DESC LIMIT 1",
                    (address,),
                ).fetchone()
                conn.close()
                if row:
                    return [dict(row)]
                return []
            rows = conn.execute(
                "SELECT ph.* FROM protocol_health ph "
                "INNER JOIN (SELECT protocol_address, MAX(computed_at) AS max_ts "
                "FROM protocol_health GROUP BY protocol_address) latest "
                "ON ph.protocol_address = latest.protocol_address "
                "AND ph.computed_at = latest.max_ts "
                "ORDER BY ph.human_ratio DESC"
            ).fetchall()
            conn.close()
            return [dict(r) for r in rows]
        except Exception as e:
            logger.debug(f"get_latest_protocol_health error: {e}")
            return []

    def get_protocol_health_history(self, address: str, days: int = 30) -> List[dict]:
        try:
            cutoff = int(time.time()) - days * 86400
            conn = self._get_conn()
            rows = conn.execute(
                "SELECT human_ratio, avg_hps, computed_at FROM protocol_health "
                "WHERE protocol_address=? AND computed_at>=? ORDER BY computed_at ASC",
                (address, cutoff),
            ).fetchall()
            conn.close()
            return [{"human_ratio": r["human_ratio"], "avg_hps": r["avg_hps"],
                      "computed_at": r["computed_at"]} for r in rows]
        except Exception as e:
            logger.debug(f"get_protocol_health_history error: {e}")
            return []

    def compute_trend(self, protocol_address: str, metric: str = "human_ratio",
                      days: int = 7) -> Optional[float]:
        try:
            cutoff = int(time.time()) - days * 86400
            conn = self._get_conn()
            rows = conn.execute(
                f"SELECT {metric}, computed_at FROM protocol_health "
                f"WHERE protocol_address=? AND computed_at>=? ORDER BY computed_at ASC",
                (protocol_address, cutoff),
            ).fetchall()
            conn.close()
            if len(rows) >= 2:
                first = rows[0][metric]
                last = rows[-1][metric]
                return round(last - first, 4)
        except Exception as e:
            logger.debug(f"compute_trend error: {e}")
        return None

    def upsert_smart_money_flow(self, protocol_address: str, protocol_name: str,
                                 period_days: int, inflow_mnt: float, outflow_mnt: float,
                                 unique_smart_wallets: int, net_flow_mnt: float,
                                 computed_at: int):
        try:
            conn = self._get_conn()
            conn.row_factory = None
            conn.execute(
                "INSERT OR REPLACE INTO smart_money_flows "
                "(protocol_address, protocol_name, period_days, inflow_mnt, "
                "outflow_mnt, unique_smart_wallets, net_flow_mnt, computed_at) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (protocol_address, protocol_name, period_days, inflow_mnt,
                 outflow_mnt, unique_smart_wallets, net_flow_mnt, computed_at),
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.debug(f"upsert_smart_money_flow error: {e}")

    def get_latest_smart_money_flows(self, period_days: int = 14) -> List[dict]:
        try:
            cutoff = int(time.time()) - 3600
            conn = self._get_conn()
            rows = conn.execute(
                "SELECT smf.* FROM smart_money_flows smf "
                "INNER JOIN (SELECT protocol_address, period_days, MAX(computed_at) AS max_ts "
                "FROM smart_money_flows WHERE period_days=? AND computed_at>=? "
                "GROUP BY protocol_address, period_days) latest "
                "ON smf.protocol_address = latest.protocol_address "
                "AND smf.period_days = latest.period_days "
                "AND smf.computed_at = latest.max_ts "
                "ORDER BY smf.net_flow_mnt DESC",
                (period_days, cutoff),
            ).fetchall()
            conn.close()
            return [dict(r) for r in rows]
        except Exception as e:
            logger.debug(f"get_latest_smart_money_flows error: {e}")
            return []

    def insert_smart_money_alert(self, alert_type: str, wallet_or_protocol: str,
                                  detail_json: str, detected_at: int):
        try:
            conn = self._get_conn()
            conn.row_factory = None
            conn.execute(
                "INSERT INTO smart_money_alerts (alert_type, wallet_or_protocol, "
                "detail_json, detected_at) VALUES (?,?,?,?)",
                (alert_type, wallet_or_protocol, detail_json, detected_at),
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.debug(f"insert_smart_money_alert error: {e}")

    def get_recent_alerts(self, hours: int = 24) -> List[dict]:
        try:
            cutoff = int(time.time()) - hours * 3600
            conn = self._get_conn()
            rows = conn.execute(
                "SELECT * FROM smart_money_alerts WHERE detected_at>=? ORDER BY detected_at DESC",
                (cutoff,),
            ).fetchall()
            conn.close()
            return [dict(r) for r in rows]
        except Exception as e:
            logger.debug(f"get_recent_alerts error: {e}")
            return []

    def upsert_emerging_protocol(self, protocol_address: str, protocol_name: str,
                                  lookback_days: int, recent_human_count: int,
                                  prior_human_count: int, human_growth_pct: float,
                                  signal: str, computed_at: int):
        try:
            conn = self._get_conn()
            conn.row_factory = None
            conn.execute(
                "INSERT OR REPLACE INTO emerging_protocols "
                "(protocol_address, protocol_name, lookback_days, recent_human_count, "
                "prior_human_count, human_growth_pct, signal, computed_at) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (protocol_address, protocol_name, lookback_days, recent_human_count,
                 prior_human_count, human_growth_pct, signal, computed_at),
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.debug(f"upsert_emerging_protocol error: {e}")

    def get_emerging_protocols(self, days: int = 7) -> List[dict]:
        try:
            cutoff = int(time.time()) - 7200
            conn = self._get_conn()
            rows = conn.execute(
                "SELECT ep.* FROM emerging_protocols ep "
                "INNER JOIN (SELECT protocol_address, MAX(computed_at) AS max_ts "
                "FROM emerging_protocols WHERE lookback_days=? AND computed_at>=? "
                "GROUP BY protocol_address) latest "
                "ON ep.protocol_address = latest.protocol_address "
                "AND ep.computed_at = latest.max_ts "
                "ORDER BY ep.human_growth_pct DESC",
                (days, cutoff),
            ).fetchall()
            conn.close()
            return [dict(r) for r in rows]
        except Exception as e:
            logger.debug(f"get_emerging_protocols error: {e}")
            return []

    def upsert_sybil_cluster(self, cluster_id: str, size: int, avg_hps: int,
                              sybil_probability: float, coordinator: Optional[str],
                              risk_level: str, members_json: str, computed_at: int):
        try:
            conn = self._get_conn()
            conn.row_factory = None
            conn.execute(
                "INSERT OR REPLACE INTO sybil_clusters "
                "(cluster_id, size, avg_hps, sybil_probability, coordinator, "
                "risk_level, members_json, computed_at) VALUES (?,?,?,?,?,?,?,?)",
                (cluster_id, size, avg_hps, sybil_probability, coordinator,
                 risk_level, members_json, computed_at),
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.debug(f"upsert_sybil_cluster error: {e}")

    def get_sybil_clusters(self, min_size: int = 3, risk_level: Optional[str] = None) -> List[dict]:
        try:
            conn = self._get_conn()
            query = "SELECT cluster_id, size, avg_hps, sybil_probability, coordinator, risk_level FROM sybil_clusters WHERE size>=?"
            params = [min_size]
            if risk_level:
                query += " AND risk_level=?"
                params.append(risk_level)
            query += " ORDER BY sybil_probability DESC, size DESC"
            rows = conn.execute(query, params).fetchall()
            conn.close()
            return [dict(r) for r in rows]
        except Exception as e:
            logger.debug(f"get_sybil_clusters error: {e}")
            return []

    def get_sybil_cluster(self, cluster_id: str) -> Optional[dict]:
        try:
            conn = self._get_conn()
            row = conn.execute(
                "SELECT * FROM sybil_clusters WHERE cluster_id=?", (cluster_id,),
            ).fetchone()
            conn.close()
            if row:
                d = dict(row)
                d["members"] = json.loads(d.pop("members_json"))
                return d
        except Exception as e:
            logger.debug(f"get_sybil_cluster error: {e}")
        return None

    def get_wallet_cluster_id(self, wallet: str) -> Optional[str]:
        wallet_lower = wallet.lower()
        clusters = self.get_sybil_clusters(min_size=0)
        for c in clusters:
            detail = self.get_sybil_cluster(c["cluster_id"])
            if detail:
                for m in detail.get("members", []):
                    if m.get("address", "").lower() == wallet_lower:
                        return c["cluster_id"]
        return None

    def get_previous_smart_wallet_set(self) -> set:
        try:
            conn = self._get_conn()
            conn.row_factory = None
            row = conn.execute(
                "SELECT wallets_json FROM previous_smart_wallet_set WHERE key='smart_wallets'"
            ).fetchone()
            conn.close()
            if row and row[0]:
                return set(json.loads(row[0]))
        except Exception:
            pass
        return set()

    def set_previous_smart_wallet_set(self, wallets: List[str]):
        try:
            conn = self._get_conn()
            conn.row_factory = None
            conn.execute(
                "INSERT OR REPLACE INTO previous_smart_wallet_set VALUES (?, ?)",
                ("smart_wallets", json.dumps(list(wallets))),
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.debug(f"set_previous_smart_wallet_set error: {e}")

    def get_all_feature_vectors(self) -> dict:
        wallet_features = {}
        try:
            conn = self._get_conn()
            conn.row_factory = None
            rows = conn.execute(
                "SELECT wallet, dimension_scores, computed_at FROM scores ORDER BY computed_at DESC"
            ).fetchall()
            conn.close()
            for r in rows:
                wallet = r[0]
                dim_scores = json.loads(r[1]) if r[1] else {}
                import numpy as np
                vec = np.zeros(49)
                for i, (k, v) in enumerate(sorted(dim_scores.items())):
                    if i < 49:
                        vec[i] = float(v)
                wallet_features[wallet] = vec
        except Exception as e:
            logger.debug(f"get_all_feature_vectors error: {e}")
        return wallet_features


_score_cache_instance: Optional[ScoreCache] = None


def get_cache() -> ScoreCache:
    global _score_cache_instance
    if _score_cache_instance is None:
        _score_cache_instance = ScoreCache()
    return _score_cache_instance
