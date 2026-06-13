from __future__ import annotations

import asyncio
import time
from collections import defaultdict

from loguru import logger

from oracle_service.config import OracleConfig
from oracle_service.score_cache import ScoreCache
from data_pipeline.mantle_fetcher import MantleDataFetcher
from scorers.interrogator import Interrogator


class IntelligenceAggregator:
    def __init__(self, cache: ScoreCache, fetcher: MantleDataFetcher, scorer: Interrogator):
        self.cache = cache
        self.fetcher = fetcher
        self.scorer = scorer
        self.config = OracleConfig()
        self._log = logger.bind(component="intelligence_aggregator")

    async def run_forever(self) -> None:
        asyncio.create_task(self._loop(self.recompute_protocol_health, self.config.intelligence_cycle_seconds))
        asyncio.create_task(self._loop(self.recompute_emerging, self.config.intelligence_cycle_seconds))
        asyncio.create_task(self._loop(self.recompute_smart_money, self.config.smart_money_cycle_seconds))

    async def _loop(self, fn, interval: int) -> None:
        await asyncio.sleep(30)
        while True:
            try:
                await fn()
            except Exception:
                self._log.exception(f"{fn.__name__} cycle failed")
            await asyncio.sleep(interval)

    async def recompute_protocol_health(self) -> None:
        sem = asyncio.Semaphore(10)
        for name, address in self.config.mantle_protocols.items():
            wallets = await self.fetcher.fetch_protocol_interactors(address, days=30)
            scores: list[int] = []

            async def _score(addr: str):
                async with sem:
                    try:
                        cached = self.cache.get_cached_score(addr)
                        if cached:
                            scores.append(cached["hps"])
                        else:
                            r = await asyncio.to_thread(self.scorer.score, addr, use_cache=True)
                            if r and "hps" in r:
                                scores.append(r["hps"])
                    except Exception as e:
                        self._log.debug(f"score failed for {addr}: {e}")

            if wallets:
                await asyncio.gather(*(_score(w) for w in wallets[:self.config.protocol_sample_cap]))

            if not scores:
                self._log.warning(f"no scorable wallets for {name} ({address})")
                continue

            scores_sorted = sorted(scores)
            n = len(scores_sorted)
            self.cache.upsert_protocol_health(
                protocol_address=address, protocol_name=name,
                wallets_sampled=n,
                human_ratio=round(sum(1 for s in scores if s >= self.config.human_hps_threshold) / n, 4),
                avg_hps=round(sum(scores) / n),
                median_hps=scores_sorted[n // 2],
                hps_p25=scores_sorted[n // 4],
                hps_p75=scores_sorted[3 * n // 4],
                bot_heavy_count=sum(1 for s in scores if s < self.config.bot_heavy_hps_threshold),
                genuine_human_count=sum(1 for s in scores if s >= self.config.human_hps_threshold),
                computed_at=int(time.time()),
            )
            latest = self.cache.get_latest_protocol_health(address)
            if latest:
                self._log.info(f"PHS[{name}] = {latest[0]['human_ratio']}")

    async def recompute_emerging(self) -> None:
        for days in (7,):
            recent = await self._aggregate_protocol_human_wallets(0, days)
            prior = await self._aggregate_protocol_human_wallets(days, days * 2)
            for address, recent_count in recent.items():
                prior_count = prior.get(address, 0)
                if prior_count < self.config.emerging_min_prior_humans:
                    continue
                growth = (recent_count - prior_count) / max(prior_count, 1)
                if growth > self.config.emerging_growth_threshold:
                    name = next((n for n, a in self.config.mantle_protocols.items() if a == address), address)
                    self.cache.upsert_emerging_protocol(
                        protocol_address=address, protocol_name=name, lookback_days=days,
                        recent_human_count=recent_count, prior_human_count=prior_count,
                        human_growth_pct=round(growth * 100, 1),
                        signal="organic_traction" if growth > 1.0 else "accelerating",
                        computed_at=int(time.time()),
                    )

    async def _aggregate_protocol_human_wallets(self, start_days_ago: int, end_days_ago: int) -> dict[str, int]:
        result: dict[str, int] = {}
        for name, address in self.config.mantle_protocols.items():
            wallets = await self.fetcher.fetch_protocol_interactors(
                address, days=end_days_ago if end_days_ago > 0 else 1,
            )
            count = 0
            for addr in wallets[:self.config.protocol_sample_cap]:
                cached = self.cache.get_cached_score(addr)
                if cached and cached["hps"] >= self.config.human_hps_threshold:
                    count += 1
            result[address] = count
        return result

    async def recompute_smart_money(self) -> None:
        smart_wallets = self.cache.get_wallets_above_threshold(self.config.smart_money_hps_threshold)
        days = 14
        protocol_flows: dict[str, dict] = defaultdict(lambda: {"inflow": 0.0, "outflow": 0.0, "wallets": set()})

        sem = asyncio.Semaphore(8)

        async def _process(wallet: str):
            async with sem:
                try:
                    txs = await self.fetcher.fetch_recent_transactions(wallet, days=days)
                    for tx in txs:
                        protocol_addr = self._identify_protocol(tx.get("to", ""))
                        if not protocol_addr:
                            continue
                        value_mnt = float(tx.get("value", 0)) / 1e18
                        if tx.get("from", "").lower() == wallet.lower():
                            protocol_flows[protocol_addr]["outflow"] += value_mnt
                            protocol_flows[protocol_addr]["inflow"] += value_mnt
                        protocol_flows[protocol_addr]["wallets"].add(wallet)
                except Exception as e:
                    self._log.debug(f"smart money process failed for {wallet}: {e}")

        await asyncio.gather(*(_process(w) for w in smart_wallets))

        for address, data in protocol_flows.items():
            name = next((n for n, a in self.config.mantle_protocols.items() if a == address), address)
            self.cache.upsert_smart_money_flow(
                protocol_address=address, protocol_name=name, period_days=days,
                inflow_mnt=round(data["inflow"], 4), outflow_mnt=round(data["outflow"], 4),
                unique_smart_wallets=len(data["wallets"]),
                net_flow_mnt=round(data["inflow"] - data["outflow"], 4),
                computed_at=int(time.time()),
            )

        previous = self.cache.get_previous_smart_wallet_set()
        new_entrants = set(smart_wallets) - previous
        for w in new_entrants:
            self.cache.insert_smart_money_alert(
                alert_type="new_smart_wallet", wallet_or_protocol=w,
                detail_json='{"hps_threshold": %d}' % self.config.smart_money_hps_threshold,
                detected_at=int(time.time()),
            )
        self.cache.set_previous_smart_wallet_set(smart_wallets)

    def _identify_protocol(self, to_address: str) -> str | None:
        to_lower = (to_address or "").lower()
        for address in self.config.mantle_protocols.values():
            if address.lower() == to_lower:
                return address
        return None
