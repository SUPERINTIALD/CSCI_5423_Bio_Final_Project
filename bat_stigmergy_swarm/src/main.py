# Working Task 1
# import sys
# import pygame
# import random
# import os
# import imageio.v2 as imageio


# from .batsim.config import SimConfig
# from .batsim.world import World
# from .batsim.agents import RuleBasedBat, LLMBat
# from .llm.lm_studio_client import LMStudioClient


# def clustered_spawn_positions(world, n, center_x=8, center_y=None, radius=3):
#     if center_y is None:
#         center_y = world.h // 2

#     positions = []
#     used = set()

#     tries = 0
#     while len(positions) < n and tries < 4000:
#         tries += 1
#         x = random.randint(max(0, center_x - radius), min(world.w - 1, center_x + radius))
#         y = random.randint(max(0, center_y - radius), min(world.h - 1, center_y + radius))
#         if world.is_free(x, y) and (x, y) not in used:
#             positions.append((x, y))
#             used.add((x, y))

#     tries = 0
#     while len(positions) < n and tries < 10000:
#         tries += 1
#         x = random.randint(1, max(10, world.outside_x0 // 4))
#         y = random.randint(1, world.h - 2)
#         if world.is_free(x, y) and (x, y) not in used:
#             positions.append((x, y))
#             used.add((x, y))

#     if len(positions) < n:
#         raise RuntimeError(
#             f"Could only place {len(positions)} bats out of {n}. "
#             f"Try reducing n_bats or increasing free cave space."
#         )

#     return positions


# def local_free_neighbors(world, x, y):
#     count = 0
#     for dx, dy in [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]:
#         nx, ny = x + dx, y + dy
#         if world.is_free(nx, ny):
#             count += 1
#     return count


# def candidate_moves_for_bat(bat, preferred):
#     dx, dy = preferred

#     # More diverse fallback ordering to reduce pileups
#     if dx > 0:
#         candidates = [
#             (dx, dy),
#             (1, -1), (1, 1), (1, 0),
#             (0, -1), (0, 1),
#             bat.heading,
#             (-1, -1), (-1, 1), (-1, 0),
#             (0, 0),
#         ]
#     else:
#         candidates = [
#             (dx, dy),
#             bat.heading,
#             (0, -1), (0, 1),
#             (1, -1), (1, 1), (1, 0),
#             (-1, -1), (-1, 1), (-1, 0),
#             (0, 0),
#         ]

#     seen = set()
#     ordered = []
#     for move in candidates:
#         if move not in seen:
#             seen.add(move)
#             ordered.append(move)
#     return ordered


# def choose_resolved_move(world, bat, preferred, reserved_next):
#     best = (bat.x, bat.y)
#     best_score = -1e9

#     for mdx, mdy in candidate_moves_for_bat(bat, preferred):
#         nx, ny = bat.x + mdx, bat.y + mdy

#         if not world.is_free(nx, ny):
#             continue
#         if (nx, ny) in reserved_next:
#             continue

#         score = 0.0

#         # prefer moving rather than staying
#         if (mdx, mdy) != (0, 0):
#             score += 0.2
#         else:
#             score -= 0.6

#         # prefer rightward progress in task 1
#         if world.cfg.task == 1:
#             score += 0.35 * mdx

#         # prefer cells with more local freedom
#         score += 0.18 * local_free_neighbors(world, nx, ny)

#         # mild persistence
#         if (mdx, mdy) == bat.heading:
#             score += 0.08

#         # if bat is jammed, strongly favor row changes
#         if getattr(bat, "stuck_steps", 0) >= 2 and mdy != 0:
#             score += 0.25

#         # tiny randomness to avoid permanent ties
#         score += random.uniform(-0.03, 0.03)

#         if score > best_score:
#             best_score = score
#             best = (nx, ny)

#     return best


# def draw(screen, cfg, world, bats, font, info_lines, camera_x, camera_y):
#     screen.fill((12, 12, 18))

#     for y in range(world.h):
#         sy = y * cfg.cell_px - camera_y
#         if sy < -cfg.cell_px or sy > cfg.window_h:
#             continue
#         for x in range(world.w):
#             sx = x * cfg.cell_px - camera_x
#             if sx < -cfg.cell_px or sx > cfg.window_w:
#                 continue
#             if world.obstacles[y, x] == 1:
#                 pygame.draw.rect(screen, (55, 55, 65), (sx, sy, cfg.cell_px, cfg.cell_px))

#     if cfg.task == 1:
#         pygame.draw.rect(
#             screen,
#             (20, 70, 20),
#             (
#                 world.outside_x0 * cfg.cell_px - camera_x,
#                 -camera_y,
#                 (world.w - world.outside_x0) * cfg.cell_px,
#                 world.h * cfg.cell_px,
#             ),
#         )

#     if cfg.task == 2:
#         for (x, y) in world.prey:
#             sx = x * cfg.cell_px - camera_x
#             sy = y * cfg.cell_px - camera_y
#             if -cfg.cell_px <= sx <= cfg.window_w and -cfg.cell_px <= sy <= cfg.window_h:
#                 pygame.draw.rect(
#                     screen,
#                     (220, 220, 90),
#                     (sx + 2, sy + 2, max(2, cfg.cell_px - 4), max(2, cfg.cell_px - 4)),
#                 )

#         px, py = world.predator_pos
#         pygame.draw.circle(
#             screen,
#             (200, 80, 80),
#             (px * cfg.cell_px + cfg.cell_px // 2 - camera_x,
#              py * cfg.cell_px + cfg.cell_px // 2 - camera_y),
#             cfg.predator_radius * cfg.cell_px,
#             width=2,
#         )

#     for b in bats:
#         cx = b.x * cfg.cell_px + cfg.cell_px // 2 - camera_x
#         cy = b.y * cfg.cell_px + cfg.cell_px // 2 - camera_y

#         if cx < -20 or cx > cfg.window_w + 20 or cy < -20 or cy > cfg.window_h + 20:
#             continue

#         if world.step_count - getattr(b, "last_ping_step", -999) <= 3:
#             ping_color = (255, 100, 100) if isinstance(b, LLMBat) else (120, 180, 255)
#             for r in [10, 18, 26]:
#                 pygame.draw.circle(screen, ping_color, (cx, cy), r, width=1)

