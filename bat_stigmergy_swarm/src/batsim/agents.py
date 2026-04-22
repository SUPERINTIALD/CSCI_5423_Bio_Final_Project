# import random
# import numpy as np
# from dataclasses import dataclass
# from .world import DIRS, World
# from .config import SimConfig
# from ..llm.lm_studio_client import LMStudioClient


# MOVE_NAMES = {
#     (0, 0): "STAY",
#     (1, 0): "E", (-1, 0): "W", (0, 1): "S", (0, -1): "N",
#     (1, 1): "SE", (1, -1): "NE", (-1, 1): "SW", (-1, -1): "NW",
# }
# NAME_TO_DIR = {v: k for k, v in MOVE_NAMES.items()}


# @dataclass
# class Bat:
#     x: int
#     y: int
#     score: float = 0.0
#     prey_collected: int = 0
#     predator_events: int = 0

#     def ping(self, world: World, cfg: SimConfig, n_rays: int = 8, max_d: int = 10):
#         # simple ray distances in 8 directions (no physics), with noise
#         dirs = [(1,0), (1,1), (0,1), (-1,1), (-1,0), (-1,-1), (0,-1), (1,-1)]
#         out = []
#         for (dx, dy) in dirs[:n_rays]:
#             d = 0
#             cx, cy = self.x, self.y
#             for _ in range(max_d):
#                 cx += dx
#                 cy += dy
#                 d += 1
#                 if not world.in_bounds(cx, cy) or world.obstacles[cy, cx] == 1:
#                     break
#             # add noise
#             noisy = d * (1 + random.uniform(-cfg.ping_noise, cfg.ping_noise))
#             out.append(noisy)
#         return out


# class RuleBasedBat(Bat):
#     def act(self, world: World, cfg: SimConfig):
#         # Local cues: follow buzz gradient, flee alarm, otherwise explore toward exit (task1) or random
#         bx, by = self.x, self.y
#         buzz_here = world.sound.buzz[by, bx]
#         alarm_here = world.sound.alarm[by, bx]

#         # sample neighbor scores
#         best = (0, 0)
#         best_val = -1e9
#         for (dx, dy) in DIRS:
#             nx, ny = bx + dx, by + dy
#             if not world.is_free(nx, ny):
#                 continue
#             buzz = world.sound.buzz[ny, nx]
#             alarm = world.sound.alarm[ny, nx]
#             val = (buzz - alarm)

#             # Task 1: small bias to move toward exit
#             if cfg.task == 1:
#                 val += 0.02 * nx

#             # prefer movement slightly
#             if (dx, dy) != (0, 0):
#                 val += 0.01

#             if val > best_val:
#                 best_val = val
#                 best = (dx, dy)

#         # Emit calls based on state (deposit handled in sim loop)
#         call = "NONE"
#         if cfg.task == 2:
#             if alarm_here > 0.5:
#                 call = "ALARM"
#             elif buzz_here > 0.5:
#                 call = "BUZZ"
#         return best, call


# class LLMBat(Bat):
#     def __init__(self, x: int, y: int, client: LMStudioClient):
#         super().__init__(x, y)
#         self.client = client
#         self._last_action = (0, 0)
#         self._last_call = "NONE"
#         self._cooldown = 0  # rate-limit LLM calls
#         self.stay_streak = 0

#     def _build_prompt(self, obs: dict):
#         system = (
#             "You control a bat in a 2D grid world.\n"
#             "Task 1: reach the exit on the RIGHT side as fast as possible. This is to exit the cave\n"
#             "Task 2: collect prey and avoid danger.\n"
#             "Return EXACTLY ONE LINE in this format:\n"
#             "ACTION: MOVE <dir>\n"
#             "Where <dir> is one of: N,NE,E,SE,S,SW,W,NW,STAY.\n"
#             "Do NOT output anything else."
#             )
#         user = (
#             f"OBSERVATION:\n"
#             f"- task: {obs['task']}\n"
#             f"- position: {obs['pos']}\n"
#             f"- ping: {obs['ping']}\n"
#             f"- local_buzz: {obs['local_buzz']:.3f}\n"
#             f"- local_alarm: {obs['local_alarm']:.3f}\n"
#             f"- buzz_gradient_hint (dx,dy): {obs['buzz_grad']}\n"
#             f"- alarm_gradient_hint (dx,dy): {obs['alarm_grad']}\n"
#             f"\nChoose an action.\n"
#             f"Return exactly:\n"
#             f"ACTION: MOVE <dir>\n"
#             f"CALL: <call>\n"
#             f"RATIONALE: <one short sentence>\n"
#             f"- exit_hint (dx,dy): {obs.get('exit_hint', (0,0))}\n"
#         )
#         return [{"role": "system", "content": system}, {"role": "user", "content": user}]

#     def _parse(self, text: str):
#         move = "STAY"
#         call = "NONE"
#         rationale = ""
#         for line in text.splitlines():
#             line = line.strip()
#             if line.upper().startswith("ACTION:"):
#                 if "MOVE" in line.upper():
#                     move = line.split()[-1].strip().upper()
#             elif line.upper().startswith("CALL:"):
#                 call = line.split(":", 1)[1].strip().upper()
#             elif line.upper().startswith("RATIONALE:"):
#                 rationale = line.split(":", 1)[1].strip()
#         if move not in NAME_TO_DIR:
#             move = "STAY"
#         if call not in {"NONE", "BUZZ", "ALARM"}:
#             call = "NONE"
#         return NAME_TO_DIR[move], call, rationale

#     def act(self, world: World, cfg: SimConfig):
#         # LLM call every cfg.llm_decision_period steps; in between, repeat last action
#         if self._cooldown > 0:
#             self._cooldown -= 1
#             return self._last_action, self._last_call, ""

#         bx, by = self.x, self.y
#         exit_dx = world.exit_x0 - bx  # positive means exit is to the right
#         exit_hint = (1 if exit_dx > 0 else 0, 0)  # crude: "go east"
#         ping = self.ping(world, cfg)

#         # simple gradient hints: compare neighboring buzz/alarm
#         def best_grad(field):
#             best = (0, 0)
#             best_val = field[by, bx]
#             for (dx, dy) in DIRS:
#                 nx, ny = bx + dx, by + dy
#                 if not world.is_free(nx, ny):
#                     continue
#                 v = field[ny, nx]
#                 if v > best_val:
#                     best_val = v
#                     best = (dx, dy)
#             return best

#         obs = {
#             "task": cfg.task,
#             "pos": (bx, by),
#             "ping": [round(v, 2) for v in ping],
#             "local_buzz": float(world.sound.buzz[by, bx]),
#             "local_alarm": float(world.sound.alarm[by, bx]),
#             "buzz_grad": best_grad(world.sound.buzz),
#             "alarm_grad": best_grad(world.sound.alarm),
#             "exit_hint": exit_hint,
#         }

