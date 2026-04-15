import random
import numpy as np
from .soundscape import Soundscape
from .config import SimConfig

DIRS = [
    (0, 0),
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

        # 1 = obstacle, 0 = free
        self.obstacles = np.ones((self.h, self.w), dtype=np.uint8)

        # Start of the outside/emergence zone
        self.outside_x0 = self.w - 90
        self.exit_x0 = self.outside_x0

        self._spawn_cave()
        self._add_rock_blobs(n_blobs=10, r_min=1, r_max=3)

        # Task 1: KEEP OUTSIDE FULLY OPEN
        # Task 2: add clutter only farther outside
        if self.cfg.task == 1:
            self.obstacles[:, self.outside_x0:] = 0
        else:
            self._add_outside_clutter(
                n_patches=30,
                patch_r_min=2,
                patch_r_max=4,
                clutter_start_x=self.outside_x0 + 30,
            )

        self.outside_field = self._build_outside_field()

        self.prey = set()
        self._spawn_prey()
        self.predator_pos = (min(self.w - 10, self.outside_x0 + 40), self.h // 2)

        self.sound = Soundscape(self.h, self.w, decay=cfg.decay, diffuse=cfg.diffuse)

    def _spawn_cave(self):
        center_y = self.h // 2
        corridor_half = max(3, self.h // 10)

        for x in range(self.w):
            if x < self.outside_x0:
                center_y += self.rng.choice([-1, 0, 1])
                center_y = max(corridor_half + 2, min(self.h - corridor_half - 3, center_y))

                widen = x / max(1, self.outside_x0)
                local_half = int(corridor_half + 5 * widen)

                y0 = max(1, center_y - local_half)
                y1 = min(self.h - 2, center_y + local_half)
                self.obstacles[y0:y1 + 1, x] = 0
            else:
                # outside open by default
                self.obstacles[:, x] = 0

    def _add_rock_blobs(self, n_blobs=10, r_min=1, r_max=3):
        placed = 0
        tries = 0
        max_tries = n_blobs * 30

        while placed < n_blobs and tries < max_tries:
            tries += 1

            cx = self.rng.randint(10, max(12, self.outside_x0 - 12))
            cy = self.rng.randint(5, self.h - 6)
            rad = self.rng.randint(r_min, r_max)

            if self.obstacles[cy, cx] == 1:
                continue

            for y in range(max(0, cy - rad), min(self.h, cy + rad + 1)):
                for x in range(max(0, cx - rad), min(self.w, cx + rad + 1)):
                    if (x - cx) ** 2 + (y - cy) ** 2 <= rad * rad:
                        self.obstacles[y, x] = 1

            placed += 1

    def _add_outside_clutter(self, n_patches=30, patch_r_min=2, patch_r_max=4, clutter_start_x=None):
        if clutter_start_x is None:
            clutter_start_x = self.outside_x0 + 30

        x_min = min(max(clutter_start_x, self.outside_x0 + 1), self.w - 10)
        x_max = self.w - 8
        if x_min >= x_max:
            return

        for _ in range(n_patches):
            cx = self.rng.randint(x_min, x_max)
            cy = self.rng.randint(4, self.h - 5)
            rad = self.rng.randint(patch_r_min, patch_r_max)

            for y in range(max(0, cy - rad), min(self.h, cy + rad + 1)):
                for x in range(max(0, cx - rad), min(self.w, cx + rad + 1)):
                    if (x - cx) ** 2 + (y - cy) ** 2 <= rad * rad:
                        self.obstacles[y, x] = 1

    def _build_outside_field(self):
        field = np.zeros((self.h, self.w), dtype=np.float32)
        for y in range(self.h):
            for x in range(self.w):
                if x >= self.outside_x0:
                    field[y, x] = (x - self.outside_x0) / max(1, (self.w - self.outside_x0))
        return field

    def _spawn_prey(self):
        self.prey.clear()
        if self.cfg.task != 2:
            return

        tries = 0
        max_tries = self.cfg.n_prey * 50
        prey_x0 = min(self.w - 5, self.outside_x0 + 25)

        while len(self.prey) < self.cfg.n_prey and tries < max_tries:
            tries += 1
            x = self.rng.randrange(prey_x0, self.w - 3)
            y = self.rng.randrange(2, self.h - 2)

            if self.obstacles[y, x] == 0:
                self.prey.add((x, y))

    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.w and 0 <= y < self.h

    def is_free(self, x: int, y: int) -> bool:
        return self.in_bounds(x, y) and self.obstacles[y, x] == 0

    def is_exit(self, x: int) -> bool:
        return x >= self.outside_x0

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