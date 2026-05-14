# oframe/scheduler/rl_optimizer.py
import random

class TimedBandit:
    """Thompson sampling over 24 hourly bins."""
    def __init__(self):
        self.alpha = [1] * 24  # successes per hour
        self.beta = [1] * 24   # failures per hour

    def select_hour(self) -> int:
        samples = [random.betavariate(self.alpha[h], self.beta[h]) for h in range(24)]
        return samples.index(max(samples))

    def update(self, hour: int, success: bool):
        if success:
            self.alpha[hour] += 1
        else:
            self.beta[hour] += 1