#         msgs = self._build_prompt(obs)
#         try:
#             out = self.client.chat(msgs)
#             print("LLM RAW OUTPUT:\n", out)
#         except Exception as e:
#             # fallback: do nothing safely
#             self._last_action, self._last_call = (0, 0), "NONE"
#             self._cooldown = cfg.llm_decision_period
#             return self._last_action, self._last_call, f"(LLM error: {e})"

#         action, call, rationale = self._parse(out)
#         if action == (0,0):
#             self.stay_streak += 1
#         else:
#             self.stay_streak = 0

#         # fallback: if stuck, move toward exit in Task 1
#         if cfg.task == 1 and self.stay_streak >= 3:
#             action = (1, 0)  # E
#             self.stay_streak = 0
#         self._last_action, self._last_call = action, call
#         self._cooldown = cfg.llm_decision_period
#         return action, call, rationale



from dataclasses import dataclass
import random
from typing import Tuple
from .world import DIRS, World
from .config import SimConfig
from ..llm.lm_studio_client import LMStudioClient


MOVE_NAMES = {
    (0, 0): "STAY",
    (1, 0): "E", (-1, 0): "W", (0, 1): "S", (0, -1): "N",
    (1, 1): "SE", (1, -1): "NE", (-1, 1): "SW", (-1, -1): "NW",
}
NAME_TO_DIR = {v: k for k, v in MOVE_NAMES.items()}


