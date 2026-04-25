import csv
import os
import random
from statistics import mean

# from CSCI_5423_Bio_Final_Project.bat_stigmergy_swarm.src.batsim import world

from .batsim.config import SimConfig
from .batsim.agents import LLMBat
from .llm.lm_studio_client import LMStudioClient
from .main import build_world_and_bats, choose_resolved_move


def run_task2_episode(cfg, client, seed):
    random.seed(seed)
    world, bats = build_world_and_bats(cfg, client)
    initial_prey_count = len(world.prey)
    for b in bats:
        b.first_prey_step = None

    time_to_all_prey = None
    timeout = 0
    all_bats_dead = 0
    all_prey_collected = 0
    episode_result = "partial"

    while world.step_count < cfg.max_steps:
        # alive_active = [b for b in bats if getattr(b, "alive", True) and not getattr(b, "done", False)]
        # if not alive_active:
        #     break
        alive_active = [b for b in bats if getattr(b, "alive", True) and not getattr(b, "done", False)]

        # failure: all bats dead
        if not alive_active:
            all_bats_dead = 1
            episode_result = "failure"
            break

        # success: all prey collected
        if len(world.prey) == 0:
            all_prey_collected = 1 if len(world.prey) == 0 else 0
            time_to_all_prey = world.step_count
            episode_result = "success"
            break

        # LLM decisions
        if world.step_count % cfg.llm_decision_period == 0:
            for b in bats:
                if isinstance(b, LLMBat) and getattr(b, "alive", True) and not getattr(b, "done", False):
                    b.query_llm(world, cfg)

        world.bat_positions = [(b.x, b.y) for b in bats if getattr(b, "alive", True) and not getattr(b, "done", False)]

        for b in bats:
            if not getattr(b, "alive", True) or getattr(b, "done", False):
                continue
            if b.should_ping(world):
                b.ping(world, cfg)

        planned = []
        for b in bats:
            if not getattr(b, "alive", True) or getattr(b, "done", False):
                planned.append((b, (0, 0), "NONE", "done"))
                continue
            action, call, rationale = b.act(world, cfg)
            planned.append((b, action, call, rationale))

        random.shuffle(planned)
        resolution_order = sorted(
            planned,
            key=lambda item: (isinstance(item[0], LLMBat), getattr(item[0], "stuck_steps", 0)),
            reverse=True
        )

        reserved_next = set()

        buzz_calls = 0
        alarm_calls = 0

        for b, (dx, dy), call, rationale in resolution_order:
            if not getattr(b, "alive", True) or getattr(b, "done", False):
                continue

            old_x, old_y = b.x, b.y
            chosen_x, chosen_y = choose_resolved_move(world, b, (dx, dy), reserved_next)

            b.x, b.y = chosen_x, chosen_y
            reserved_next.add((b.x, b.y))

            moved = (b.x, b.y) != (old_x, old_y)
            if moved:
                if cfg.task == 2:
                    dxh = b.x - old_x
                    dyh = b.y - old_y
                    if dxh > world.w / 2:
                        dxh -= world.w
                    elif dxh < -world.w / 2:
                        dxh += world.w
                    if dyh > world.h / 2:
                        dyh -= world.h
                    elif dyh < -world.h / 2:
                        dyh += world.h
                    dxh = 0 if dxh == 0 else (1 if dxh > 0 else -1)
                    dyh = 0 if dyh == 0 else (1 if dyh > 0 else -1)
                    b.heading = (dxh, dyh)
                else:
                    b.heading = (b.x - old_x, b.y - old_y)
                b.stuck_steps = 0
            else:
                b.stuck_steps += 1

            # predator incidents

            # predator kill check (match interactive sim)
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

                if dxp * dxp + dyp * dyp <= max(2, cfg.predator_radius // 2) ** 2:
                    if getattr(b, "alive", True):
                        b.alive = False
                        b.done = True
                    continue
            if world.predator_risk(b.x, b.y) > 0:
                b.predator_events += 1

            # prey capture
            caught_prey = None
            for px2, py2 in list(world.prey):
                dxp2 = abs(b.x - px2)
                dyp2 = abs(b.y - py2)
                dxp2 = min(dxp2, world.w - dxp2)
                dyp2 = min(dyp2, world.h - dyp2)
                if dxp2 * dxp2 + dyp2 * dyp2 <= 4:
                    caught_prey = (px2, py2)
                    break

            if caught_prey is not None:
                world.prey.remove(caught_prey)
                b.prey_collected += 1
                if b.first_prey_step is None:
                    b.first_prey_step = world.step_count

            # call logging
            if call == "BUZZ":
                buzz_calls += 1
                b.last_call_step = world.step_count
                b.last_call_type = "BUZZ"
                if cfg.stigmergy_on:
                    world.sound.deposit_buzz(b.x, b.y, cfg.buzz_deposit * 0.75)
            elif call == "ALARM":
                alarm_calls += 1
                b.last_call_step = world.step_count
                b.last_call_type = "ALARM"
                if cfg.stigmergy_on:
                    world.sound.deposit_alarm(b.x, b.y, cfg.alarm_deposit * 1.0)

                if isinstance(b, LLMBat) and cfg.recruitment_on:
                    for other in bats:
                        if other is b or not getattr(other, "alive", True) or getattr(other, "done", False):
                            continue
                        dxh = abs(other.x - b.x)
                        dyh = abs(other.y - b.y)
                        dxh = min(dxh, world.w - dxh)
                        dyh = min(dyh, world.h - dyh)
                        if dxh + dyh <= 16:
                            other.follow_leader_ticks = 24
                            other.leader_mode = "ALARM"
                            other.recruited_ticks = 0

            # BUZZ recruitment
            if call == "BUZZ" and isinstance(b, LLMBat) and cfg.recruitment_on:
                for other in bats:
                    if other is b or not getattr(other, "alive", True) or getattr(other, "done", False):
                        continue
                    dxh = abs(other.x - b.x)
                    dyh = abs(other.y - b.y)
                    dxh = min(dxh, world.w - dxh)
                    dyh = min(dyh, world.h - dyh)
                    if dxh + dyh <= 14:
                        other.follow_leader_ticks = 30
                        other.leader_mode = "BUZZ"
                        other.recruited_ticks = 20

        world.step()

    if episode_result == "partial":
        timeout = 1
    total_prey = sum(getattr(b, "prey_collected", 0) for b in bats)
    total_pred_incidents = sum(getattr(b, "predator_events", 0) for b in bats)
    alive_count = sum(1 for b in bats if getattr(b, "alive", True))
    dead_count = len(bats) - alive_count
    survival_rate = alive_count / max(1, len(bats))

    first_prey_steps = [b.first_prey_step for b in bats if b.first_prey_step is not None]
    time_to_first_prey = min(first_prey_steps) if first_prey_steps else None

    prey_completion_rate = total_prey / max(1, initial_prey_count)

    llm_bats = [b for b in bats if isinstance(b, LLMBat)]
    llm_survived = 1 if any(getattr(b, "alive", True) for b in llm_bats) else 0

    episodes_with_zero_deaths = 1 if dead_count == 0 else 0
    all_prey_collected = 1 if len(world.prey) == 0 else 0
    return {
        "total_prey_collected": total_prey,
        "predator_incidents": total_pred_incidents,
        "survival_rate": survival_rate,
        "time_to_first_prey": time_to_first_prey,
        "prey_completion_rate": prey_completion_rate,
        "all_prey_collected": all_prey_collected,
        "time_to_all_prey": time_to_all_prey,
        "bats_eaten": dead_count,
        "llm_survived": llm_survived,
        "timeout": timeout,
        "all_bats_dead": all_bats_dead,
        "episodes_with_zero_deaths": episodes_with_zero_deaths,
        "episode_result": episode_result,
    }


def run_task2_batch():
    os.makedirs("results", exist_ok=True)

    base_cfg = SimConfig()
    base_cfg.task = 2
    base_cfg.render = False

    client = LMStudioClient(base_cfg.llm_base_url, base_cfg.llm_model, base_cfg.llm_temperature)

    conditions = [
        {
            "condition": "rule_stig_off",
            "n_llm_bats": 0,
            "stigmergy_on": False,
            "privileged_obs": False,
            "recruitment_on": False,
        },
        {
            "condition": "rule_stig_on",
            "n_llm_bats": 0,
            "stigmergy_on": True,
            "privileged_obs": False,
            "recruitment_on": False,
        },
        {
            "condition": "llm_priv_on_recruit_on",
            "n_llm_bats": 1,
            "stigmergy_on": True,
            "privileged_obs": True,
            "recruitment_on": True,
        },
        {
            "condition": "llm_local_only_recruit_on",
            "n_llm_bats": 1,
            "stigmergy_on": True,
            "privileged_obs": False,
            "recruitment_on": True,
        },
        {
            "condition": "llm_priv_on_recruit_off",
            "n_llm_bats": 1,
            "stigmergy_on": True,
            "privileged_obs": True,
            "recruitment_on": False,
        },
    ]

    seeds = list(range(20))
    rows = []

    for cond in conditions:
        for seed in seeds:
            cfg = SimConfig(**base_cfg.model_dump())
            cfg.task = 2
            cfg.n_llm_bats = cond["n_llm_bats"]
            cfg.stigmergy_on = cond["stigmergy_on"]
            cfg.privileged_obs = cond["privileged_obs"]
            cfg.recruitment_on = cond["recruitment_on"]

            metrics = run_task2_episode(cfg, client, seed)
            rows.append({
                "condition": cond["condition"],
                "seed": seed,
                **metrics,
            })
            print(cond["condition"], seed, metrics)

    out_csv = os.path.join("results", "task2_results.csv")
    with open(out_csv, "w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "condition", "seed",
                "total_prey_collected",
                "predator_incidents",
                "survival_rate",
                "time_to_first_prey",
                "prey_completion_rate",
                "all_prey_collected",
                "time_to_all_prey",
                "bats_eaten",
                "llm_survived",
                "timeout",
                "all_bats_dead",
                "episodes_with_zero_deaths",
                "episode_result",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"Saved {out_csv}")


if __name__ == "__main__":
    run_task2_batch()