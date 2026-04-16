# import sys
# import pygame
# import random

# from .batsim.config import SimConfig
# from .batsim.world import World
# from .batsim.agents import RuleBasedBat, LLMBat
# from .llm.lm_studio_client import LMStudioClient

# def draw(screen, cfg: SimConfig, world: World, bats, font, info_lines):
#     screen.fill((10, 10, 14))

#     # obstacles
#     for y in range(world.h):
#         for x in range(world.w):
#             if world.obstacles[y, x] == 1:
#                 pygame.draw.rect(
#                     screen, (60, 60, 70),
#                     (x * cfg.cell_px, y * cfg.cell_px, cfg.cell_px, cfg.cell_px)
#                 )

#     # exit region (Task 1)
#     if cfg.task == 1:
#         pygame.draw.rect(
#             screen, (20, 40, 20),
#             (world.exit_x0 * cfg.cell_px, 0, cfg.exit_width * cfg.cell_px, world.h * cfg.cell_px),
#             width=0
#         )

#     # prey (Task 2)
#     if cfg.task == 2:
#         for (x, y) in world.prey:
#             pygame.draw.rect(
#                 screen, (220, 220, 90),
#                 (x * cfg.cell_px + 2, y * cfg.cell_px + 2, cfg.cell_px - 4, cfg.cell_px - 4)
#             )
#         # predator center
#         px, py = world.predator_pos
#         pygame.draw.circle(
#             screen, (200, 80, 80),
#             (px * cfg.cell_px + cfg.cell_px // 2, py * cfg.cell_px + cfg.cell_px // 2),
#             cfg.predator_radius * cfg.cell_px,
#             width=2
#         )

#     # bats
#     for i, b in enumerate(bats):
#         color = (80, 200, 240) if isinstance(b, LLMBat) else (200, 200, 220)
#         pygame.draw.circle(
#             screen, color,
#             (b.x * cfg.cell_px + cfg.cell_px // 2, b.y * cfg.cell_px + cfg.cell_px // 2),
#             max(2, cfg.cell_px // 3)
#         )

#     # info text
#     y0 = 5
#     for line in info_lines:
#         surf = font.render(line, True, (230, 230, 230))
#         screen.blit(surf, (5, y0))
#         y0 += 18


# def main():
#     cfg = SimConfig()
#     # allow task selection: python -m src.main 1 or 2
#     if len(sys.argv) >= 2:
#         cfg.task = int(sys.argv[1])

#     random.seed(0)

#     pygame.init()
#     screen = pygame.display.set_mode((cfg.grid_w * cfg.cell_px, cfg.grid_h * cfg.cell_px))
#     pygame.display.set_caption("Bat Stigmergy Swarm (MVP)")
#     clock = pygame.time.Clock()
#     font = pygame.font.SysFont("consolas", 16)

#     world = World(cfg, seed=0)

#     # spawn bats
#     bats = []
#     client = LMStudioClient(cfg.llm_base_url, cfg.llm_model, cfg.llm_temperature)

#     def random_free_pos():
#         while True:
#             x = random.randrange(0, world.w // 2)
#             y = random.randrange(0, world.h)
#             if world.is_free(x, y):
#                 return x, y

#     # LLM bats first
#     for _ in range(cfg.n_llm_bats):
#         x, y = random_free_pos()
#         bats.append(LLMBat(x, y, client))

#     # rule-based bats
#     for _ in range(cfg.n_bats - cfg.n_llm_bats):
#         x, y = random_free_pos()
#         bats.append(RuleBasedBat(x, y))

#     running = True
#     llm_last_rationale = ""

#     while running:
#         clock.tick(cfg.fps)

#         for event in pygame.event.get():
#             if event.type == pygame.QUIT:
#                 running = False

#         # STEP: act + move
#         for b in bats:
#             if isinstance(b, LLMBat):
#                 (dx, dy), call, rationale = b.act(world, cfg)
#                 if rationale:
#                     llm_last_rationale = rationale
#             else:
#                 (dx, dy), call = b.act(world, cfg)

#             nx, ny = b.x + dx, b.y + dy
#             if world.is_free(nx, ny):
#                 b.x, b.y = nx, ny

#             # Task 1: exit check
#             # if cfg.task == 1 and world.is_exit(b.x):
#             #     b.score += 1.0
#             # small incentive to move (Task 1)
#             if cfg.task == 1 and (dx, dy) != (0, 0):
#                 b.score += 0.01
#             if cfg.task == 1 and world.is_exit(b.x):
#                 b.score += 100.0
#                 b.done = True
#             # Task 2: prey/predator + soundscape deposit
#             if cfg.task == 2:
#                 # predator event
#                 if world.predator_risk(b.x, b.y) > 0:
#                     b.predator_events += 1
#                     b.score -= cfg.predator_penalty
#                     world.sound.deposit_alarm(b.x, b.y, cfg.alarm_deposit)

