import numpy as np
import time
from typing import Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class NewsEvent:
    id: str
    severity: float
    timestamp: float
    processed: bool = False


class NewsReactionModule:

    NEWS_MU = np.log(900)
    NEWS_SIGMA = 0.8
    NEWS_MAX_SECONDS = 21600

    NEWS_GENERATION_PROB = 0.15

    BURST_INTENSITY_LAMBDA = 3.0

    def __init__(self, seed: Optional[int] = None):
        self.rng = np.random.default_rng(seed)
        self._pending_events: list = []
        self._active_bursts: int = 0
        self._last_news_time = 0
        self._news_history = []

    def check_for_news(self) -> Optional[Dict[str, Any]]:
        current_time = time.time()

        if self.rng.random() < self.NEWS_GENERATION_PROB:
            severity = self.rng.beta(2, 5)
            event = NewsEvent(
                id=f"news_{int(current_time)}",
                severity=severity,
                timestamp=current_time,
            )
            self._pending_events.append(event)

        for event in self._pending_events:
            if event.processed:
                continue

            delay = self.rng.lognormal(mean=self.NEWS_MU, sigma=self.NEWS_SIGMA)
            delay = min(delay, self.NEWS_MAX_SECONDS)

            if current_time - event.timestamp >= delay:
                event.processed = True
                self._last_news_time = current_time
                self._news_history.append({
                    "id": event.id,
                    "severity": event.severity,
                    "delay_applied": delay,
                    "processed_at": current_time,
                })

                self._pending_events = [e for e in self._pending_events if not e.processed][-5:]

                burst_size = max(1, int(self.rng.poisson(
                    self.BURST_INTENSITY_LAMBDA * (0.5 + event.severity * 0.5)
                )))

                return {
                    "type": "news_reaction",
                    "event_id": event.id,
                    "severity": event.severity,
                    "burst_size": burst_size,
                    "reaction_delay": delay,
                }

        return None

    def get_stats(self) -> dict:
        if not self._news_history:
            return {"total_events": 0}
        delays = [e["delay_applied"] for e in self._news_history]
        return {
            "total_events": len(self._news_history),
            "mean_reaction_delay": float(np.mean(delays)) if delays else 0,
            "std_reaction_delay": float(np.std(delays)) if delays else 0,
            "pending_events": len(self._pending_events),
        }
