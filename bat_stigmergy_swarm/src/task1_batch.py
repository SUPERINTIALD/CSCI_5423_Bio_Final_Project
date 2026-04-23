import csv
import math
import random
from statistics import mean

from .batsim.config import SimConfig
from .batsim.world import World
from .batsim.agents import RuleBasedBat, LLMBat
from .llm.lm_studio_client import LMStudioClient
from .main import build_world_and_bats, choose_resolved_move


def init_bat_stats(bats):
    for b in bats:
        b.start_x = b.x
        b.start_y = b.y
        b.path_len = 0.0
        b.jam_events = 0
        b.was_jammed = False
        b.exit_step = None


def update_jam_stats(b):
    jammed_now = getattr(b, "stuck_steps", 0) >= 3
    if jammed_now and not getattr(b, "was_jammed", False):
        b.jam_events += 1
    b.was_jammed = jammed_now


def task1_summary(world, bats):
    escaped = [b for b in bats if getattr(b, "done", False)]
    escape_rate = len(escaped) / max(1, len(bats))

    mean_time_to_exit = mean([b.exit_step for b in escaped]) if escaped else None
    mean_jam_events = mean([getattr(b, "jam_events", 0) for b in bats]) if bats else 0.0

    efficiencies = []
    for b in escaped:
        net_progress = max(0, b.x - b.start_x)
        eff = net_progress / max(1e-6, b.path_len)
        efficiencies.append(eff)

    mean_path_eff = mean(efficiencies) if efficiencies else None

    return {
        "escape_rate": escape_rate,
        "time_to_exit_mean": mean_time_to_exit,
        "jam_events_mean": mean_jam_events,
        "path_eff_mean": mean_path_eff,
    }


def run_task1_episode(cfg, client, seed):
    random.seed(seed)
    world = World(cfg, seed=seed)

    bats = []
    spawn_positions = []
    # reuse your current spawn builder
    tmp_world, tmp_bats = build_world_and_bats(cfg, client)
    spawn_positions = [(b.x, b.y) for b in tmp_bats]

    bats = []
    for i in range(cfg.n_llm_bats):
        x, y = spawn_positions[i]
        bats.append(LLMBat(x, y, client))
    for i in range(cfg.n_llm_bats, cfg.n_bats):
        x, y = spawn_positions[i]
        bats.append(RuleBasedBat(x, y))

    world.bats = bats
    init_bat_stats(bats)

    while world.step_count < cfg.max_steps:
        if all(getattr(b, "done", False) for b in bats):
            break

        # LLM decisions
        if world.step_count % cfg.llm_decision_period == 0:
            for b in bats:
                if isinstance(b, LLMBat) and not getattr(b, "done", False):
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

            action, call, rationale = b.act(world, cfg)
            planned.append((b, action, call, rationale))

        random.shuffle(planned)
        resolution_order = sorted(
            planned,
            key=lambda item: (isinstance(item[0], LLMBat), getattr(item[0], "stuck_steps", 0)),
            reverse=True,
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
                step_len = math.sqrt(2) if abs(b.x - old_x) == 1 and abs(b.y - old_y) == 1 else 1.0
                b.path_len += step_len
                b.heading = (b.x - old_x, b.y - old_y)
                b.stuck_steps = 0
            else:
                b.stuck_steps += 1

            update_jam_stats(b)

            if world.is_exit(b.x):
                b.done = True
                b.exit_step = world.step_count

        world.step()

    return task1_summary(world, bats)


def run_task1_batch():
    base_cfg = SimConfig()
    base_cfg.task = 1

    client = LMStudioClient(base_cfg.llm_base_url, base_cfg.llm_model, base_cfg.llm_temperature)

    layouts = ["corridor", "bottleneck", "zigzag", "culdesac"]
    ping_noises = [0.08, 0.12, 0.20]
    conditions = [
        ("rule_only", 0),
        ("one_llm", 1),
    ]
    seeds = list(range(10))

    rows = []

    for layout in layouts:
        for ping_noise in ping_noises:
            for condition_name, n_llm in conditions:
                for seed in seeds:
                    cfg = SimConfig(**base_cfg.model_dump())
                    cfg.task = 1
                    cfg.task1_layout = layout
                    cfg.ping_noise = ping_noise
                    cfg.n_llm_bats = n_llm

                    metrics = run_task1_episode(cfg, client, seed)
                    rows.append({
                        "layout": layout,
                        "ping_noise": ping_noise,
                        "condition": condition_name,
                        "seed": seed,
                        **metrics,
                    })
                    print(f"done | layout={layout} ping={ping_noise} cond={condition_name} seed={seed} -> {metrics}")

    with open("task1_results.csv", "w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "layout", "ping_noise", "condition", "seed",
                "escape_rate", "time_to_exit_mean", "jam_events_mean", "path_eff_mean"
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    print("Saved task1_results.csv")


if __name__ == "__main__":
    run_task1_batch()