@dataclass
class Bat:
    x: int
    y: int
    score: float = 0.0
    prey_collected: int = 0
    predator_events: int = 0
    done: bool = False
    last_ping_step: int = -999
    heading: tuple[int, int] = (1, 0)
    stuck_steps: int = 0
    last_call_step: int = -999
    last_call_type: str = "NONE"
    hungry: bool = True
    alive: bool = True
    follow_leader_ticks: int = 0
    leader_mode: str = "NONE"   # NONE / BUZZ / ALARM
    dying: bool = False
    fade_ticks: int = 0
    fade_total: int = 24
    visible: bool = True
    recruited_ticks: int = 0
    llm_mode: str = "EXPLORE"
    # def ping(self, world: World, cfg: SimConfig, max_d: int = 10):
    #     """
    #     Simple bat-like echolocation abstraction:
    #     8 ray distances with noise.
    #     """
    #     self.last_ping_step = world.step_count
    #     dirs = [(1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1)]
    #     out = []
    #     for dx, dy in dirs:
    #         d = 0
    #         cx, cy = self.x, self.y
    #         for _ in range(max_d):
    #             cx += dx
    #             cy += dy
    #             d += 1
    #             if not world.in_bounds(cx, cy) or world.obstacles[cy, cx] == 1:
    #                 break
    #         noisy = d * (1 + random.uniform(-cfg.ping_noise, cfg.ping_noise))
    #         out.append(round(noisy, 2))
    #     return out

    # def ping(self, world: World, cfg: SimConfig, max_d: int = 10):
    #     """
    #     Labeled echolocation distances by direction.
    #     """
    #     self.last_ping_step = world.step_count
    #     dirs = {
    #         "E":  (1, 0),
    #         "SE": (1, 1),
    #         "S":  (0, 1),
    #         "SW": (-1, 1),
    #         "W":  (-1, 0),
    #         "NW": (-1, -1),
    #         "N":  (0, -1),
    #         "NE": (1, -1),
    #     }
    #     out = {}
    #     for name, (dx, dy) in dirs.items():
    #         d = 0
    #         cx, cy = self.x, self.y
    #         for _ in range(max_d):
    #             cx += dx
    #             cy += dy
    #             d += 1
    #             if not world.in_bounds(cx, cy) or world.obstacles[cy, cx] == 1:
    #                 break
    #         noisy = d * (1 + random.uniform(-cfg.ping_noise, cfg.ping_noise))
    #         out[name] = round(noisy, 2)
    #     return out
    def ping(self, world: World, cfg: SimConfig, max_d: int = 10):
        """
        Labeled echolocation distances by direction.
        In task 2, the world wraps toroidally.
        """
        self.last_ping_step = world.step_count
        dirs = {
            "E":  (1, 0),
            "SE": (1, 1),
            "S":  (0, 1),
            "SW": (-1, 1),
            "W":  (-1, 0),
            "NW": (-1, -1),
            "N":  (0, -1),
            "NE": (1, -1),
        }
        out = {}
        for name, (dx, dy) in dirs.items():
            d = 0
            cx, cy = self.x, self.y
            for _ in range(max_d):
                cx += dx
                cy += dy

                if world.cfg.task == 2:
                    cx, cy = world.wrap_xy(cx, cy)

                d += 1

                if world.cfg.task == 1:
                    if not world.in_bounds(cx, cy):
                        break

                if world.obstacles[cy, cx] == 1:
                    break

            noisy = d * (1 + random.uniform(-cfg.ping_noise, cfg.ping_noise))
            out[name] = round(noisy, 2)
        return out
    def local_patch(self, world: World, radius: int = 4) -> str:
        """
        Tiny symbolic local map.
        # = obstacle/wall
        . = free
        X = self
        E = exit region (Task 1)
        P = prey (Task 2)
        D = predator danger center (Task 2)
        """
        rows = []
        for yy in range(self.y - radius, self.y + radius + 1):
            row = ""
            for xx in range(self.x - radius, self.x + radius + 1):
                if world.cfg.task == 2:
                    wx, wy = world.wrap_xy(xx, yy)
                else:
                    wx, wy = xx, yy

                if xx == self.x and yy == self.y:
                    row += "X"
                elif not world.in_bounds(wx, wy):
                    row += "#"
                elif world.obstacles[wy, wx] == 1:
                    row += "#"
                elif world.cfg.task == 1 and world.is_exit(wx):
                    row += "E"
                elif world.cfg.task == 2 and (wx, wy) in world.prey:
                    row += "P"
                elif world.cfg.task == 2 and (wx, wy) == world.predator_pos:
                    row += "D"
                else:
                    row += "."
            rows.append(row)
        return "\n".join(rows)
    
    # def directional_clearance(self, world: World, max_d: int = 8):
    #     dirs = {
    #         "E": (1, 0),
    #         "NE": (1, -1),
    #         "SE": (1, 1),
    #         "N": (0, -1),
    #         "S": (0, 1),
    #     }
    #     out = {}
    #     for name, (dx, dy) in dirs.items():
    #         d = 0
    #         cx, cy = self.x, self.y
    #         for _ in range(max_d):
    #             cx += dx
    #             cy += dy
    #             if not world.in_bounds(cx, cy) or world.obstacles[cy, cx] == 1:
    #                 break
    #             d += 1
    #         out[name] = d
    #     return out

    def directional_clearance(self, world: World, max_d: int = 8):
        dirs = {
            "E": (1, 0),
            "NE": (1, -1),
            "SE": (1, 1),
            "N": (0, -1),
            "S": (0, 1),
        }
        out = {}
        for name, (dx, dy) in dirs.items():
            d = 0
            cx, cy = self.x, self.y
            for _ in range(max_d):
                cx += dx
                cy += dy

                if world.cfg.task == 2:
                    cx, cy = world.wrap_xy(cx, cy)

                if world.cfg.task == 1 and not world.in_bounds(cx, cy):
                    break

                if world.obstacles[cy, cx] == 1:
                    break

                d += 1
            out[name] = d
        return out
    
    def should_ping(self, world: World, base_prob=0.03, crowded_prob=0.18, crowd_radius=3):
        nearby = 0
        if not hasattr(world, "bat_positions"):
            return random.random() < base_prob

        for (bx, by) in world.bat_positions:
            if (bx, by) == (self.x, self.y):
                continue
            if abs(bx - self.x) <= crowd_radius and abs(by - self.y) <= crowd_radius:
                nearby += 1

        p = crowded_prob if nearby >= 2 else base_prob
        return random.random() < p

    def legal_moves(self, world: World):
        out = {}
        for name, (dx, dy) in NAME_TO_DIR.items():
            nx, ny = self.x + dx, self.y + dy
            out[name] = world.is_free(nx, ny)
        return out
    


    # def entity_cues(self, world: World, radius: int = 18):
    #     """
    #     Returns simple prey/predator cues for the LLM and rule-based logic.
    #     """
    #     def torus_dist(ax, ay, bx, by):
    #         dx = abs(ax - bx)
    #         dy = abs(ay - by)
    #         if world.cfg.task == 2:
    #             dx = min(dx, world.w - dx)
    #             dy = min(dy, world.h - dy)
    #         return dx + dy

    #     def torus_delta(ax, ay, bx, by):
    #         dx = bx - ax
    #         dy = by - ay
    #         if world.cfg.task == 2:
    #             if dx > world.w / 2:
    #                 dx -= world.w
    #             elif dx < -world.w / 2:
    #                 dx += world.w
    #             if dy > world.h / 2:
    #                 dy -= world.h
    #             elif dy < -world.h / 2:
    #                 dy += world.h
    #         return dx, dy

    #     nearest_prey = None
    #     nearest_prey_dist = 10**9
    #     prey_count = 0
    #     for px, py in world.prey:
    #         d = torus_dist(self.x, self.y, px, py)
    #         if d <= radius:
    #             prey_count += 1
    #             if d < nearest_prey_dist:
    #                 nearest_prey_dist = d
    #                 nearest_prey = (px, py)

    #     predator_vec = None
    #     predator_dist = None
    #     if world.cfg.task == 2:
    #         pd = torus_dist(self.x, self.y, world.predator_pos[0], world.predator_pos[1])
    #         if pd <= radius:
    #             predator_dist = pd
    #             predator_vec = torus_delta(self.x, self.y, world.predator_pos[0], world.predator_pos[1])

    #     prey_vec = None
    #     if nearest_prey is not None:
    #         prey_vec = torus_delta(self.x, self.y, nearest_prey[0], nearest_prey[1])

    #     return {
    #         "nearby_prey_count": prey_count,
    #         "nearest_prey_dist": None if nearest_prey is None else nearest_prey_dist,
    #         "nearest_prey_vec": prey_vec,
    #         "predator_dist": predator_dist,
    #         "predator_vec": predator_vec,
    #     }
    def entity_cues(self, world: World, radius: int = 18):
        def torus_dist(ax, ay, bx, by):
            dx = abs(ax - bx)
            dy = abs(ay - by)
            if world.cfg.task == 2:
                dx = min(dx, world.w - dx)
                dy = min(dy, world.h - dy)
            return dx + dy

        def torus_delta(ax, ay, bx, by):
            dx = bx - ax
            dy = by - ay
            if world.cfg.task == 2:
                if dx > world.w / 2:
                    dx -= world.w
                elif dx < -world.w / 2:
                    dx += world.w
                if dy > world.h / 2:
                    dy -= world.h
                elif dy < -world.h / 2:
                    dy += world.h
            return dx, dy

        # nearest prey: global for informed bat
        nearest_prey = None
        nearest_prey_dist = 10**9
        prey_count = 0
        for px, py in world.prey:
            d = torus_dist(self.x, self.y, px, py)
            if d < nearest_prey_dist:
                nearest_prey_dist = d
                nearest_prey = (px, py)
            if d <= radius:
                prey_count += 1

        prey_vec = None
        if nearest_prey is not None:
            prey_vec = torus_delta(self.x, self.y, nearest_prey[0], nearest_prey[1])

        predator_dist = None
        predator_vec = None
        if world.cfg.task == 2:
            predator_dist = torus_dist(self.x, self.y, world.predator_pos[0], world.predator_pos[1])
            predator_vec = torus_delta(self.x, self.y, world.predator_pos[0], world.predator_pos[1])

        return {
            "nearby_prey_count": prey_count,
            "nearest_prey_dist": None if nearest_prey is None else nearest_prey_dist,
            "nearest_prey_vec": prey_vec,
            "predator_dist": predator_dist,
            "predator_vec": predator_vec,
            "predator_pos": world.predator_pos if world.cfg.task == 2 else None,
        }


    def _dir_index(self, move):
        dirs = [(1,0),(1,1),(0,1),(-1,1),(-1,0),(-1,-1),(0,-1),(1,-1)]
        if move == (0, 0):
            return None
        try:
            return dirs.index(move)
        except ValueError:
            return None


    def smooth_move(self, desired_move, world: World):
        """
        Bat-like glide: no instant reverse unless forced.
        """
        if desired_move == (0, 0):
            return desired_move

        if self.heading == (0, 0):
            return desired_move

        dirs = [(1,0),(1,1),(0,1),(-1,1),(-1,0),(-1,-1),(0,-1),(1,-1)]
        h_idx = self._dir_index(self.heading)
        d_idx = self._dir_index(desired_move)

        if h_idx is None or d_idx is None:
            return desired_move

        diff = (d_idx - h_idx) % 8
        if diff > 4:
            diff -= 8

        # if desired turn is too sharp, rotate only one step toward it
        if abs(diff) > 2:
            step = 1 if diff > 0 else -1
            new_idx = (h_idx + step) % 8
            candidate = dirs[new_idx]
        else:
            candidate = desired_move

        if world.cfg.task == 2:
            nx, ny = world.wrap_xy(self.x + candidate[0], self.y + candidate[1])
        else:
            nx, ny = self.x + candidate[0], self.y + candidate[1]

        if world.is_free(nx, ny):
            return candidate

        return desired_move
# class RuleBasedBat(Bat):
#     def act(self, world: World, cfg: SimConfig):
#         if self.done:
#             return (0, 0), "NONE", "done"

#         bx, by = self.x, self.y

#         best = (0, 0)
#         best_val = -1e9

#         for dx, dy in DIRS:
#             nx, ny = bx + dx, by + dy
#             if not world.is_free(nx, ny):
#                 continue