#         color = (100, 220, 100) if getattr(b, "done", False) else (
#             (220, 70, 70) if isinstance(b, LLMBat) else (210, 210, 225)
#         )

#         pygame.draw.circle(screen, color, (cx, cy), max(2, cfg.cell_px // 3))

#         hx, hy = getattr(b, "heading", (1, 0))
#         tip_x = cx + hx * 8
#         tip_y = cy + hy * 8
#         pygame.draw.line(screen, (255, 255, 255), (cx, cy), (tip_x, tip_y), 2)

#     y0 = 8
#     for line in info_lines:
#         surf = font.render(line, True, (235, 235, 235))
#         screen.blit(surf, (8, y0))
#         y0 += 20


# def main():
#     cfg = SimConfig()
#     if len(sys.argv) >= 2:
#         cfg.task = int(sys.argv[1])

#     random.seed(0)
#     pygame.init()
#     os.makedirs("frames", exist_ok=True)
#     os.makedirs("gifs", exist_ok=True)

#     record_gif = True
#     saved_frames = []
#     screen = pygame.display.set_mode((cfg.window_w, cfg.window_h))
#     pygame.display.set_caption("Bat Stigmergy Swarm")
#     clock = pygame.time.Clock()
#     font = pygame.font.SysFont("consolas", 18)

#     world = World(cfg, seed=0)
#     client = LMStudioClient(cfg.llm_base_url, cfg.llm_model, cfg.llm_temperature)

#     bats = []
#     spawn_positions = clustered_spawn_positions(
#         world, cfg.n_bats, center_x=8, center_y=world.h // 2, radius=3
#     )

#     for i in range(cfg.n_llm_bats):
#         x, y = spawn_positions[i]
#         bats.append(LLMBat(x, y, client))

#     for i in range(cfg.n_llm_bats, cfg.n_bats):
#         x, y = spawn_positions[i]
#         bats.append(RuleBasedBat(x, y))

#     world.bats = bats
#     running = True
#     llm_last_rationale = ""

#     while running:
#         clock.tick(cfg.fps)

#         for event in pygame.event.get():
#             if event.type == pygame.QUIT:
#                 running = False

#         # LLM decision phase
#         if world.step_count % cfg.llm_decision_period == 0:
#             for b in bats:
#                 if isinstance(b, LLMBat) and not b.done:
#                     b.query_llm(world, cfg)

#         world.bat_positions = [(b.x, b.y) for b in bats if not getattr(b, "done", False)]

#         for b in bats:
#             if getattr(b, "done", False):
#                 continue
#             if b.should_ping(world):
#                 b.ping(world, cfg)

#         planned = []
#         for b in bats:
#             if getattr(b, "done", False):
#                 planned.append((b, (0, 0), "NONE", "done"))
#                 continue

#             if isinstance(b, LLMBat):
#                 action, call, rationale = b.act(world, cfg)
#                 if rationale:
#                     llm_last_rationale = rationale
#             else:
#                 action, call, rationale = b.act(world, cfg)

#             planned.append((b, action, call, rationale))

#         # Important: shuffle first so ties do not always go to same bats
#         random.shuffle(planned)

#         # Then prioritize LLM and jammed bats
#         resolution_order = sorted(
#             planned,
#             key=lambda item: (
#                 isinstance(item[0], LLMBat),
#                 getattr(item[0], "stuck_steps", 0)
#             ),
#             reverse=True
#         )

#         reserved_next = set()

#         for b, (dx, dy), call, rationale in resolution_order:
#             if getattr(b, "done", False):
#                 continue

#             old_x, old_y = b.x, b.y
#             chosen_x, chosen_y = choose_resolved_move(world, b, (dx, dy), reserved_next)

#             b.x, b.y = chosen_x, chosen_y
#             reserved_next.add((b.x, b.y))

#             moved = (b.x, b.y) != (old_x, old_y)

#             if moved:
#                 b.heading = (b.x - old_x, b.y - old_y)
#                 b.stuck_steps = 0
#             else:
#                 b.stuck_steps += 1
#                 b.score -= 0.15

#             if cfg.task == 1:
#                 if moved:
#                     b.score += 0.01
#                 else:
#                     b.score -= 0.02

#                 if hasattr(world, "outside_field"):
#                     b.score += 0.03 * float(world.outside_field[b.y, b.x])

#                 if b.x >= world.w - 3:
#                     b.done = True
#                     b.score += 50.0

#             if cfg.task == 2:
#                 if world.predator_risk(b.x, b.y) > 0:
#                     b.predator_events += 1
#                     b.score -= cfg.predator_penalty
#                     world.sound.deposit_alarm(b.x, b.y, cfg.alarm_deposit)

#                 if (b.x, b.y) in world.prey:
#                     world.prey.remove((b.x, b.y))
#                     b.prey_collected += 1
#                     b.score += cfg.prey_reward
#                     world.sound.deposit_buzz(b.x, b.y, cfg.buzz_deposit)

#                 if call == "BUZZ":
#                     world.sound.deposit_buzz(b.x, b.y, cfg.buzz_deposit * 0.5)
#                 elif call == "ALARM":
#                     world.sound.deposit_alarm(b.x, b.y, cfg.alarm_deposit * 0.5)

#         world.step()

#         if world.step_count >= cfg.max_steps:
#             running = False

#         if cfg.task == 1 and all(getattr(b, "done", False) for b in bats):
#             running = False

#         active_bats = [b for b in bats if not getattr(b, "done", False)]
#         if active_bats:
#             avg_x = sum(b.x for b in active_bats) / len(active_bats)
#             avg_y = sum(b.y for b in active_bats) / len(active_bats)
#         else:
#             avg_x = world.w / 2
#             avg_y = world.h / 2

#         camera_x = int(avg_x * cfg.cell_px - cfg.window_w // 3)
#         camera_y = int(avg_y * cfg.cell_px - cfg.window_h // 2)

#         camera_x = max(0, min(camera_x, cfg.grid_w * cfg.cell_px - cfg.window_w))
#         camera_y = max(0, min(camera_y, cfg.grid_h * cfg.cell_px - cfg.window_h))