#                 # prey capture
#                 if (b.x, b.y) in world.prey:
#                     world.prey.remove((b.x, b.y))
#                     b.prey_collected += 1
#                     b.score += cfg.prey_reward
#                     world.sound.deposit_buzz(b.x, b.y, cfg.buzz_deposit)

#                 # optional call deposits
#                 if call == "BUZZ":
#                     world.sound.deposit_buzz(b.x, b.y, cfg.buzz_deposit * 0.5)
#                 elif call == "ALARM":
#                     world.sound.deposit_alarm(b.x, b.y, cfg.alarm_deposit * 0.5)

#         world.step()

#         # HUD
#         total_score = sum(b.score for b in bats)
#         total_prey = sum(getattr(b, "prey_collected", 0) for b in bats)
#         total_pred = sum(getattr(b, "predator_events", 0) for b in bats)

#         info = [
#             f"Task={cfg.task}  Steps={world.step_count}",
#             f"Total score={total_score:.1f}  Prey={total_prey}  PredatorEvents={total_pred}",
#             f"LLM model={cfg.llm_model}  LLM bats={cfg.n_llm_bats}  LLM period={cfg.llm_decision_period}",
#             f"LLM rationale: {llm_last_rationale[:80]}",
#             "Press [X] close window to quit.",
#         ]

#         draw(screen, cfg, world, bats, font, info)
#         pygame.display.flip()
#         if world.step_count >= cfg.max_steps:
#             running = False 

#     pygame.quit()


# if __name__ == "__main__":
#     main()
import sys
import pygame
import random
import os
import imageio.v2 as imageio