#             val = 0.0

#             # Task 1: move toward exit
#             if cfg.task == 1:
#                 val += 0.15 * nx
#                 if (dx, dy) != (0, 0):
#                     val += 0.02

#             # Task 2: follow buzz, avoid alarm, seek prey, avoid predator
#             if cfg.task == 2:
#                 val += float(world.sound.buzz[ny, nx]) * 1.0
#                 val -= float(world.sound.alarm[ny, nx]) * 1.3
#                 if (nx, ny) in world.prey:
#                     val += 3.0
#                 if world.predator_risk(nx, ny) > 0:
#                     val -= 5.0

#             if val > best_val:
#                 best_val = val
#                 best = (dx, dy)

#         call = "NONE"
#         if cfg.task == 2:
#             if world.predator_risk(self.x, self.y) > 0:
#                 call = "ALARM"
#             elif (self.x, self.y) in world.prey:
#                 call = "BUZZ"

#         return best, call, ""








class RuleBasedBat(Bat):
    def act(self, world: World, cfg: SimConfig):
        if self.done or not self.alive:
            return (0, 0), "NONE", "done"

        bx, by = self.x, self.y
        best = (0, 0)
        best_val = -1e9

        llm_target = None
        if hasattr(world, "bats"):
            for other in world.bats:
                if isinstance(other, LLMBat) and getattr(other, "alive", True) and not getattr(other, "done", False):
                    llm_target = (other.x, other.y)
                    break

        prev_hx, prev_hy = self.heading
        jammed = self.stuck_steps >= 2

        def torus_dist(ax, ay, bx, by):
            dx = abs(ax - bx)
            dy = abs(ay - by)
            if cfg.task == 2:
                dx = min(dx, world.w - dx)
                dy = min(dy, world.h - dy)
            return dx + dy

        # px, py = world.predator_pos if cfg.task == 2 else (-999, -999)
        # predator_close = cfg.task == 2 and torus_dist(bx, by, px, py) <= (cfg.predator_radius + 6)
        px, py = world.predator_pos if cfg.task == 2 else (-999, -999)
        current_predator_close = cfg.task == 2 and torus_dist(bx, by, px, py) <= (cfg.predator_radius + 14)
        candidate_predator_close = False
        for dx, dy in DIRS:
            if cfg.task == 2:
                nx, ny = world.wrap_xy(bx + dx, by + dy)
            else:
                nx, ny = bx + dx, by + dy

            if not world.is_free(nx, ny):
                continue

            val = 0.0
            # short-range separation: don't stack bats on top of each other
            if hasattr(world, "bat_positions"):
                for ox, oy in world.bat_positions:
                    if (ox, oy) == (bx, by):
                        continue
                    dsep = torus_dist(nx, ny, ox, oy) if cfg.task == 2 else (abs(nx - ox) + abs(ny - oy))
                    if dsep <= 1:
                        val -= 6.0
                    elif dsep == 2:
                        val -= 2.0

            # ---------------- TASK 1 ----------------
            if cfg.task == 1:
                val += 0.08 * dx
                if dx > 0:
                    val += 0.10

                clearance_score = 0
                for sx, sy in [(1,0), (1,-1), (1,1), (0,-1), (0,1), (-1,0), (-1,-1), (-1,1)]:
                    tx, ty = nx, ny
                    d = 0
                    for _ in range(6):
                        tx += sx
                        ty += sy
                        if not world.in_bounds(tx, ty) or not world.is_free(tx, ty):
                            break
                        d += 1
                    clearance_score += d
                val += 0.12 * clearance_score

                free_neighbors = 0
                for sx, sy in DIRS:
                    tx, ty = nx + sx, ny + sy
                    if world.is_free(tx, ty):
                        free_neighbors += 1
                val += 0.25 * free_neighbors

                if (dx, dy) == (prev_hx, prev_hy):
                    val += 0.08

                # 3) informed individual leadership
                if llm_target is not None:
                    lx, ly = llm_target
                    old_ld = torus_dist(bx, by, lx, ly)
                    new_ld = torus_dist(nx, ny, lx, ly)

                    # default: stay with informed leader
                    if new_ld < old_ld:
                        val += 3.0

                    # stronger if already near the leader
                    if old_ld <= 18 and new_ld < old_ld:
                        val += 1.5

                    # if in explicit follow mode, really commit
                    if self.follow_leader_ticks > 0:
                        if self.leader_mode == "ALARM":
                            if new_ld < old_ld and new_pd > old_pd:
                                val += 4.0
                        elif self.leader_mode == "BUZZ":
                            if self.hungry and new_ld < old_ld:
                                val += 4.0

                    # punish drifting too far from leader unless escaping danger
                    if not candidate_predator_close and new_ld > 20:
                        val -= 3.0

                if jammed:
                    if dy != 0:
                        val += 0.35
                    if (dx, dy) == (0, 0):
                        val -= 1.0

                if (dx, dy) == (0, 0):
                    val -= 0.35

            # ---------------- TASK 2 ----------------
            if cfg.task == 2:
            

                px, py = world.predator_pos
                old_pd = torus_dist(bx, by, px, py)
                new_pd = torus_dist(nx, ny, px, py)
                candidate_predator_close = old_pd <= (cfg.predator_radius + 8)

                # --------------------------
                # 1) strong predator avoidance
                # --------------------------
                if world.predator_risk(nx, ny) > 0:
                    val -= 40.0

                if new_pd > old_pd:
                    val += 2.5

                if candidate_predator_close and new_pd > old_pd:
                    val += 5.0

                val -= float(world.sound.alarm[ny, nx]) * 3.0

                # --------------------------
                # 2) flock cohesion
                # --------------------------
                group_neighbors = []
                if hasattr(world, "bat_positions"):
                    for ox, oy in world.bat_positions:
                        if (ox, oy) == (bx, by):
                            continue
                        d_old = torus_dist(bx, by, ox, oy)
                        if d_old <= 18:
                            d_new = torus_dist(nx, ny, ox, oy)
                            group_neighbors.append((d_old, d_new))

                if group_neighbors:
                    mean_old = sum(d0 for d0, _ in group_neighbors) / len(group_neighbors)
                    mean_new = sum(d1 for _, d1 in group_neighbors) / len(group_neighbors)

                    # always try to re-form into flock after disruption
                    if mean_new < mean_old:
                        val += 2.0

                    # punish drifting too far from local flock
                    if mean_new > 10:
                        val -= 3

                    # in predator situations, cohesion matters even more
                    if candidate_predator_close and mean_new <= mean_old + 1.0:
                        val += 2.5

                # --------------------------
                # 3) informed individual leadership
                # --------------------------
                if llm_target is not None:
                    lx, ly = llm_target
                    old_ld = torus_dist(bx, by, lx, ly)
                    new_ld = torus_dist(nx, ny, lx, ly)

                    # default: stay with informed leader whenever possible
                    if new_ld < old_ld:
                        val += 2.2

                    # stronger if already close to leader
                    if old_ld <= 20 and new_ld < old_ld:
                        val += 1.2

                    # if wrapped path is shorter, torus_dist already handles that
                    # so bats will naturally choose whichever side is closer

                    # during alarm, strongly follow leader escape
                    if self.follow_leader_ticks > 0 and self.leader_mode == "ALARM":
                        if new_ld < old_ld and new_pd > old_pd:
                            val += 3.5

                    # during food recruitment, hungry bats follow leader more
                    if self.follow_leader_ticks > 0 and self.leader_mode == "BUZZ":
                        if self.hungry and new_ld < old_ld:
                            val += 3.0
                # if not in immediate danger, strongly discourage being far from leader
                if llm_target is not None and not candidate_predator_close:
                    lx, ly = llm_target
                    new_ld = torus_dist(nx, ny, lx, ly)
                    if new_ld > 22:
                        val -= 2.0
                # --------------------------
                # 4) prey seeking only for hungry / recruited bats
                # --------------------------
                # 4) prey seeking as subgroup behavior
                buzz_weight = 0.2
                if self.hungry:
                    buzz_weight = 0.8
                if self.recruited_ticks > 0 or (self.follow_leader_ticks > 0 and self.leader_mode == "BUZZ"):
                    buzz_weight = 3.5

                val += float(world.sound.buzz[ny, nx]) * buzz_weight
                # direct nearest-prey attraction for hungry bats
                if self.hungry and world.prey:
                    nearest_prey = None
                    nearest_prey_old = 10**9
                    nearest_prey_new = 10**9

                    for px2, py2 in world.prey:
                        d_old = torus_dist(bx, by, px2, py2)
                        d_new = torus_dist(nx, ny, px2, py2)
                        if d_old < nearest_prey_old:
                            nearest_prey_old = d_old
                            nearest_prey_new = d_new
                            nearest_prey = (px2, py2)

                    if nearest_prey is not None:
                        if nearest_prey_new < nearest_prey_old:
                            val += 2.5
                        if nearest_prey_new <= 10:
                            val += 2.0
                # direct prey attraction only really matters for hungry bats near the recruited subgroup
                if (nx, ny) in world.prey:
                    val += 14.0 if self.hungry else 1.0
                elif self.hungry and (self.recruited_ticks > 0 or self.leader_mode == "BUZZ"):
                    val += 0.8

                # --------------------------
                # 5) free-space / motion bias
                # --------------------------
                free_neighbors = 0
                for sx, sy in DIRS:
                    tx, ty = world.wrap_xy(nx + sx, ny + sy)
                    if world.is_free(tx, ty):
                        free_neighbors += 1
                val += 0.10 * free_neighbors

                if (dx, dy) == (prev_hx, prev_hy):
                    val += 0.15

                if (dx, dy) == (0, 0):
                    val -= 0.5

            # IMPORTANT: shared best-move update
            if val > best_val:
                best_val = val
                best = (dx, dy)
                # exploration bonus when no close prey and no close predator
            if world.prey:
                nearest_any = min(torus_dist(nx, ny, px2, py2) for px2, py2 in world.prey)
            else:
                nearest_any = 10**9

            if nearest_any > 20 and not candidate_predator_close:
                if (dx, dy) != (0, 0):
                    val += 0.4
                if (dx, dy) == (prev_hx, prev_hy):
                    val -= 0.1  # discourage infinite straight drift

        call = "NONE"
        if cfg.task == 2:
            if current_predator_close or world.predator_risk(self.x, self.y) > 0:
                call = "ALARM"
            elif self.hungry:
                prey_near = False
                for px2, py2 in world.prey:
                    if torus_dist(self.x, self.y, px2, py2) <= 2:
                        prey_near = True
                        break

                if prey_near or self.recruited_ticks > 0:
                    call = "BUZZ"

        return best, call, ""