#         total_score = sum(b.score for b in bats)
#         total_prey = sum(getattr(b, "prey_collected", 0) for b in bats)
#         total_pred = sum(getattr(b, "predator_events", 0) for b in bats)

#         info = [
#             f"Task={cfg.task}  Steps={world.step_count}/{cfg.max_steps}",
#             f"Score={total_score:.1f}  Prey={total_prey}  PredatorEvents={total_pred}",
#             f"LLM model={cfg.llm_model}  LLM bats={cfg.n_llm_bats}  Decision period={cfg.llm_decision_period}",
#             f"LLM rationale: {llm_last_rationale[:110]}",
#         ]

#         draw(screen, cfg, world, bats, font, info, camera_x, camera_y)
#         pygame.display.flip()



#         #===================================GIF RECORDING (optional)===================================
#         # if record_gif and world.step_count % 2 == 0:
#         #     frame_path = f"frames/frame_{world.step_count:05d}.png"
#         #     pygame.image.save(screen, frame_path)
#         #     saved_frames.append(frame_path)

#         # if record_gif and saved_frames:
#         #     images = [imageio.imread(fp) for fp in saved_frames]
#         #     gif_name = f"gifs/task_{cfg.task}_run.gif"
#         #     imageio.mimsave(gif_name, images, fps=12)
#         #     print(f"Saved GIF to {gif_name}")
#     pygame.quit()


# if __name__ == "__main__":
#     main()



import sys
from tkinter import font
import pygame
import random
import os
import imageio.v2 as imageio

from .batsim.config import SimConfig
from .batsim.world import World
from .batsim.agents import RuleBasedBat, LLMBat
from .llm.lm_studio_client import LMStudioClient

class Slider:
    def __init__(self, label, x, y, w, min_val, max_val, value, step=1):
        self.label = label
        self.rect = pygame.Rect(x, y, w, 8)
        self.knob_radius = 10
        self.min_val = min_val
        self.max_val = max_val
        self.value = value
        self.step = step
        self.dragging = False

    def value_to_pos(self):
        t = (self.value - self.min_val) / max(1e-9, (self.max_val - self.min_val))
        return int(self.rect.x + t * self.rect.w)

    def pos_to_value(self, mx):
        t = (mx - self.rect.x) / max(1, self.rect.w)
        t = max(0.0, min(1.0, t))
        raw = self.min_val + t * (self.max_val - self.min_val)
        if self.step >= 1:
            raw = round(raw / self.step) * self.step
        return int(raw) if self.step >= 1 else raw

    def handle_event(self, event):
        knob_x = self.value_to_pos()
        knob_rect = pygame.Rect(
            knob_x - self.knob_radius,
            self.rect.centery - self.knob_radius,
            self.knob_radius * 2,
            self.knob_radius * 2
        )

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if knob_rect.collidepoint(event.pos) or self.rect.inflate(0, 20).collidepoint(event.pos):
                self.dragging = True
                self.value = self.pos_to_value(event.pos[0])
                return True

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging = False

        elif event.type == pygame.MOUSEMOTION and self.dragging:
            self.value = self.pos_to_value(event.pos[0])
            return True

        return False

    def draw(self, screen, font, panel_color=(35, 35, 45)):
        # label
        label_surf = font.render(f"{self.label}: {self.value}", True, (240, 240, 240))
        screen.blit(label_surf, (self.rect.x, self.rect.y - 24))

        # line
        pygame.draw.rect(screen, (90, 90, 110), self.rect, border_radius=4)

        # fill
        fill_w = self.value_to_pos() - self.rect.x
        if fill_w > 0:
            pygame.draw.rect(
                screen,
                (120, 170, 255),
                pygame.Rect(self.rect.x, self.rect.y, fill_w, self.rect.h),
                border_radius=4
            )

        # knob
        knob_x = self.value_to_pos()
        pygame.draw.circle(screen, (230, 230, 240), (knob_x, self.rect.centery), self.knob_radius)
        pygame.draw.circle(screen, (60, 60, 80), (knob_x, self.rect.centery), self.knob_radius, width=2)

# def draw_ui_panel(screen, ui_font, sliders, apply_button, panel_x, panel_y, panel_w, panel_h):
#     panel_rect = pygame.Rect(panel_x, panel_y, panel_w, panel_h)
#     pygame.draw.rect(screen, (25, 25, 35), panel_rect, border_radius=12)
#     pygame.draw.rect(screen, (80, 80, 100), panel_rect, width=2, border_radius=12)

#     title = ui_font.render("Task Controls", True, (255, 255, 255))
#     screen.blit(title, (panel_x + 20, panel_y + 10))

#     for s in sliders:
#         s.draw(screen, ui_font)

#     apply_button.draw(screen, ui_font)


def draw_ui_panel(screen, ui_font, sliders, apply_button, panel_x, panel_y, panel_w, panel_h, scroll_y=0):
    panel_rect = pygame.Rect(panel_x, panel_y, panel_w, panel_h)
    pygame.draw.rect(screen, (25, 25, 35), panel_rect, border_radius=12)
    pygame.draw.rect(screen, (80, 80, 100), panel_rect, width=2, border_radius=12)

    title = ui_font.render("Task Controls", True, (255, 255, 255))
    screen.blit(title, (panel_x + 20, panel_y + 10))

    old_clip = screen.get_clip()
    inner_rect = pygame.Rect(panel_x + 8, panel_y + 40, panel_w - 16, panel_h - 48)
    screen.set_clip(inner_rect)

    for s in sliders:
        old_y = s.rect.y
        s.rect.y = old_y - scroll_y
        s.draw(screen, ui_font)
        s.rect.y = old_y

    old_btn_y = apply_button.rect.y
    apply_button.rect.y = old_btn_y - scroll_y
    apply_button.draw(screen, ui_font)
    apply_button.rect.y = old_btn_y

    screen.set_clip(old_clip)

