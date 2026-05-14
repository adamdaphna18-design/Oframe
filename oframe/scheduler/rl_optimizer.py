import random
import math

class TimedBandit:
    def __init__(self):
        self.alpha = [1] * 24  # successes per hour
        self.beta = [1] * 24   # failures per hour

    def select_hour(self):
        samples = [random.betavariate(self.alpha[h], self.beta[h]) for h in range(24)]
        return samples.index(max(samples))

    def update(self, hour, success):
        if success:
            self.alpha[hour] += 1
        else:
            self.beta[hour] += 1