# class RuleBasedBat(Bat):
#     def act(self, world: World, cfg: SimConfig):
#         if self.done:
#             return (0, 0), "NONE", "done"

#         bx, by = self.x, self.y
#         best = (0, 0)
#         best_val = -1e9

#         llm_target = None
#         if hasattr(world, "bats"):
#             for other in world.bats:
#                 if isinstance(other, LLMBat) and not getattr(other, "done", False):
#                     llm_target = (other.x, other.y)
#                     break

#         prev_hx, prev_hy = self.heading
#         jammed = self.stuck_steps >= 2

#         for dx, dy in DIRS:
#             if cfg.task == 2:
#                 nx, ny = world.wrap_xy(bx + dx, by + dy)
#             else:
#                 nx, ny = bx + dx, by + dy
#             if not world.is_free(nx, ny):
#                 continue

#             val = 0.0

#             if cfg.task == 1:
#                 # normal cave progress
#                 val += 0.08 * dx
#                 if dx > 0:
#                     val += 0.10

#                 # strongly prefer open space around target
#                 clearance_score = 0
#                 for sx, sy in [(1,0), (1,-1), (1,1), (0,-1), (0,1), (-1,0), (-1,-1), (-1,1)]:
#                     tx, ty = nx, ny
#                     d = 0
#                     for _ in range(6):
#                         tx += sx
#                         ty += sy
#                         if not world.in_bounds(tx, ty) or not world.is_free(tx, ty):
#                             break
#                         d += 1
#                     clearance_score += d
#                 val += 0.12 * clearance_score

#                 # prefer cells with many free neighbors
#                 free_neighbors = 0
#                 for sx, sy in DIRS:
#                     if cfg.task == 2:
#                         tx, ty = world.wrap_xy(nx + sx, ny + sy)
#                     else:
#                         tx, ty = nx + sx, ny + sy

#                     if world.is_free(tx, ty):
#                         free_neighbors += 1
#                 val += 0.25 * free_neighbors

#                 # slight directional persistence
#                 if (dx, dy) == (prev_hx, prev_hy):
#                     val += 0.08

#                 # small reward for moving toward informed bat, but less when jammed
#                 if llm_target is not None:
#                     lx, ly = llm_target
#                     old_dist = abs(bx - lx) + abs(by - ly)
#                     new_dist = abs(nx - lx) + abs(ny - ly)
#                     if new_dist < old_dist:
#                         val += 0.10 if not jammed else 0.02

#                 # if jammed, strongly prefer changing row / escaping bottleneck
#                 if jammed:
#                     if dy != 0:
#                         val += 0.35
#                     if (dx, dy) == (0, 0):
#                         val -= 1.0

#                 # discourage staying
#                 if (dx, dy) == (0, 0):
#                     val -= 0.35

#             if cfg.task == 2:
#                 buzz_weight = 2.2 if self.hungry else 0.2
#                 alarm_weight = 2.5

#                 val += float(world.sound.buzz[ny, nx]) * buzz_weight
#                 val -= float(world.sound.alarm[ny, nx]) * alarm_weight

