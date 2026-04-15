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

from .batsim.config import SimConfig
from .batsim.world import World
from .batsim.agents import RuleBasedBat, LLMBat
from .llm.lm_studio_client import LMStudioClient

def draw(screen, cfg: SimConfig, world: World, bats, font, info_lines):
    screen.fill((10, 10, 14))

    # obstacles
    for y in range(world.h):
        for x in range(world.w):
            if world.obstacles[y, x] == 1:
                pygame.draw.rect(
                    screen, (50, 50, 60),
                    (x * cfg.cell_px, y * cfg.cell_px, cfg.cell_px, cfg.cell_px)
                )

    # exit region
    if cfg.task == 1:
        pygame.draw.rect(
            screen, (20, 60, 20),
            (world.exit_x0 * cfg.cell_px, 0, cfg.exit_width * cfg.cell_px, world.h * cfg.cell_px)
        )

    # prey/predator
    if cfg.task == 2:
        for (x, y) in world.prey:
            pygame.draw.rect(
                screen, (220, 220, 90),
                (x * cfg.cell_px + 2, y * cfg.cell_px + 2, cfg.cell_px - 4, cfg.cell_px - 4)
            )

        px, py = world.predator_pos
        pygame.draw.circle(
            screen, (200, 80, 80),
            (px * cfg.cell_px + cfg.cell_px // 2, py * cfg.cell_px + cfg.cell_px // 2),
            cfg.predator_radius * cfg.cell_px,
            width=2
        )

    # bats
    for b in bats:
        if getattr(b, "done", False):
            color = (100, 220, 100)
        else:
            color = (80, 200, 240) if isinstance(b, LLMBat) else (200, 200, 220)

        pygame.draw.circle(
            screen, color,
            (b.x * cfg.cell_px + cfg.cell_px // 2, b.y * cfg.cell_px + cfg.cell_px // 2),
            max(2, cfg.cell_px // 3)
        )

    # info
    y0 = 5
    for line in info_lines:
        surf = font.render(line, True, (235, 235, 235))
        screen.blit(surf, (5, y0))
        y0 += 18


def main():
    cfg = SimConfig()
    if len(sys.argv) >= 2:
        cfg.task = int(sys.argv[1])

    random.seed(0)

    pygame.init()
    screen = pygame.display.set_mode((cfg.grid_w * cfg.cell_px, cfg.grid_h * cfg.cell_px))
    pygame.display.set_caption("Bat Stigmergy Swarm")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("consolas", 16)

    world = World(cfg, seed=0)
    client = LMStudioClient(cfg.llm_base_url, cfg.llm_model, cfg.llm_temperature)

    bats = []
    def clustered_spawn_positions(world, n, center_x=5, center_y=None, radius=4):
        if center_y is None:
            center_y = world.h // 2

        positions = []
        tries = 0
        while len(positions) < n and tries < 1000:
            tries += 1
            x = random.randint(max(0, center_x - radius), min(world.w - 1, center_x + radius))
            y = random.randint(max(0, center_y - radius), min(world.h - 1, center_y + radius))
            if world.is_free(x, y) and (x, y) not in positions:
                positions.append((x, y))
        return positions

    # def random_free_pos():
    #     while True:
    #         x = random.randrange(0, max(2, world.w // 4))
    #         y = random.randrange(0, world.h)
    #         if world.is_free(x, y):
    #             return x, y
    spawn_positions = clustered_spawn_positions(world, cfg.n_bats, center_x=6, center_y=world.h // 2, radius=3)

    # LLM bats first
    for i in range(cfg.n_llm_bats):
        x, y = spawn_positions[i]
        bats.append(LLMBat(x, y, client))

    # Rule bats
    for i in range(cfg.n_llm_bats, cfg.n_bats):
        x, y = spawn_positions[i]
        bats.append(RuleBasedBat(x, y))
    # for _ in range(cfg.n_llm_bats):
    #     x, y = random_free_pos()
    #     bats.append(LLMBat(x, y, client))

    # for _ in range(cfg.n_bats - cfg.n_llm_bats):
    #     x, y = random_free_pos()
    #     bats.append(RuleBasedBat(x, y))

    running = True
    llm_last_rationale = ""

    while running:
        clock.tick(cfg.fps)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        # -----------------------------
        # PHASE 1: LLM decision step
        # -----------------------------
        if world.step_count % cfg.llm_decision_period == 0:
            for b in bats:
                if isinstance(b, LLMBat) and not b.done:
                    b.query_llm(world, cfg)

        # -----------------------------
        # PHASE 2: collect all actions
        # -----------------------------
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

        # -----------------------------
        # PHASE 3: apply all actions
        # -----------------------------
        for b, (dx, dy), call, rationale in planned:
            if getattr(b, "done", False):
                continue

            nx, ny = b.x + dx, b.y + dy
            if world.is_free(nx, ny):
                b.x, b.y = nx, ny

            # Task 1 scoring
            if cfg.task == 1:
                if (dx, dy) != (0, 0):
                    b.score += 0.01
                else:
                    b.score -= 0.02

                if world.is_exit(b.x):
                    # keep rewarding outward movement beyond exit
                    b.score += 1.0 + 0.05 * (b.x - world.exit_x0)
                    if b.x >= world.w - 2:
                        b.done = True

            # Task 2 scoring
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

        # -----------------------------
        # PHASE 4: world update
        # -----------------------------
        world.step()

        # end conditions
        if world.step_count >= cfg.max_steps:
            running = False

        if cfg.task == 1 and all(getattr(b, "done", False) for b in bats):
            running = False

        total_score = sum(b.score for b in bats)
        total_prey = sum(getattr(b, "prey_collected", 0) for b in bats)
        total_pred = sum(getattr(b, "predator_events", 0) for b in bats)

        info = [
            f"Task={cfg.task}  Steps={world.step_count}/{cfg.max_steps}",
            f"Score={total_score:.1f}  Prey={total_prey}  PredatorEvents={total_pred}",
            f"LLM model={cfg.llm_model}  LLM bats={cfg.n_llm_bats}  Decision period={cfg.llm_decision_period}",
            f"LLM rationale: {llm_last_rationale[:90]}",
        ]

        draw(screen, cfg, world, bats, font, info)
        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()