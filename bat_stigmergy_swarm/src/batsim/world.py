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

        # shared fields
        self.outside_x0 = self.w - 90
        self.exit_x0 = self.outside_x0

        # task-specific world generation
        if self.cfg.task == 1:
            self._spawn_task1_cave()
        else:
            self._spawn_task2_open_world()

        self.outside_field = self._build_outside_field()

        # dynamic entities
        self.prey = set()
        self._spawn_prey()

        # self.predator_pos = (min(self.w - 12, self.outside_x0 + 35), self.h // 2)
        # self.predator_heading = (-1, 0)
        self.predators = []
        for i in range(self.cfg.n_predators):
            px = min(self.w - 12, self.outside_x0 + 35 + i * 12)
            py = self.h // 2 + (i % 3) * 6
            self.predators.append({"pos": (px, py), "heading": (-1, 0)})

        self.sound = Soundscape(self.h, self.w, decay=cfg.decay, diffuse=cfg.diffuse)






    
    def wrap_xy(self, x: int, y: int):
        if self.cfg.task == 2:
            return x % self.w, y % self.h
        return x, y

    def in_bounds(self, x: int, y: int) -> bool:
        if self.cfg.task == 2:
            return True
        return 0 <= x < self.w and 0 <= y < self.h

    def is_free(self, x: int, y: int) -> bool:
        if self.cfg.task == 2:
            x, y = self.wrap_xy(x, y)
            return self.obstacles[y, x] == 0
        return self.in_bounds(x, y) and self.obstacles[y, x] == 0

    # -------------------------
    # TASK 1 WORLD
    # -------------------------
    def _spawn_task1_cave(self):
        """
        Cave on the left, long open outside on the right.
        """
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
                self.obstacles[:, x] = 0

        self._add_rock_blobs(n_blobs=20, r_min=1, r_max=3)

        # fully open outside region for task 1
        self.obstacles[:, self.outside_x0:] = 0

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

    # -------------------------
    # TASK 2 WORLD
    # -------------------------
    def _spawn_task2_open_world(self):
        """
        Open outside world with scattered clutter.
        No cave corridor.
        """
        self.outside_x0 = 0
        self.exit_x0 = 0

        # start fully open
        self.obstacles[:, :] = 0

        # add sparse tree-like clutter
        self._add_open_world_clutter(n_patches=30, patch_r_min=2, patch_r_max=4)

    def _add_open_world_clutter(self, n_patches=45, patch_r_min=2, patch_r_max=4):
        for _ in range(n_patches):
            cx = self.rng.randint(8, self.w - 8)
            cy = self.rng.randint(4, self.h - 5)
            rad = self.rng.randint(patch_r_min, patch_r_max)

            for y in range(max(0, cy - rad), min(self.h, cy + rad + 1)):
                for x in range(max(0, cx - rad), min(self.w, cx + rad + 1)):
                    if (x - cx) ** 2 + (y - cy) ** 2 <= rad * rad:
                        self.obstacles[y, x] = 1

    # -------------------------
    # SHARED HELPERS
    # -------------------------
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

        # 3 clustered insect swarms
        n_clusters = 3
        cluster_centers = []

        tries = 0
        while len(cluster_centers) < n_clusters and tries < 500:
            tries += 1
            cx = self.rng.randint(20, self.w - 20)
            cy = self.rng.randint(15, self.h - 15)
            if self.is_free(cx, cy):
                cluster_centers.append((cx, cy))

        for cx, cy in cluster_centers:
            spawned = 0
            inner_tries = 0
            target = max(8, self.cfg.n_prey // n_clusters)

            while spawned < target and inner_tries < target * 30:
                inner_tries += 1
                x = int(round(self.rng.gauss(cx, 6)))
                y = int(round(self.rng.gauss(cy, 4)))
                if self.is_free(x, y):
                    self.prey.add((x, y))
                    spawned += 1

    def _move_prey(self):
        if self.cfg.task != 2 or not self.prey:
            return

        new_prey = set()
        for (x, y) in self.prey:
            if self.rng.random() < 0.25:
                dx, dy = self.rng.choice(DIRS)
                nx, ny = self.wrap_xy(x + dx, y + dy)
                if self.is_free(nx, ny):
                    new_prey.add((nx, ny))
                else:
                    new_prey.add((x, y))
            else:
                new_prey.add((x, y))
        self.prey = new_prey

    # def _move_predator(self):
    #     if self.cfg.task != 2:
    #         return

    #     # move predator 3 substeps per world step
    #     # if self.step_count % 2 != 0:
    #     #     return
        
    #     for _ in range(1):
    #         px, py = self.predator_pos
    #         target = None

    #         if hasattr(self, "bats"):
    #             active = [b for b in self.bats if getattr(b, "alive", True) and not getattr(b, "done", False)]
    #             if active:
    #                 def torus_dist(b):
    #                     dx = abs(b.x - px)
    #                     dy = abs(b.y - py)
    #                     dx = min(dx, self.w - dx)
    #                     dy = min(dy, self.h - dy)
    #                     return dx + dy

    #                 nearest = min(active, key=torus_dist)
    #                 if torus_dist(nearest) <= 30:
    #                     target = nearest

    #         if target is not None:
    #             # chase using wrap-aware shortest direction
    #             dx_raw = target.x - px
    #             dy_raw = target.y - py

    #             if abs(dx_raw) > self.w / 2:
    #                 dx_raw = -1 if dx_raw > 0 else 1
    #             else:
    #                 dx_raw = 0 if dx_raw == 0 else (1 if dx_raw > 0 else -1)

    #             if abs(dy_raw) > self.h / 2:
    #                 dy_raw = -1 if dy_raw > 0 else 1
    #             else:
    #                 dy_raw = 0 if dy_raw == 0 else (1 if dy_raw > 0 else -1)

    #             candidates = [(dx_raw, dy_raw), (dx_raw, 0), (0, dy_raw)] + DIRS
    #         else:
    #             candidates = [self.predator_heading] + DIRS

    #         best = None
    #         best_score = -1e9
    #         for dx, dy in candidates:
    #             nx, ny = self.wrap_xy(px + dx, py + dy)
    #             if not self.is_free(nx, ny):
    #                 continue

    #             score = 0.0
    #             if target is not None:
    #                 ddx = abs(target.x - nx)
    #                 ddy = abs(target.y - ny)
    #                 ddx = min(ddx, self.w - ddx)
    #                 ddy = min(ddy, self.h - ddy)
    #                 score -= (ddx + ddy)
    #             score += random.uniform(-0.05, 0.05)

    #             if score > best_score:
    #                 best_score = score
    #                 best = (nx, ny, dx, dy)

    #         if best is not None:
    #             nx, ny, dx, dy = best
    #             self.predator_pos = (nx, ny)
    #             if (dx, dy) != (0, 0):
    #                 self.predator_heading = (dx, dy)







    def _move_predator(self):
        if self.cfg.task != 2:
            return
        
        # if self.step_count % self.cfg.predator_move_period != 0:
        if self.rng.random() > self.cfg.predator_move_chance:
            return


        for pred in self.predators:
            px, py = pred["pos"]
            predator_heading = pred["heading"]
            target = None

            if hasattr(self, "bats"):
                active = [b for b in self.bats if getattr(b, "alive", True) and not getattr(b, "done", False)]
                if active:
                    def torus_dist(b):
                        dx = abs(b.x - px)
                        dy = abs(b.y - py)
                        dx = min(dx, self.w - dx)
                        dy = min(dy, self.h - dy)
                        return dx + dy

                    nearest = min(active, key=torus_dist)
                    if torus_dist(nearest) <= 18:
                        target = nearest

            if target is not None:
                dx_raw = target.x - px
                dy_raw = target.y - py

                if abs(dx_raw) > self.w / 2:
                    dx_raw = -1 if dx_raw > 0 else 1
                else:
                    dx_raw = 0 if dx_raw == 0 else (1 if dx_raw > 0 else -1)

                if abs(dy_raw) > self.h / 2:
                    dy_raw = -1 if dy_raw > 0 else 1
                else:
                    dy_raw = 0 if dy_raw == 0 else (1 if dy_raw > 0 else -1)

                candidates = [(dx_raw, dy_raw), (dx_raw, 0), (0, dy_raw)] + DIRS
            else:
                candidates = [predator_heading] + DIRS

            best = None
            best_score = -1e9
            for dx, dy in candidates:
                nx, ny = self.wrap_xy(px + dx, py + dy)
                if not self.is_free(nx, ny):
                    continue

                score = 0.0
                if target is not None:
                    ddx = abs(target.x - nx)
                    ddy = abs(target.y - ny)
                    ddx = min(ddx, self.w - ddx)
                    ddy = min(ddy, self.h - ddy)
                    score -= (ddx + ddy)

                score += random.uniform(-0.05, 0.05)

                if score > best_score:
                    best_score = score
                    best = (nx, ny, dx, dy)

            if best is not None:
                nx, ny, dx, dy = best
                pred["pos"] = (nx, ny)
                if (dx, dy) != (0, 0):
                    pred["heading"] = (dx, dy)





    # -------------------------
    # API
    # -------------------------
    # def in_bounds(self, x: int, y: int) -> bool:
    #     return 0 <= x < self.w and 0 <= y < self.h

    # def is_free(self, x: int, y: int) -> bool:
    #     return self.in_bounds(x, y) and self.obstacles[y, x] == 0

    def is_exit(self, x: int) -> bool:
        return x >= self.outside_x0

    # def predator_risk(self, x: int, y: int) -> float:
    #     if self.cfg.task != 2:
    #         return 0.0
    #     px, py = self.predator_pos
    #     dx = x - px
    #     dy = y - py
    #     d2 = dx * dx + dy * dy
    #     return 1.0 if d2 <= (self.cfg.predator_radius ** 2) else 0.0
    # def predator_risk(self, x: int, y: int) -> float:
    #     if self.cfg.task != 2:
    #         return 0.0

    #     px, py = self.predator_pos
    #     dx = abs(x - px)
    #     dy = abs(y - py)

    #     dx = min(dx, self.w - dx)
    #     dy = min(dy, self.h - dy)

    #     d2 = dx * dx + dy * dy
    #     return 1.0 if d2 <= (self.cfg.predator_radius ** 2) else 0.0

    def predator_risk(self, x: int, y: int) -> float:
        if self.cfg.task != 2:
            return 0.0

        for pred in self.predators:
            px, py = pred["pos"]
            dx = abs(x - px)
            dy = abs(y - py)
            dx = min(dx, self.w - dx)
            dy = min(dy, self.h - dy)
            d2 = dx * dx + dy * dy
            if d2 <= (self.cfg.predator_radius ** 2):
                return 1.0
        return 0.0
    
    
    def step(self):
        self.step_count += 1

        if self.cfg.task == 2:
            self._move_prey()
            self._move_predator()

        self.sound.step()