#                 # direct prey seeking
#                 if (nx, ny) in world.prey:
#                     val += 8.0 if self.hungry else 1.0

#                 # avoid predator hard
#                 if world.predator_risk(nx, ny) > 0:
#                     val -= 20.0

#                 px, py = world.predator_pos
#                 old_pd_x = abs(bx - px)
#                 old_pd_y = abs(by - py)
#                 new_pd_x = abs(nx - px)
#                 new_pd_y = abs(ny - py)

#                 old_pd_x = min(old_pd_x, world.w - old_pd_x)
#                 old_pd_y = min(old_pd_y, world.h - old_pd_y)
#                 new_pd_x = min(new_pd_x, world.w - new_pd_x)
#                 new_pd_y = min(new_pd_y, world.h - new_pd_y)

#                 if (new_pd_x + new_pd_y) > (old_pd_x + old_pd_y):
#                     val += 1.5

#                 # leader following only if hungry and safe
#                 if llm_target is not None and self.hungry and world.predator_risk(nx, ny) == 0:
#                     lx, ly = llm_target
#                     old_ld = abs(bx - lx) + abs(by - ly)
#                     new_ld = abs(nx - lx) + abs(ny - ly)
#                     if new_ld < old_ld:
#                         val += 0.6

#                 free_neighbors = 0
#                 for sx, sy in DIRS:
#                     tx, ty = nx + sx, ny + sy
#                     if world.is_free(tx, ty):
#                         free_neighbors += 1
#                 val += 0.12 * free_neighbors

#                 if (dx, dy) == (0, 0):
#                     val -= 0.5

#                 if val > best_val:
#                     best_val = val
#                     best = (dx, dy)

#         call = "NONE"
#         # if cfg.task == 2:
#         #     if world.predator_risk(self.x, self.y) > 0:
#         #         call = "ALARM"
#         #     elif (self.x, self.y) in world.prey:
#         #         call = "BUZZ"
#         if cfg.task == 2:
#             if world.predator_risk(self.x, self.y) > 0:
#                 call = "ALARM"
#             elif self.hungry:
#                 prey_near = False
#                 for px, py in world.prey:
#                     dx = abs(self.x - px)
#                     dy = abs(self.y - py)
#                     dx = min(dx, world.w - dx) if cfg.task == 2 else dx
#                     dy = min(dy, world.h - dy) if cfg.task == 2 else dy
#                     if dx <= 2 and dy <= 2:
#                         prey_near = True
#                         break
#                 if prey_near:
#                     call = "BUZZ"
#         return best, call, ""
    
