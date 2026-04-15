import random
import numpy as np
from .soundscape import Soundscape
from .config import SimConfig


DIRS = [
    (0, 0),   # STAY
    (1, 0), (-1, 0), (0, 1), (0, -1),
    (1, 1), (1, -1), (-1, 1), (-1, -1),
]


class World:
    def __init__(self, cfg: SimConfig, seed: int = 0):
        self.cfg = cfg
        self.rng = random.Random(seed)
        self.step_count = 0

        self.w = cfg.grid_w
        self.h = cfg.grid_h

        # 0 free, 1 obstacle
        self.obstacles = np.zeros((self.h, self.w), dtype=np.uint8)
        self._spawn_obstacles()

        # Exit region is on right side (Task 1)
        self.exit_x0 = self.w - cfg.exit_width

        # Task 2: prey positions + predator position
        self.prey = set()
        self._spawn_prey()
        self.predator_pos = (self.w // 3, self.h // 2)  # simple fixed predator for MVP

        self.sound = Soundscape(self.h, self.w, decay=cfg.decay, diffuse=cfg.diffuse)

    def _spawn_obstacles(self):
        # Keep exit corridor clear-ish
        for y in range(self.h):
            for x in range(self.w):
                if x >= self.w - self.cfg.exit_width:
                    continue
                if self.rng.random() < self.cfg.obstacle_density:
                    self.obstacles[y, x] = 1

    def _spawn_prey(self):
        self.prey.clear()
        if self.cfg.task != 2:
            return
        tries = 0
        while len(self.prey) < self.cfg.n_prey and tries < self.cfg.n_prey * 20:
            tries += 1
            x = self.rng.randrange(0, self.w)
            y = self.rng.randrange(0, self.h)
            if self.obstacles[y, x] == 0 and x < self.exit_x0:
                self.prey.add((x, y))

    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.w and 0 <= y < self.h

    def is_free(self, x: int, y: int) -> bool:
        return self.in_bounds(x, y) and self.obstacles[y, x] == 0

    def is_exit(self, x: int) -> bool:
        return x >= self.exit_x0

    def predator_risk(self, x: int, y: int) -> float:
        if self.cfg.task != 2:
            return 0.0
        px, py = self.predator_pos
        dx = x - px
        dy = y - py
        d2 = dx * dx + dy * dy
        return 1.0 if d2 <= (self.cfg.predator_radius ** 2) else 0.0

    def step(self):
        self.step_count += 1
        self.sound.step()