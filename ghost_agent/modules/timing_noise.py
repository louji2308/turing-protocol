import numpy as np
from scipy import stats
import time
import asyncio
from dataclasses import dataclass
from typing import Optional


@dataclass
class AttentivenessState:
    is_focused: bool
    state_duration_seconds: float
    state_entered_at: float


class TimingNoiseModule:

    FOCUSED_MU = 1.1
    FOCUSED_SIGMA = 0.45
    FOCUSED_MAX = 30

    DISTRACTED_MU = 3.2
    DISTRACTED_SIGMA = 0.9
    DISTRACTED_MAX = 300

    P_FOCUS_TO_DISTRACT = 0.12
    P_DISTRACT_TO_FOCUS = 0.30

    def __init__(self, seed: Optional[int] = None):
        self.rng = np.random.default_rng(seed)
        self._state = AttentivenessState(
            is_focused=True,
            state_duration_seconds=0,
            state_entered_at=time.time()
        )
        self._reaction_history = []

    def get_delay(self) -> float:
        self._maybe_transition_state()
        if self._state.is_focused:
            delay = self._sample_lognormal(
                self.FOCUSED_MU, self.FOCUSED_SIGMA, max_val=self.FOCUSED_MAX
            )
        else:
            delay = self._sample_lognormal(
                self.DISTRACTED_MU, self.DISTRACTED_SIGMA, max_val=self.DISTRACTED_MAX
            )
        self._reaction_history.append({
            "delay": delay,
            "state": "focused" if self._state.is_focused else "distracted",
            "timestamp": time.time()
        })
        return delay

    async def wait(self) -> float:
        delay = self.get_delay()
        await asyncio.sleep(delay)
        return delay

    def _sample_lognormal(self, mu: float, sigma: float, max_val: float) -> float:
        sample = self.rng.lognormal(mean=mu, sigma=sigma)
        return float(min(sample, max_val))

    def _maybe_transition_state(self):
        if self._state.is_focused:
            if self.rng.random() < self.P_FOCUS_TO_DISTRACT:
                self._state.is_focused = False
                self._state.state_entered_at = time.time()
        else:
            if self.rng.random() < self.P_DISTRACT_TO_FOCUS:
                self._state.is_focused = True
                self._state.state_entered_at = time.time()

    def get_current_state(self) -> str:
        return "focused" if self._state.is_focused else "distracted"

    def get_stats(self) -> dict:
        if not self._reaction_history:
            return {"count": 0}
        delays = [r["delay"] for r in self._reaction_history]
        return {
            "count": len(delays),
            "mean_delay": float(np.mean(delays)),
            "std_delay": float(np.std(delays)),
            "cv": float(np.std(delays) / (np.mean(delays) + 1e-9)),
            "current_state": self.get_current_state(),
            "pct_fast": float(sum(1 for d in delays if d < 5) / len(delays)),
        }