class LLMBat(Bat):
    def __init__(self, x: int, y: int, client: LMStudioClient):
        super().__init__(x, y)
        self.client = client
        self.last_action = (0, 0)
        self.last_call = "NONE"
        self.last_rationale = ""
        self.stay_streak = 0

    def _build_prompt(self, obs: dict):
        if obs["task"] == 1:
            system = (
                "You are controlling one bat in a 2D cave simulation.\n"
                "Task 1: there is NO prey and NO predator.\n"
                "Your goal is to leave the cave by reaching open space on the RIGHT side.\n"
                "You are given legal moves, directional clearance, and a local patch.\n"
                "If East is blocked, choose another LEGAL move that increases free space while still progressing rightward.\n"
                "Do NOT output a blocked move.\n"
                "Return EXACTLY these lines:\n"
                "ACTION: <N|NE|E|SE|S|SW|W|NW|STAY>\n"
                "RATIONALE: <one short sentence>\n"
            )
            user = (
                f"position={obs['position']}\n"
                f"exit_hint={obs['exit_hint']}\n"
                f"legal_moves={obs['legal_moves']}\n"
                f"clearance={obs['clearance']}\n"
                f"ping={obs['ping']}\n"
                f"local_patch=\n{obs['local_patch']}\n"
            )
        else:
            # system = (
            #     "You are controlling one bat in a 2D outside environment.\n"
            #     "Task 2: collect prey and avoid predator danger.\n"
            #     "Use legal moves, ping, soundscape traces, and local patch.\n"
            #     "If predator danger is nearby, use CALL: ALARM.\n"
            #     "If prey is found or strongly indicated, use CALL: BUZZ.\n"
            #     "Return EXACTLY these lines:\n"
            #     "ACTION: <N|NE|E|SE|S|SW|W|NW|STAY>\n"
            #     "CALL: <NONE|BUZZ|ALARM>\n"
            #     "RATIONALE: <one short sentence>\n"
            # )
            # system = (
            #     "You are controlling one bat in a 2D outside environment.\n"
            #     "Task 2: collect prey and avoid predator danger.\n"
            #     "IMPORTANT: the world wraps around like a torus. "
            #     "If you move off the left edge you appear on the right edge, "
            #     "and if you move off the top edge you appear on the bottom edge.\n"
            #     "Use legal moves, ping, soundscape traces, and local patch.\n"
            #     "The local patch is centered on you, but the world edges connect.\n"
            #     "If predator danger is nearby, use CALL: ALARM.\n"
            #     "If prey is found or strongly indicated, use CALL: BUZZ.\n"
            #     "Return EXACTLY these lines:\n"
            #     "ACTION: <N|NE|E|SE|S|SW|W|NW|STAY>\n"
            #     "CALL: <NONE|BUZZ|ALARM>\n"
            #     "RATIONALE: <one short sentence>\n"
            # )
            # user = (
            #     f"position={obs['position']}\n"
            #     f"legal_moves={obs['legal_moves']}\n"
            #     f"clearance={obs['clearance']}\n"
            #     f"ping={obs['ping']}\n"
            #     f"local_buzz={obs['local_buzz']:.3f}\n"
            #     f"local_alarm={obs['local_alarm']:.3f}\n"
            #     f"local_patch=\n{obs['local_patch']}\n"
            # )




            # system = (
            #     "You are controlling one informed bat in a 2D outside environment.\n"
            #     "Task 2: lead the group to prey and away from predator danger.\n"
            #     "The world wraps immediately left-right and top-bottom like a torus.\n"
            #     "You are a LEADER: nearby bats may follow your BUZZ or ALARM calls.\n"
            #     "Use legal moves, ping, local patch, prey/predator vectors, and soundscape.\n"
            #     "Rules:\n"
            #     "- If predator_dist is small or predator_vec is present and close, use CALL: ALARM.\n"
            #     "- If prey is nearby and you are guiding bats to food, use CALL: BUZZ.\n"
            #     "- Otherwise use CALL: NONE.\n"
            #     "- CALL must be exactly one of: NONE, BUZZ, ALARM.\n"
            #     "- ACTION must be exactly one of: N, NE, E, SE, S, SW, W, NW, STAY.\n"
            #     "- Never output any other call token.\n"
            #     "Return EXACTLY these lines:\n"
            #     "ACTION: <N|NE|E|SE|S|SW|W|NW|STAY>\n"
            #     "CALL: <NONE|BUZZ|ALARM>\n"
            #     "RATIONALE: <one short sentence>\n"
            # )
            # user = (
            #     f"position={obs['position']}\n"
            #     f"legal_moves={obs['legal_moves']}\n"
            #     f"clearance={obs['clearance']}\n"
            #     f"ping={obs['ping']}\n"
            #     f"local_buzz={obs['local_buzz']:.3f}\n"
            #     f"local_alarm={obs['local_alarm']:.3f}\n"
            #     f"nearest_prey_vec={obs['nearest_prey_vec']}\n"
            #     f"nearest_prey_dist={obs['nearest_prey_dist']}\n"
            #     f"nearby_prey_count={obs['nearby_prey_count']}\n"
            #     f"predator_vec={obs['predator_vec']}\n"
            #     f"predator_dist={obs['predator_dist']}\n"
            #     f"predator_pos={obs['predator_pos']}\n"
            #     f"local_patch=\n{obs['local_patch']}\n"
            # )
            system = (
                "You are controlling one informed bat in a 2D outside environment.\n"
                "Your job is to choose the bat's HIGH-LEVEL MODE, not the exact movement.\n"
                "Main goal: move toward prey.\n"
                "If predator is close, choose FLEE.\n"
                "If prey exists and predator is not close, choose FORAGE.\n"
                "If no strong cue exists, choose EXPLORE.\n"
                "You may also choose a call:\n"
                "- ALARM when predator is close\n"
                "- BUZZ when guiding bats to prey\n"
                "- NONE otherwise\n"
                "Return EXACTLY these lines:\n"
                "MODE: <FORAGE|FLEE|EXPLORE>\n"
                "CALL: <NONE|BUZZ|ALARM>\n"
                "RATIONALE: <one short sentence>\n"
            )
            user = (
                f"position={obs['position']}\n"
                f"legal_moves={obs['legal_moves']}\n"
                f"clearance={obs['clearance']}\n"
                f"ping={obs['ping']}\n"
                f"local_buzz={obs['local_buzz']:.3f}\n"
                f"local_alarm={obs['local_alarm']:.3f}\n"
                f"nearest_prey_vec={obs['nearest_prey_vec']}\n"
                f"nearest_prey_dist={obs['nearest_prey_dist']}\n"
                f"nearby_prey_count={obs['nearby_prey_count']}\n"
                f"predator_vec={obs['predator_vec']}\n"
                f"predator_dist={obs['predator_dist']}\n"
                f"predator_pos={obs['predator_pos']}\n"
                f"local_patch=\n{obs['local_patch']}\n"
            )

        return [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]

    # def _parse(self, text: str, task: int):
    #     move = "STAY"
    #     call = "NONE"
    #     rationale = ""

    #     for line in text.splitlines():
    #         s = line.strip()
    #         if s.upper().startswith("ACTION:"):
    #             move = s.split(":", 1)[1].strip().upper().replace("MOVE", "").strip()
    #         elif s.upper().startswith("CALL:"):
    #             call = s.split(":", 1)[1].strip().upper()
    #         elif s.upper().startswith("RATIONALE:"):
    #             rationale = s.split(":", 1)[1].strip()

    #     if move not in NAME_TO_DIR:
    #         move = "STAY"

    #     if task == 1:
    #         call = "NONE"
    #     elif call not in {"NONE", "BUZZ", "ALARM"}:
    #         call = "NONE"

    #     return NAME_TO_DIR[move], call, rationale
    def _parse(self, text: str, task: int):
        move = "STAY"
        mode = "EXPLORE"
        call = "NONE"
        rationale = ""

        for line in text.splitlines():
            s = line.strip()
            if task == 1 and s.upper().startswith("ACTION:"):
                move = s.split(":", 1)[1].strip().upper().replace("MOVE", "").strip()
            elif task == 2 and s.upper().startswith("MODE:"):
                mode = s.split(":", 1)[1].strip().upper()
            elif s.upper().startswith("CALL:"):
                call = s.split(":", 1)[1].strip().upper()
            elif s.upper().startswith("RATIONALE:"):
                rationale = s.split(":", 1)[1].strip()

        if move not in NAME_TO_DIR:
            move = "STAY"
        if mode not in {"FORAGE", "FLEE", "EXPLORE"}:
            mode = "EXPLORE"
        if call not in {"NONE", "BUZZ", "ALARM"}:
            call = "NONE"

        return NAME_TO_DIR[move], mode, call, rationale
    def query_llm(self, world: World, cfg: SimConfig):
        if self.done:
            self.last_action, self.last_call, self.last_rationale = (0, 0), "NONE", "done"
            return

        # obs = {
        #     "task": cfg.task,
        #     "position": (self.x, self.y),
        #     "exit_hint": "RIGHT",
        #     "ping": self.ping(world, cfg),
        #     "local_patch": self.local_patch(world, radius=4),
        #     "clearance": self.directional_clearance(world),
        #     "legal_moves": self.legal_moves(world),
        #     "local_buzz": float(world.sound.buzz[self.y, self.x]),
        #     "local_alarm": float(world.sound.alarm[self.y, self.x]),
        # }

        entity = self.entity_cues(world, radius=18)

        obs = {
            "task": cfg.task,
            "position": (self.x, self.y),
            "exit_hint": "RIGHT",
            "ping": self.ping(world, cfg),
            "local_patch": self.local_patch(world, radius=4),
            "clearance": self.directional_clearance(world),
            "legal_moves": self.legal_moves(world),
            "local_buzz": float(world.sound.buzz[self.y, self.x]),
            "local_alarm": float(world.sound.alarm[self.y, self.x]),
            "nearest_prey_vec": entity["nearest_prey_vec"],
            "nearest_prey_dist": entity["nearest_prey_dist"],
            "nearby_prey_count": entity["nearby_prey_count"],
            "predator_vec": entity["predator_vec"],
            "predator_dist": entity["predator_dist"],
            "predator_pos": entity["predator_pos"],

        }
        msgs = self._build_prompt(obs)
        out = self.client.chat(msgs, max_tokens=80)
        print("LLM RAW OUTPUT:\n", out)
        if cfg.task == 1:
            action, _, call, rationale = self._parse(out, cfg.task)

            if action == (0, 0):
                self.stay_streak += 1
            else:
                self.stay_streak = 0

            if self.stay_streak >= 3:
                action = (1, 0)
                call = "NONE"
                rationale = "Fallback move toward exit after repeated STAY."
                self.stay_streak = 0

            self.last_action = self.smooth_move(action, world)
            self.last_call = call
            self.last_rationale = rationale
            self.llm_mode = "EXPLORE"
            return

        # -----------------------------
        # Task 2: mode-based control
        # -----------------------------
        _, mode, call, rationale = self._parse(out, cfg.task)
        entity = self.entity_cues(world, radius=18)

        predator_dist = entity["predator_dist"]
        predator_vec = entity["predator_vec"]
        prey_dist = entity["nearest_prey_dist"]
        prey_vec = entity["nearest_prey_vec"]

        # hard override mode
        if predator_dist is not None and predator_dist <= (cfg.predator_radius + 8):
            mode = "FLEE"
        elif prey_vec is not None:
            mode = "FORAGE"
        else:
            mode = "EXPLORE"

        # hard override call
        if predator_dist is not None and predator_dist <= (cfg.predator_radius + 8):
            call = "ALARM"
        elif self.hungry and prey_dist is not None and prey_dist <= 30:
            call = "BUZZ"
        else:
            call = "NONE"

        # convert mode -> action
        action = (0, 0)

        if mode == "FLEE" and predator_vec is not None:
            pvx, pvy = predator_vec
            move_dx = 0 if pvx == 0 else (-1 if pvx > 0 else 1)
            move_dy = 0 if pvy == 0 else (-1 if pvy > 0 else 1)
            action = (move_dx, move_dy)

        elif mode == "FORAGE" and prey_vec is not None:
            pvx, pvy = prey_vec
            move_dx = 0 if pvx == 0 else (1 if pvx > 0 else -1)
            move_dy = 0 if pvy == 0 else (1 if pvy > 0 else -1)
            action = (move_dx, move_dy)

        else:
            # exploration
            explore_choices = [
                (1, 0), (1, -1), (0, -1), (-1, -1),
                (-1, 0), (-1, 1), (0, 1), (1, 1)
            ]
            if self.heading in explore_choices:
                explore_choices.remove(self.heading)
                explore_choices.append(self.heading)

            for cand in explore_choices:
                tx, ty = world.wrap_xy(self.x + cand[0], self.y + cand[1]) if cfg.task == 2 else (self.x + cand[0], self.y + cand[1])
                if world.is_free(tx, ty):
                    action = cand
                    break

        action = self.smooth_move(action, world)

        if action == (0, 0):
            self.stay_streak += 1
        else:
            self.stay_streak = 0

        self.last_action = action
        self.last_call = call
        self.last_rationale = rationale
        self.llm_mode = mode

        print(
            f"LLM DECISION | pos={(self.x, self.y)} | mode={mode} | "
            f"predator_dist={predator_dist} | prey_dist={prey_dist} | "
            f"call={call} | action={action}"
        )
        # action, call, rationale = self._parse(out)
        # action, call, rationale = self._parse(out, cfg.task)
        # if action == (0, 0):
        #     self.stay_streak += 1
        # else:
        #     self.stay_streak = 0
        # action, call, rationale = self._parse(out, cfg.task)




        # # -----------------------------
        # # hard call override for Task 2
        # # -----------------------------
        # if cfg.task == 2:
        #     entity = self.entity_cues(world, radius=18)

        #     predator_dist = entity["predator_dist"]
        #     prey_dist = entity["nearest_prey_dist"]
        #     prey_count = entity["nearby_prey_count"]

        #     # force alarm if predator is genuinely close
        #     if predator_dist is not None and predator_dist <= (cfg.predator_radius + 7):
        #         call = "ALARM"

        #     # otherwise buzz if prey is nearby and bat is still hungry
        #     elif self.hungry and prey_dist is not None and prey_dist <= 30:
        #         call = "BUZZ"

        #     # otherwise none
        #     else:
        #         call = "NONE"

        # # smooth movement after parse
        # # if predator is close, bias movement away from predator before smoothing
        # # if predator is close, bias movement away from predator before smoothing
        # if cfg.task == 2 and entity["predator_vec"] is not None and entity["predator_dist"] is not None:
        #     if entity["predator_dist"] <= (cfg.predator_radius + 4):
        #         pvx, pvy = entity["predator_vec"]
        #         away_dx = 0 if pvx == 0 else (-1 if pvx > 0 else 1)
        #         away_dy = 0 if pvy == 0 else (-1 if pvy > 0 else 1)
        #         forced_escape = (away_dx, away_dy)

        #         tx, ty = world.wrap_xy(self.x + forced_escape[0], self.y + forced_escape[1]) if cfg.task == 2 else (self.x + forced_escape[0], self.y + forced_escape[1])
        #         if world.is_free(tx, ty):
        #             action = forced_escape

        # # otherwise, if prey is close and safe, bias toward prey
        # elif cfg.task == 2 and entity["nearest_prey_vec"] is not None and entity["nearest_prey_dist"] is not None:
        #     if entity["nearest_prey_dist"] <= 60:
        #         pvx, pvy = entity["nearest_prey_vec"]
        #         prey_dx = 0 if pvx == 0 else (1 if pvx > 0 else -1)
        #         prey_dy = 0 if pvy == 0 else (1 if pvy > 0 else -1)
        #         forced_prey = (prey_dx, prey_dy)

        #         tx, ty = world.wrap_xy(self.x + forced_prey[0], self.y + forced_prey[1]) if cfg.task == 2 else (self.x + forced_prey[0], self.y + forced_prey[1])
        #         if world.is_free(tx, ty):
        #             action = forced_prey

        # action = self.smooth_move(action, world)
        # # exploration mode: if prey is far and predator is not close, don't keep marching in one direction forever
        # if cfg.task == 2:
        #     far_from_prey = entity["nearest_prey_dist"] is None or entity["nearest_prey_dist"] > 60
        #     safe_from_pred = entity["predator_dist"] is None or entity["predator_dist"] > (cfg.predator_radius + 8)

        #     if far_from_prey and safe_from_pred:
        #         explore_choices = [(0, -1), (1, -1), (1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1)]
        #         random.shuffle(explore_choices)
        #         for cand in explore_choices:
        #             tx, ty = world.wrap_xy(self.x + cand[0], self.y + cand[1]) if cfg.task == 2 else (self.x + cand[0], self.y + cand[1])
        #             if world.is_free(tx, ty):
        #                 action = cand
        #                 break
        # if action == (0, 0):
        #     self.stay_streak += 1
        # else:
        #     self.stay_streak = 0

        # # fallback so it does not freeze forever
        # if cfg.task == 1 and self.stay_streak >= 3:
        #     action = (1, 0)  # move east
        #     call = "NONE"
        #     rationale = "Fallback move toward exit after repeated STAY."
        #     self.stay_streak = 0


        # # action = self.smooth_move(action, world)


        # self.last_action = action
        # self.last_call = call
        # self.last_rationale = rationale

        # if cfg.task == 2:
        #     print(
        #         f"LLM DECISION | pos={(self.x, self.y)} | "
        #         f"predator_dist={entity['predator_dist']} | "
        #         f"prey_dist={entity['nearest_prey_dist']} | "
        #         f"call={call} | action={action}"
        #     )

    def act(self, world: World, cfg: SimConfig):
        if self.done:
            return (0, 0), "NONE", "done"
        return self.last_action, self.last_call, self.last_rationale