import random
import numpy as np
from dataclasses import dataclass
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

    def ping(self, world: World, cfg: SimConfig, n_rays: int = 8, max_d: int = 10):
        # simple ray distances in 8 directions (no physics), with noise
        dirs = [(1,0), (1,1), (0,1), (-1,1), (-1,0), (-1,-1), (0,-1), (1,-1)]
        out = []
        for (dx, dy) in dirs[:n_rays]:
            d = 0
            cx, cy = self.x, self.y
            for _ in range(max_d):
                cx += dx
                cy += dy
                d += 1
                if not world.in_bounds(cx, cy) or world.obstacles[cy, cx] == 1:
                    break
            # add noise
            noisy = d * (1 + random.uniform(-cfg.ping_noise, cfg.ping_noise))
            out.append(noisy)
        return out


class RuleBasedBat(Bat):
    def act(self, world: World, cfg: SimConfig):
        # Local cues: follow buzz gradient, flee alarm, otherwise explore toward exit (task1) or random
        bx, by = self.x, self.y
        buzz_here = world.sound.buzz[by, bx]
        alarm_here = world.sound.alarm[by, bx]

        # sample neighbor scores
        best = (0, 0)
        best_val = -1e9
        for (dx, dy) in DIRS:
            nx, ny = bx + dx, by + dy
            if not world.is_free(nx, ny):
                continue
            buzz = world.sound.buzz[ny, nx]
            alarm = world.sound.alarm[ny, nx]
            val = (buzz - alarm)

            # Task 1: small bias to move toward exit
            if cfg.task == 1:
                val += 0.02 * nx

            # prefer movement slightly
            if (dx, dy) != (0, 0):
                val += 0.01

            if val > best_val:
                best_val = val
                best = (dx, dy)

        # Emit calls based on state (deposit handled in sim loop)
        call = "NONE"
        if cfg.task == 2:
            if alarm_here > 0.5:
                call = "ALARM"
            elif buzz_here > 0.5:
                call = "BUZZ"
        return best, call


class LLMBat(Bat):
    def __init__(self, x: int, y: int, client: LMStudioClient):
        super().__init__(x, y)
        self.client = client
        self._last_action = (0, 0)
        self._last_call = "NONE"
        self._cooldown = 0  # rate-limit LLM calls
        self.stay_streak = 0

    def _build_prompt(self, obs: dict):
        system = (
            "You control a bat in a 2D grid world.\n"
            "Task 1: reach the exit on the RIGHT side as fast as possible. This is to exit the cave\n"
            "Task 2: collect prey and avoid danger.\n"
            "Return EXACTLY ONE LINE in this format:\n"
            "ACTION: MOVE <dir>\n"
            "Where <dir> is one of: N,NE,E,SE,S,SW,W,NW,STAY.\n"
            "Do NOT output anything else."
            )
        user = (
            f"OBSERVATION:\n"
            f"- task: {obs['task']}\n"
            f"- position: {obs['pos']}\n"
            f"- ping: {obs['ping']}\n"
            f"- local_buzz: {obs['local_buzz']:.3f}\n"
            f"- local_alarm: {obs['local_alarm']:.3f}\n"
            f"- buzz_gradient_hint (dx,dy): {obs['buzz_grad']}\n"
            f"- alarm_gradient_hint (dx,dy): {obs['alarm_grad']}\n"
            f"\nChoose an action.\n"
            f"Return exactly:\n"
            f"ACTION: MOVE <dir>\n"
            f"CALL: <call>\n"
            f"RATIONALE: <one short sentence>\n"
            f"- exit_hint (dx,dy): {obs.get('exit_hint', (0,0))}\n"
        )
        return [{"role": "system", "content": system}, {"role": "user", "content": user}]

    def _parse(self, text: str):
        move = "STAY"
        call = "NONE"
        rationale = ""
        for line in text.splitlines():
            line = line.strip()
            if line.upper().startswith("ACTION:"):
                if "MOVE" in line.upper():
                    move = line.split()[-1].strip().upper()
            elif line.upper().startswith("CALL:"):
                call = line.split(":", 1)[1].strip().upper()
            elif line.upper().startswith("RATIONALE:"):
                rationale = line.split(":", 1)[1].strip()
        if move not in NAME_TO_DIR:
            move = "STAY"
        if call not in {"NONE", "BUZZ", "ALARM"}:
            call = "NONE"
        return NAME_TO_DIR[move], call, rationale

    def act(self, world: World, cfg: SimConfig):
        # LLM call every cfg.llm_decision_period steps; in between, repeat last action
        if self._cooldown > 0:
            self._cooldown -= 1
            return self._last_action, self._last_call, ""

        bx, by = self.x, self.y
        exit_dx = world.exit_x0 - bx  # positive means exit is to the right
        exit_hint = (1 if exit_dx > 0 else 0, 0)  # crude: "go east"
        ping = self.ping(world, cfg)

        # simple gradient hints: compare neighboring buzz/alarm
        def best_grad(field):
            best = (0, 0)
            best_val = field[by, bx]
            for (dx, dy) in DIRS:
                nx, ny = bx + dx, by + dy
                if not world.is_free(nx, ny):
                    continue
                v = field[ny, nx]
                if v > best_val:
                    best_val = v
                    best = (dx, dy)
            return best

        obs = {
            "task": cfg.task,
            "pos": (bx, by),
            "ping": [round(v, 2) for v in ping],
            "local_buzz": float(world.sound.buzz[by, bx]),
            "local_alarm": float(world.sound.alarm[by, bx]),
            "buzz_grad": best_grad(world.sound.buzz),
            "alarm_grad": best_grad(world.sound.alarm),
            "exit_hint": exit_hint,
        }

        msgs = self._build_prompt(obs)
        try:
            out = self.client.chat(msgs)
            print("LLM RAW OUTPUT:\n", out)
        except Exception as e:
            # fallback: do nothing safely
            self._last_action, self._last_call = (0, 0), "NONE"
            self._cooldown = cfg.llm_decision_period
            return self._last_action, self._last_call, f"(LLM error: {e})"

        action, call, rationale = self._parse(out)
        if action == (0,0):
            self.stay_streak += 1
        else:
            self.stay_streak = 0

        # fallback: if stuck, move toward exit in Task 1
        if cfg.task == 1 and self.stay_streak >= 3:
            action = (1, 0)  # E
            self.stay_streak = 0
        self._last_action, self._last_call = action, call
        self._cooldown = cfg.llm_decision_period
        return action, call, rationale