class Button:
    def __init__(self, label, rect):
        self.label = label
        self.rect = pygame.Rect(rect)

    def handle_event(self, event):
        return event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.rect.collidepoint(event.pos)

    def draw(self, screen, font, bg=(70, 100, 70), fg=(255, 255, 255)):
        pygame.draw.rect(screen, bg, self.rect, border_radius=8)
        pygame.draw.rect(screen, (30, 30, 30), self.rect, width=2, border_radius=8)
        surf = font.render(self.label, True, fg)
        screen.blit(
            surf,
            (self.rect.centerx - surf.get_width() // 2, self.rect.centery - surf.get_height() // 2)
        )


# def spawn_positions_for_task(world, cfg):
#     if cfg.task == 1:
#         return clustered_spawn_positions(
#             world, cfg.n_bats, center_x=8, center_y=world.h // 2, radius=3
#         )

#     # Task 2: open-world spawn
#     positions = []
#     used = set()
#     tries = 0
#     while len(positions) < cfg.n_bats and tries < 20000:
#         tries += 1
#         x = random.randint(5, world.w - 6)
#         y = random.randint(3, world.h - 4)
#         if world.is_free(x, y) and (x, y) not in used:
#             positions.append((x, y))
#             used.add((x, y))

#     if len(positions) < cfg.n_bats:
#         raise RuntimeError(f"Could only place {len(positions)} bats out of {cfg.n_bats} in task 2.")

#     return positions

def spawn_positions_for_task(world, cfg):
    if cfg.task == 1:
        return clustered_spawn_positions(
            world, cfg.n_bats, center_x=8, center_y=world.h // 2, radius=3
        )

    # Task 2: clumped flock spawn with no touching
    positions = []
    used = set()
    tries = 0

    cx = world.w // 3
    cy = world.h // 2

    # put informed bat near center of flock first
    while len(positions) < cfg.n_bats and tries < 40000:
        tries += 1

        if len(positions) == 0:
            x, y = cx, cy
        else:
            x = int(round(random.gauss(cx, 7)))
            y = int(round(random.gauss(cy, 5)))

        if cfg.task == 2:
            x, y = world.wrap_xy(x, y)

        if not world.is_free(x, y):
            continue

        # prevent touching / overlap
        ok = True
        for ox, oy in used:
            dx = abs(x - ox)
            dy = abs(y - oy)
            if cfg.task == 2:
                dx = min(dx, world.w - dx)
                dy = min(dy, world.h - dy)
            if dx <= 1 and dy <= 1:
                ok = False
                break

        if ok:
            positions.append((x, y))
            used.add((x, y))

    if len(positions) < cfg.n_bats:
        raise RuntimeError(
            f"Could only place {len(positions)} bats out of {cfg.n_bats} in task 2."
        )

    return positions


def clustered_spawn_positions(world, n, center_x=8, center_y=None, radius=3):
    if center_y is None:
        center_y = world.h // 2

    positions = []
    used = set()

    tries = 0
    while len(positions) < n and tries < 4000:
        tries += 1
        x = random.randint(max(0, center_x - radius), min(world.w - 1, center_x + radius))
        y = random.randint(max(0, center_y - radius), min(world.h - 1, center_y + radius))
        if world.is_free(x, y) and (x, y) not in used:
            positions.append((x, y))
            used.add((x, y))

    tries = 0
    while len(positions) < n and tries < 10000:
        tries += 1
        x = random.randint(1, max(10, world.w // 4))
        y = random.randint(1, world.h - 2)
        if world.is_free(x, y) and (x, y) not in used:
            positions.append((x, y))
            used.add((x, y))

    if len(positions) < n:
        raise RuntimeError(
            f"Could only place {len(positions)} bats out of {n}. "
            f"Try reducing n_bats or increasing free cave space."
        )

    return positions


def local_free_neighbors(world, x, y):
    count = 0
    for dx, dy in [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]:
        nx, ny = x + dx, y + dy
        if world.is_free(nx, ny):
            count += 1
    return count


def candidate_moves_for_bat(bat, preferred):
    dx, dy = preferred

    if dx > 0:
        candidates = [
            (dx, dy),
            (1, -1), (1, 1), (1, 0),
            (0, -1), (0, 1),
            bat.heading,
            (-1, -1), (-1, 1), (-1, 0),
            (0, 0),
        ]
    else:
        candidates = [
            (dx, dy),
            bat.heading,
            (0, -1), (0, 1),
            (1, -1), (1, 1), (1, 0),
            (-1, -1), (-1, 1), (-1, 0),
            (0, 0),
        ]

    seen = set()
    ordered = []
    for move in candidates:
        if move not in seen:
            seen.add(move)
            ordered.append(move)
    return ordered


def choose_resolved_move(world, bat, preferred, reserved_next):
    best = (bat.x, bat.y)
    best_score = -1e9

    for mdx, mdy in candidate_moves_for_bat(bat, preferred):
        # nx, ny = world.wrap_xy(bat.x + mdx, bat.y + mdy) if world.cfg.task == 2 else (bat.x + mdx, bat.y + mdy)
        if world.cfg.task == 2:
            nx, ny = world.wrap_xy(bat.x + mdx, bat.y + mdy)
        else:
            nx, ny = bat.x + mdx, bat.y + mdy
        if not world.is_free(nx, ny):
            continue
        if (nx, ny) in reserved_next:
            continue

        score = 0.0
        if (mdx, mdy) == preferred:
            score += 2.0

        if isinstance(bat, LLMBat) and (mdx, mdy) == preferred:
            score += 4.0

        if (mdx, mdy) != (0, 0):
            score += 0.2
        else:
            score -= 0.6

        if world.cfg.task == 1:
            score += 0.35 * mdx

        score += 0.18 * local_free_neighbors(world, nx, ny)

        if (mdx, mdy) == bat.heading:
            score += 0.08

        if getattr(bat, "stuck_steps", 0) >= 2 and mdy != 0:
            score += 0.25

        score += random.uniform(-0.03, 0.03)

        if score > best_score:
            best_score = score
            best = (nx, ny)

    return best


def draw(screen, cfg, world, bats, font, info_lines, camera_x, camera_y):
    # background
    if cfg.task == 2:
        screen.fill((18, 48, 18))
    else:
        screen.fill((12, 12, 18))

    # task 2 open-world green field
    if cfg.task == 2:
        pygame.draw.rect(
            screen,
            (24, 85, 24),
            (0, 0, cfg.window_w, cfg.window_h),
        )

    # obstacles
    for y in range(world.h):
        sy = y * cfg.cell_px - camera_y
        if sy < -cfg.cell_px or sy > cfg.window_h:
            continue
        for x in range(world.w):
            sx = x * cfg.cell_px - camera_x
            if sx < -cfg.cell_px or sx > cfg.window_w:
                continue
            if world.obstacles[y, x] == 1:
                color = (45, 75, 35) if cfg.task == 2 else (55, 55, 65)
                pygame.draw.rect(screen, color, (sx, sy, cfg.cell_px, cfg.cell_px))

    # task 1 outside green zone
    if cfg.task == 1:
        pygame.draw.rect(
            screen,
            (20, 70, 20),
            (
                world.outside_x0 * cfg.cell_px - camera_x,
                -camera_y,
                (world.w - world.outside_x0) * cfg.cell_px,
                world.h * cfg.cell_px,
            ),
        )

    # prey / predator
    if cfg.task == 2:
        for (x, y) in world.prey:
            sx = x * cfg.cell_px - camera_x
            sy = y * cfg.cell_px - camera_y
            if -cfg.cell_px <= sx <= cfg.window_w and -cfg.cell_px <= sy <= cfg.window_h:
                pygame.draw.rect(
                    screen,
                    (255, 230, 90),
                    (sx + 2, sy + 2, max(2, cfg.cell_px - 4), max(2, cfg.cell_px - 4)),
                )

        # px, py = world.predator_pos
        # pygame.draw.circle(
        #     screen,
        #     (120, 20, 20),
        #     (px * cfg.cell_px + cfg.cell_px // 2 - camera_x,
        #     py * cfg.cell_px + cfg.cell_px // 2 - camera_y),
        #     max(10, cfg.predator_radius * cfg.cell_px),
        #     width=2,
        # )

        # predator

        for pred in getattr(world, "predators", []):
            px, py = pred["pos"]
            pcx = px * cfg.cell_px + cfg.cell_px // 2 - camera_x
            pcy = py * cfg.cell_px + cfg.cell_px // 2 - camera_y
            pr = max(12, cfg.predator_radius * cfg.cell_px)

            pygame.draw.polygon(
                screen,
                (110, 20, 20),
                [(pcx - pr, pcy), (pcx - pr // 3, pcy - pr // 2), (pcx - pr // 3, pcy + pr // 2)]
            )
            pygame.draw.polygon(
                screen,
                (110, 20, 20),
                [(pcx + pr, pcy), (pcx + pr // 3, pcy - pr // 2), (pcx + pr // 3, pcy + pr // 2)]
            )

            pygame.draw.circle(screen, (170, 30, 30), (pcx, pcy), pr // 2)
            pygame.draw.circle(screen, (60, 10, 10), (pcx, pcy), pr // 2, width=2)
        # px, py = world.predator_pos
        # pcx = px * cfg.cell_px + cfg.cell_px // 2 - camera_x
        # pcy = py * cfg.cell_px + cfg.cell_px // 2 - camera_y
        # pr = max(12, cfg.predator_radius * cfg.cell_px)

        # # wings
        # pygame.draw.polygon(
        #     screen,
        #     (110, 20, 20),
        #     [(pcx - pr, pcy), (pcx - pr // 3, pcy - pr // 2), (pcx - pr // 3, pcy + pr // 2)]
        # )
        # pygame.draw.polygon(
        #     screen,
        #     (110, 20, 20),
        #     [(pcx + pr, pcy), (pcx + pr // 3, pcy - pr // 2), (pcx + pr // 3, pcy + pr // 2)]
        # )

        # # body
        # pygame.draw.circle(screen, (170, 30, 30), (pcx, pcy), pr // 2)
        # pygame.draw.circle(screen, (60, 10, 10), (pcx, pcy), pr // 2, width=2)

    # bats
    for b in bats:
        if not getattr(b, "visible", True):
            continue
        cx = b.x * cfg.cell_px + cfg.cell_px // 2 - camera_x
        cy = b.y * cfg.cell_px + cfg.cell_px // 2 - camera_y

        if cx < -20 or cx > cfg.window_w + 20 or cy < -20 or cy > cfg.window_h + 20:
            continue

        if world.step_count - getattr(b, "last_ping_step", -999) <= 3:
            ping_color = (255, 100, 100) if isinstance(b, LLMBat) else (120, 180, 255)
            for r in [10, 18, 26]:
                pygame.draw.circle(screen, ping_color, (cx, cy), r, width=1)

        # color = (100, 220, 100) if getattr(b, "done", False) else (
        #     (220, 70, 70) if isinstance(b, LLMBat) else (210, 210, 225)
        # )
        if getattr(b, "dying", False):
            fade_ratio = max(0.0, b.fade_ticks / max(1, b.fade_total))
            color = (
                int(180 * fade_ratio),
                int(60 * fade_ratio),
                int(60 * fade_ratio),
            )
            bat_radius = max(1, int(max(2, cfg.cell_px // 3) * fade_ratio))
        elif getattr(b, "done", False):
            color = (100, 220, 100)
            bat_radius = max(2, cfg.cell_px // 3)
        else:
            color = (220, 70, 70) if isinstance(b, LLMBat) else (210, 210, 225)
            bat_radius = max(2, cfg.cell_px // 3)

        # pygame.draw.circle(screen, color, (cx, cy), max(2, cfg.cell_px // 3))

        pygame.draw.circle(screen, color, (cx, cy), bat_radius)
        hx, hy = getattr(b, "heading", (1, 0))
        tip_x = cx + hx * 8
        tip_y = cy + hy * 8
        pygame.draw.line(screen, (255, 255, 255), (cx, cy), (tip_x, tip_y), 2)
        
        # show recent social calls in Task 2

        # show recent social calls in Task 2
        if cfg.task == 2 and world.step_count - getattr(b, "last_call_step", -999) <= 8:
            call_type = getattr(b, "last_call_type", "NONE")

            if isinstance(b, LLMBat):
                # LLM-specific palette
                if call_type == "BUZZ":
                    call_color = (255, 170, 60)   # orange-gold for LLM buzz
                    radii = [16, 26, 36]
                elif call_type == "ALARM":
                    call_color = (120, 220, 255)  # cyan-blue for LLM alarm
                    radii = [18, 30, 42]
                else:
                    call_color = None
                    radii = []
            else:
                # Rule-based palette
                if call_type == "BUZZ":
                    call_color = (255, 230, 90)   # yellow
                    radii = [14, 22]
                elif call_type == "ALARM":
                    call_color = (170, 90, 255)   # purple
                    radii = [16, 26, 36]
                else:
                    call_color = None
                    radii = []

            if call_color is not None:
                for r in radii:
                    pygame.draw.circle(screen, call_color, (cx, cy), r, width=2)
        # if cfg.task == 2 and world.step_count - getattr(b, "last_call_step", -999) <= 6:
        #     if getattr(b, "last_call_type", "NONE") == "BUZZ":
        #         call_color = (255, 230, 90)   # bright yellow
        #         radii = [14, 22]
        #     elif getattr(b, "last_call_type", "NONE") == "ALARM":
        #         call_color = (170, 90, 255)   # alarm color (purple, non-red)
        #         radii = [16, 26, 50]
        #     else:
        #         call_color = None
        #         radii = []

        #     if call_color is not None:
        #         for r in radii:
        #             pygame.draw.circle(screen, call_color, (cx, cy), r, width=2)    
    y0 = 8
    for line in info_lines:
        surf = font.render(line, True, (235, 235, 235))
        screen.blit(surf, (8, y0))
        y0 += 20


def build_world_and_bats(cfg, client):
    world = World(cfg, seed=random.randint(0, 999999))
    bats = []
    spawn_positions = spawn_positions_for_task(world, cfg)

    for i in range(cfg.n_llm_bats):
        x, y = spawn_positions[i]
        bats.append(LLMBat(x, y, client))

    for i in range(cfg.n_llm_bats, cfg.n_bats):
        x, y = spawn_positions[i]
        bats.append(RuleBasedBat(x, y))

    world.bats = bats
    return world, bats


def main():
    cfg = SimConfig()
    if len(sys.argv) >= 2:
        cfg.task = int(sys.argv[1])

    random.seed(0)
    pygame.init()
    os.makedirs("frames", exist_ok=True)
    os.makedirs("gifs", exist_ok=True)

    record_gif = False
    saved_frames = []

    screen = pygame.display.set_mode((cfg.window_w, cfg.window_h))
    pygame.display.set_caption("Bat Stigmergy Swarm")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("consolas", 18)
    client = LMStudioClient(cfg.llm_base_url, cfg.llm_model, cfg.llm_temperature)
    world, bats = build_world_and_bats(cfg, client)
    # world = World(cfg, seed=0)
    # client = LMStudioClient(cfg.llm_base_url, cfg.llm_model, cfg.llm_temperature)

    # bats = []
    # spawn_positions = spawn_positions_for_task(world, cfg)

    # for i in range(cfg.n_llm_bats):
    #     x, y = spawn_positions[i]
    #     bats.append(LLMBat(x, y, client))

    # for i in range(cfg.n_llm_bats, cfg.n_bats):
    #     x, y = spawn_positions[i]
    #     bats.append(RuleBasedBat(x, y))
    ui_font = pygame.font.SysFont("consolas", 16)

    panel_x = cfg.window_w - 260
    panel_y = 20
    panel_w = 240
    panel_h = 250

    sliders = [
        Slider("Bats", panel_x + 20, panel_y + 40, 180, 4, 60, cfg.n_bats, step=1),
        Slider("LLM Bats", panel_x + 20, panel_y + 95, 180, 1, 8, cfg.n_llm_bats, step=1),
        Slider("Prey", panel_x + 20, panel_y + 150, 180, 10, 200, cfg.n_prey, step=5),
        Slider("Pred Radius", panel_x + 20, panel_y + 205, 180, 2, 20, cfg.predator_radius, step=1),
        # Slider("Predators", panel_x + 20, panel_y + 260, 180, 1, 6, getattr(cfg, "n_predators", 1), step=1),
        Slider("Predators", panel_x + 20, panel_y + 260, 180, 1, 6, cfg.n_predators, step=1),
        Slider("Pred Speed", panel_x + 20, panel_y + 330, 180, 1, 6, cfg.predator_move_period, step=1),
    ]

    apply_button = Button("Apply / Reset", (panel_x + 20, panel_y + 235, 180, 34))
    world.bats = bats
    running = True
    show_hud = True
    show_controls = True
    llm_last_rationale = ""

    while running:
        clock.tick(cfg.fps)

        for event in pygame.event.get():

            if event.type == pygame.MOUSEWHEEL and show_controls:
                panel_scroll_y -= event.y * 30
                panel_scroll_y = max(0, min(panel_scroll_y, 400))
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_h:
                    show_hud = not show_hud
                elif event.key == pygame.K_TAB:
                    show_controls = not show_controls


            if event.type == pygame.QUIT:
                running = False
            # for s in sliders:
            #     s.handle_event(event)

            # if apply_button.handle_event(event):


            if show_controls:
                for s in sliders:
                    s.handle_event(event)

                if apply_button.handle_event(event):
                        
                    # push slider values into config
                    cfg.n_bats = int(sliders[0].value)
                    cfg.n_llm_bats = min(int(sliders[1].value), cfg.n_bats)
                    sliders[1].value = cfg.n_llm_bats  # keep UI consistent
                    cfg.n_prey = int(sliders[2].value)
                    cfg.predator_radius = int(sliders[3].value)
                    cfg.n_predators = int(sliders[4].value)
                    # rebuild sim
                    world, bats = build_world_and_bats(cfg, client)
                    llm_last_rationale = ""


        # fade out dead bats
        for b in bats:
            if getattr(b, "dying", False):
                b.fade_ticks -= 1
                if b.fade_ticks <= 0:
                    b.dying = False
                    b.visible = False


        # decay temporary prey recruitment state
        for b in bats:
            if getattr(b, "recruited_ticks", 0) > 0:
                b.recruited_ticks -= 1

        for b in bats:
            if getattr(b, "follow_leader_ticks", 0) > 0:
                b.follow_leader_ticks -= 1
                if b.follow_leader_ticks <= 0:
                    b.leader_mode = "NONE"



        if world.step_count % cfg.llm_decision_period == 0:
            for b in bats:
                if isinstance(b, LLMBat) and not b.done:
                    b.query_llm(world, cfg)

        world.bat_positions = [(b.x, b.y) for b in bats if not getattr(b, "done", False)]

        for b in bats:
            if getattr(b, "done", False):
                continue
            if b.should_ping(world):
                b.ping(world, cfg)

        planned = []
        for b in bats:
            if getattr(b, "done", False):
                planned.append((b, (0, 0), "NONE", "done"))
                continue

            if isinstance(b, LLMBat):
                action, call, rationale = b.act(world, cfg)
                if rationale:
                    llm_last_rationale = rationale
            else:
                action, call, rationale = b.act(world, cfg)

            planned.append((b, action, call, rationale))

        random.shuffle(planned)

        resolution_order = sorted(
            planned,
            key=lambda item: (
                isinstance(item[0], LLMBat),
                getattr(item[0], "stuck_steps", 0)
            ),
            reverse=True
        )

        reserved_next = set()

        for b, (dx, dy), call, rationale in resolution_order:
            if getattr(b, "done", False):
                continue

            old_x, old_y = b.x, b.y
            chosen_x, chosen_y = choose_resolved_move(world, b, (dx, dy), reserved_next)
            applied_dx = chosen_x - old_x
            applied_dy = chosen_y - old_y
            
            
            
            # if isinstance(b, LLMBat):
                # print(f"LLM wanted {(dx, dy)} but applied {(applied_dx, applied_dy)}")
            b.x, b.y = chosen_x, chosen_y
            reserved_next.add((b.x, b.y))

            moved = (b.x, b.y) != (old_x, old_y)

            if moved:
                b.heading = (b.x - old_x, b.y - old_y)
                b.stuck_steps = 0
            else:
                b.stuck_steps += 1
                b.score -= 0.15

            if cfg.task == 1:
                if moved:
                    b.score += 0.01
                else:
                    b.score -= 0.02

                if hasattr(world, "outside_field"):
                    b.score += 0.03 * float(world.outside_field[b.y, b.x])

                outside_success_x = world.outside_x0 + 12
                if b.x >= outside_success_x:
                    b.done = True
                    b.score += 50.0
            # if cfg.task == 2:
            #     px, py = world.predator_pos
            #     dxp = abs(b.x - px)
            #     dyp = abs(b.y - py)
            #     dxp = min(dxp, world.w - dxp) if cfg.task == 2 else dxp
            #     dyp = min(dyp, world.h - dyp) if cfg.task == 2 else dyp


            if cfg.task == 2:
                nearest_pred = None
                nearest_d2 = 10**9

                for pred in getattr(world, "predators", []):
                    px, py = pred["pos"]
                    dxp = abs(b.x - px)
                    dyp = abs(b.y - py)
                    dxp = min(dxp, world.w - dxp)
                    dyp = min(dyp, world.h - dyp)
                    d2 = dxp * dxp + dyp * dyp

                    if d2 < nearest_d2:
                        nearest_d2 = d2
                        nearest_pred = (px, py, dxp, dyp)

                if nearest_pred is not None:
                    px, py, dxp, dyp = nearest_pred

                # if dxp * dxp + dyp * dyp <= max(2, cfg.predator_radius // 2) ** 2:
                #     b.alive = False
                #     b.done = True
                #     b.score -= 200.0
                #     if isinstance(b, LLMBat):
                #         llm_last_rationale = "LLM bat died to predator."
                #     continue

                if dxp * dxp + dyp * dyp <= max(2, cfg.predator_radius // 2) ** 2:
                    if b.alive:
                        b.alive = False
                        b.done = True
                        b.dying = True
                        b.fade_total = 24
                        b.fade_ticks = b.fade_total
                        b.score -= 120.0
                        if isinstance(b, LLMBat):
                            llm_last_rationale = "LLM bat died to predator."
                    continue
                
            if cfg.task == 2:
                if world.predator_risk(b.x, b.y) > 0:
                    b.predator_events += 1
                    b.score -= cfg.predator_penalty
                    world.sound.deposit_alarm(b.x, b.y, cfg.alarm_deposit)

                caught_prey = None
                for px2, py2 in list(world.prey):
                    dxp2 = abs(b.x - px2)
                    dyp2 = abs(b.y - py2)
                    if cfg.task == 2:
                        dxp2 = min(dxp2, world.w - dxp2)
                        dyp2 = min(dyp2, world.h - dyp2)

                    # small capture radius instead of exact overlap
                    if dxp2 * dxp2 + dyp2 * dyp2 <= 5:
                        caught_prey = (px2, py2)
                        break

                if caught_prey is not None:
                    world.prey.remove(caught_prey)
                    b.prey_collected += 1
                    b.score += cfg.prey_reward
                    b.hungry = False
                    world.sound.deposit_buzz(b.x, b.y, cfg.buzz_deposit)
                    b.recruited_ticks = 0
                    b.follow_leader_ticks = 0
                    b.leader_mode = "NONE"

            if cfg.task == 2 and world.step_count % 10 == 0:
                # print("Predator:", world.predator_pos)
                for i, b in enumerate(bats[:5]):
                    print(f"Bat {i}: {(b.x, b.y)}")
                # if call == "BUZZ":
                #     world.sound.deposit_buzz(b.x, b.y, cfg.buzz_deposit * 0.5)
                # elif call == "ALARM":
                #     world.sound.deposit_alarm(b.x, b.y, cfg.alarm_deposit * 0.5)


                # if call == "BUZZ":
                #     world.sound.deposit_buzz(b.x, b.y, cfg.buzz_deposit * 0.75)
                #     b.last_call_step = world.step_count
                #     b.last_call_type = "BUZZ"
                # elif call == "ALARM":
                #     world.sound.deposit_alarm(b.x, b.y, cfg.alarm_deposit * 0.75)
                #     b.last_call_step = world.step_count
                #     b.last_call_type = "ALARM"
                # else:
                #     b.last_call_type = "NONE"

                if call == "BUZZ":
                    world.sound.deposit_buzz(b.x, b.y, cfg.buzz_deposit * 0.75)
                    b.last_call_step = world.step_count
                    b.last_call_type = "BUZZ"

                    # informed leader recruits nearby hungry bats
                    if isinstance(b, LLMBat):
                        for other in bats:
                            if other is b or getattr(other, "done", False) or not getattr(other, "alive", True):
                                continue
                            if not getattr(other, "hungry", True):
                                continue

                            dxh = abs(other.x - b.x)
                            dyh = abs(other.y - b.y)
                            if cfg.task == 2:
                                dxh = min(dxh, world.w - dxh)
                                dyh = min(dyh, world.h - dyh)

                            if dxh + dyh <= 14:
                                other.follow_leader_ticks = 30
                                other.leader_mode = "BUZZ"
                                other.recruited_ticks = 20

                elif call == "ALARM":
                    world.sound.deposit_alarm(b.x, b.y, cfg.alarm_deposit * 1.0)
                    b.last_call_step = world.step_count
                    b.last_call_type = "ALARM"

                    # informed leader recruits nearby bats into coordinated escape
                    if isinstance(b, LLMBat):
                        for other in bats:
                            if other is b or getattr(other, "done", False) or not getattr(other, "alive", True):
                                continue

                            dxh = abs(other.x - b.x)
                            dyh = abs(other.y - b.y)
                            if cfg.task == 2:
                                dxh = min(dxh, world.w - dxh)
                                dyh = min(dyh, world.h - dyh)

                            if dxh + dyh <= 16:
                                other.follow_leader_ticks = 24
                                other.leader_mode = "ALARM"
                                other.recruited_ticks = 0

                    # informed leader recruits nearby bats into coordinated escape
                    if isinstance(b, LLMBat):
                        for other in bats:
                            if other is b or getattr(other, "done", False) or not getattr(other, "alive", True):
                                continue

                            dxh = abs(other.x - b.x)
                            dyh = abs(other.y - b.y)
                            if cfg.task == 2:
                                dxh = min(dxh, world.w - dxh)
                                dyh = min(dyh, world.h - dyh)

                            if dxh + dyh <= 16:
                                other.follow_leader_ticks = 24
                                other.leader_mode = "ALARM"
                else:
                    b.last_call_type = "NONE"
        world.step()

        if world.step_count >= cfg.max_steps:
            running = False

        if cfg.task == 1 and all(getattr(b, "done", False) for b in bats):
            running = False

        if cfg.task == 2:
            camera_x = 0
            camera_y = 0
        else:
            active_bats = [b for b in bats if not getattr(b, "done", False)]
            if active_bats:
                avg_x = sum(b.x for b in active_bats) / len(active_bats)
                avg_y = sum(b.y for b in active_bats) / len(active_bats)
            else:
                avg_x = world.w / 2
                avg_y = world.h / 2

            if cfg.task == 2:
                camera_x = 0
                camera_y = 0
            else:
                camera_x = int(avg_x * cfg.cell_px - cfg.window_w // 3)
                camera_y = int(avg_y * cfg.cell_px - cfg.window_h // 2)

                camera_x = max(0, min(camera_x, cfg.grid_w * cfg.cell_px - cfg.window_w))
                camera_y = max(0, min(camera_y, cfg.grid_h * cfg.cell_px - cfg.window_h))

        total_score = sum(b.score for b in bats)
        total_prey = sum(getattr(b, "prey_collected", 0) for b in bats)
        total_pred = sum(getattr(b, "predator_events", 0) for b in bats)

        buzz_calls = sum(1 for b in bats if getattr(b, "last_call_type", "NONE") == "BUZZ")
        alarm_calls = sum(1 for b in bats if getattr(b, "last_call_type", "NONE") == "ALARM")
        initial_prey = cfg.n_prey
        prey_left = len(world.prey)
        prey_eaten = initial_prey - prey_left

        total_bats = len(bats)
        alive_bats = sum(1 for b in bats if getattr(b, "alive", True))
        dead_bats = total_bats - alive_bats

        llm_bats = [b for b in bats if isinstance(b, LLMBat)]
        llm_total = len(llm_bats)
        llm_alive = sum(1 for b in llm_bats if getattr(b, "alive", True))
        llm_dead = llm_total - llm_alive

        predator_count = getattr(cfg, "n_predators", 1)

        llm_bat = next((b for b in bats if isinstance(b, LLMBat)), None)
        llm_mode = llm_bat.llm_mode if llm_bat else "N/A"
        llm_call = llm_bat.last_call_type if llm_bat else "N/A"
        info = [
            f"Task={cfg.task}  Steps={world.step_count}/{cfg.max_steps}",
            f"Prey total={initial_prey}  eaten={prey_eaten}  left={prey_left}",
            f"Bats total={total_bats}  dead={dead_bats}  alive={alive_bats}",
            f"LLM bats total={llm_total}  dead={llm_dead}  alive={llm_alive}",
            f"Predators={predator_count}",
            f"Score={total_score:.1f}  PreyCollected={total_prey}  PredatorEvents={total_pred}",
            f"ActivePrey={len(world.prey)}  Predators={len(getattr(world, 'predators', []))}",
            f"BuzzCalls={buzz_calls}  AlarmCalls={alarm_calls}",
            f"LLM model={cfg.llm_model}  LLM bats={cfg.n_llm_bats}  Decision period={cfg.llm_decision_period}",
            f"LLM rationale: {llm_last_rationale[:110]}",
            # f"LLM mode={next((b.llm_mode for b in bats if isinstance(b, LLMBat)), 'N/A')}",
            f"LLM mode={llm_mode}  LLM call={llm_call}",
        ]
        # draw(screen, cfg, world, bats, font, info, camera_x, camera_y)
        panel_scroll_y = 0
        draw(screen, cfg, world, bats, font, info if show_hud else [], camera_x, camera_y)
        if cfg.task == 2:
            if show_controls:

                # draw_ui_panel(screen, ui_font, sliders, apply_button, panel_x, panel_y, panel_w, panel_h)
                draw_ui_panel(screen, ui_font, sliders, apply_button, panel_x, panel_y, panel_w, panel_h, panel_scroll_y)
        pygame.display.flip()

        if record_gif and world.step_count % 2 == 0:
            frame_path = f"frames/frame_{world.step_count:05d}.png"
            pygame.image.save(screen, frame_path)
            saved_frames.append(frame_path)

    if record_gif and saved_frames:
        images = [imageio.imread(fp) for fp in saved_frames]
        gif_name = f"gifs/task_{cfg.task}_run.gif"
        imageio.mimsave(gif_name, images, fps=12)
        print(f"Saved GIF to {gif_name}")

    pygame.quit()


if __name__ == "__main__":

    main()