from .batsim.config import SimConfig
from .batsim.world import World
from .batsim.agents import RuleBasedBat, LLMBat
from .llm.lm_studio_client import LMStudioClient


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
        x = random.randint(1, max(10, world.outside_x0 // 4))
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

    # More diverse fallback ordering to reduce pileups
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
        nx, ny = bat.x + mdx, bat.y + mdy

        if not world.is_free(nx, ny):
            continue
        if (nx, ny) in reserved_next:
            continue

        score = 0.0

        # prefer moving rather than staying
        if (mdx, mdy) != (0, 0):
            score += 0.2
        else:
            score -= 0.6

        # prefer rightward progress in task 1
        if world.cfg.task == 1:
            score += 0.35 * mdx

        # prefer cells with more local freedom
        score += 0.18 * local_free_neighbors(world, nx, ny)

        # mild persistence
        if (mdx, mdy) == bat.heading:
            score += 0.08

        # if bat is jammed, strongly favor row changes
        if getattr(bat, "stuck_steps", 0) >= 2 and mdy != 0:
            score += 0.25

        # tiny randomness to avoid permanent ties
        score += random.uniform(-0.03, 0.03)

        if score > best_score:
            best_score = score
            best = (nx, ny)

    return best


def draw(screen, cfg, world, bats, font, info_lines, camera_x, camera_y):
    screen.fill((12, 12, 18))

    for y in range(world.h):
        sy = y * cfg.cell_px - camera_y
        if sy < -cfg.cell_px or sy > cfg.window_h:
            continue
        for x in range(world.w):
            sx = x * cfg.cell_px - camera_x
            if sx < -cfg.cell_px or sx > cfg.window_w:
                continue
            if world.obstacles[y, x] == 1:
                pygame.draw.rect(screen, (55, 55, 65), (sx, sy, cfg.cell_px, cfg.cell_px))

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

    if cfg.task == 2:
        for (x, y) in world.prey:
            sx = x * cfg.cell_px - camera_x
            sy = y * cfg.cell_px - camera_y
            if -cfg.cell_px <= sx <= cfg.window_w and -cfg.cell_px <= sy <= cfg.window_h:
                pygame.draw.rect(
                    screen,
                    (220, 220, 90),
                    (sx + 2, sy + 2, max(2, cfg.cell_px - 4), max(2, cfg.cell_px - 4)),
                )

        px, py = world.predator_pos
        pygame.draw.circle(
            screen,
            (200, 80, 80),
            (px * cfg.cell_px + cfg.cell_px // 2 - camera_x,
             py * cfg.cell_px + cfg.cell_px // 2 - camera_y),
            cfg.predator_radius * cfg.cell_px,
            width=2,
        )

    for b in bats:
        cx = b.x * cfg.cell_px + cfg.cell_px // 2 - camera_x
        cy = b.y * cfg.cell_px + cfg.cell_px // 2 - camera_y

        if cx < -20 or cx > cfg.window_w + 20 or cy < -20 or cy > cfg.window_h + 20:
            continue

        if world.step_count - getattr(b, "last_ping_step", -999) <= 3:
            ping_color = (255, 100, 100) if isinstance(b, LLMBat) else (120, 180, 255)
            for r in [10, 18, 26]:
                pygame.draw.circle(screen, ping_color, (cx, cy), r, width=1)

        color = (100, 220, 100) if getattr(b, "done", False) else (
            (220, 70, 70) if isinstance(b, LLMBat) else (210, 210, 225)
        )

        pygame.draw.circle(screen, color, (cx, cy), max(2, cfg.cell_px // 3))

        hx, hy = getattr(b, "heading", (1, 0))
        tip_x = cx + hx * 8
        tip_y = cy + hy * 8
        pygame.draw.line(screen, (255, 255, 255), (cx, cy), (tip_x, tip_y), 2)

    y0 = 8
    for line in info_lines:
        surf = font.render(line, True, (235, 235, 235))
        screen.blit(surf, (8, y0))
        y0 += 20


def main():
    cfg = SimConfig()
    if len(sys.argv) >= 2:
        cfg.task = int(sys.argv[1])

    random.seed(0)
    pygame.init()
    os.makedirs("frames", exist_ok=True)
    os.makedirs("gifs", exist_ok=True)

    record_gif = True
    saved_frames = []
    screen = pygame.display.set_mode((cfg.window_w, cfg.window_h))
    pygame.display.set_caption("Bat Stigmergy Swarm")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("consolas", 18)

    world = World(cfg, seed=0)
    client = LMStudioClient(cfg.llm_base_url, cfg.llm_model, cfg.llm_temperature)

    bats = []
    spawn_positions = clustered_spawn_positions(
        world, cfg.n_bats, center_x=8, center_y=world.h // 2, radius=3
    )

    for i in range(cfg.n_llm_bats):
        x, y = spawn_positions[i]
        bats.append(LLMBat(x, y, client))

    for i in range(cfg.n_llm_bats, cfg.n_bats):
        x, y = spawn_positions[i]
        bats.append(RuleBasedBat(x, y))

    world.bats = bats
    running = True
    llm_last_rationale = ""

    while running:
        clock.tick(cfg.fps)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        # LLM decision phase
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

        # Important: shuffle first so ties do not always go to same bats
        random.shuffle(planned)

        # Then prioritize LLM and jammed bats
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

                if b.x >= world.w - 3:
                    b.done = True
                    b.score += 50.0

            if cfg.task == 2:
                if world.predator_risk(b.x, b.y) > 0:
                    b.predator_events += 1
                    b.score -= cfg.predator_penalty
                    world.sound.deposit_alarm(b.x, b.y, cfg.alarm_deposit)

                if (b.x, b.y) in world.prey:
                    world.prey.remove((b.x, b.y))
                    b.prey_collected += 1
                    b.score += cfg.prey_reward
                    world.sound.deposit_buzz(b.x, b.y, cfg.buzz_deposit)

                if call == "BUZZ":
                    world.sound.deposit_buzz(b.x, b.y, cfg.buzz_deposit * 0.5)
                elif call == "ALARM":
                    world.sound.deposit_alarm(b.x, b.y, cfg.alarm_deposit * 0.5)

        world.step()

        if world.step_count >= cfg.max_steps:
            running = False

        if cfg.task == 1 and all(getattr(b, "done", False) for b in bats):
            running = False

        active_bats = [b for b in bats if not getattr(b, "done", False)]
        if active_bats:
            avg_x = sum(b.x for b in active_bats) / len(active_bats)
            avg_y = sum(b.y for b in active_bats) / len(active_bats)
        else:
            avg_x = world.w / 2
            avg_y = world.h / 2

        camera_x = int(avg_x * cfg.cell_px - cfg.window_w // 3)
        camera_y = int(avg_y * cfg.cell_px - cfg.window_h // 2)

        camera_x = max(0, min(camera_x, cfg.grid_w * cfg.cell_px - cfg.window_w))
        camera_y = max(0, min(camera_y, cfg.grid_h * cfg.cell_px - cfg.window_h))

        total_score = sum(b.score for b in bats)
        total_prey = sum(getattr(b, "prey_collected", 0) for b in bats)
        total_pred = sum(getattr(b, "predator_events", 0) for b in bats)

        info = [
            f"Task={cfg.task}  Steps={world.step_count}/{cfg.max_steps}",
            f"Score={total_score:.1f}  Prey={total_prey}  PredatorEvents={total_pred}",
            f"LLM model={cfg.llm_model}  LLM bats={cfg.n_llm_bats}  Decision period={cfg.llm_decision_period}",
            f"LLM rationale: {llm_last_rationale[:110]}",
        ]

        draw(screen, cfg, world, bats, font, info, camera_x, camera_y)
        pygame.display.flip()



        #===================================GIF RECORDING (optional)===================================
        # if record_gif and world.step_count % 2 == 0:
        #     frame_path = f"frames/frame_{world.step_count:05d}.png"
        #     pygame.image.save(screen, frame_path)
        #     saved_frames.append(frame_path)

        # if record_gif and saved_frames:
        #     images = [imageio.imread(fp) for fp in saved_frames]
        #     gif_name = f"gifs/task_{cfg.task}_run.gif"
        #     imageio.mimsave(gif_name, images, fps=12)
        #     print(f"Saved GIF to {gif_name}")
    pygame.quit()


if __name__ == "__main__":
    main()