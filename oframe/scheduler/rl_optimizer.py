import random

class TimedBandit:
    def __init__(self):
        self.alpha = [1] * 24
        self.beta = [1] * 24

    def select_hour(self) -> int:
        samples = [random.betavariate(self.alpha[h], self.beta[h]) for h in range(24)]
        return samples.index(max(samples))

    def update(self, hour: int, success: bool):
        if success:
            self.alpha[hour] += 1
        else:
            self.beta[hour] += 1
