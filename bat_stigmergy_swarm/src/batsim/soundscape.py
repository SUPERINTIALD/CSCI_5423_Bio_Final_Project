import numpy as np


class Soundscape:
    """
    Two-channel stigmergy field:
      buzz[y,x]  : "prey found / feeding buzz"
      alarm[y,x] : "danger nearby / alarm"
    """
    def __init__(self, h: int, w: int, decay: float, diffuse: float):
        self.h = h
        self.w = w
        self.decay = decay
        self.diffuse = diffuse
        self.buzz = np.zeros((h, w), dtype=np.float32)
        self.alarm = np.zeros((h, w), dtype=np.float32)

    def deposit_buzz(self, x: int, y: int, amount: float):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.buzz[y, x] += amount

    def deposit_alarm(self, x: int, y: int, amount: float):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.alarm[y, x] += amount

    def step(self):
        # decay
        self.buzz *= self.decay
        self.alarm *= self.decay

        # diffuse (very simple neighbor mixing, stable enough for MVP)
        if self.diffuse <= 0:
            return

        for field in (self.buzz, self.alarm):
            up = np.roll(field, -1, axis=0)
            down = np.roll(field, 1, axis=0)
            left = np.roll(field, -1, axis=1)
            right = np.roll(field, 1, axis=1)
            neighbor_avg = (up + down + left + right) / 4.0
            field[:] = (1 - self.diffuse) * field + self.diffuse * neighbor_avg