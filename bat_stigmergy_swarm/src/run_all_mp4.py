import os
import sys
import subprocess
import imageio.v2 as imageio

PYTHON = sys.executable


def run_scenario(task: int, media_name: str, *, layout=None, env_overrides=None,
                 task_label="", condition_label="", layout_label=""):
    env = os.environ.copy()
    env["GIF_RECORD"] = "1"
    env["MEDIA_NAME"] = media_name
    env["HIDE_CONTROLS"] = "1"
    env["TASK_LABEL"] = task_label
    env["CONDITION_LABEL"] = condition_label
    env["LAYOUT_LABEL"] = layout_label
    env["SIM_SEED"] = env_overrides.get("SIM_SEED", "0") if env_overrides else "0"

    if env_overrides:
        for k, v in env_overrides.items():
            env[k] = str(v)

    cmd = [PYTHON, "-m", "src.main", str(task)]
    if task == 1 and layout is not None:
        cmd.append(layout)

    print(f"\n=== Running: {' '.join(cmd)} ===")
    print(f"MP4 -> {media_name}")
    subprocess.run(cmd, env=env, check=True)


def concat_mp4s(mp4_paths, output_path, fps=12):
    writer = imageio.get_writer(output_path, fps=fps, codec="libx264")
    for path in mp4_paths:
        reader = imageio.get_reader(path)
        for frame in reader:
            writer.append_data(frame)
        reader.close()
    writer.close()
    print(f"Saved combined MP4 to {output_path}")


def main():
    os.makedirs("videos/tmp", exist_ok=True)
    os.makedirs("videos", exist_ok=True)

    scenarios = [
        {
            "task": 1,
            "layout": "corridor",
            "media": "videos/tmp/task1_corridor_llm.mp4",
            "task_label": "Task 1: Cave Exit Navigation",
            "condition_label": "One LLM-Informed Bat with Rule-Based Bats",
            "layout_label": "Corridor",
            "env": {
                "CFG_N_BATS": 15,
                "CFG_N_LLM_BATS": 1,
                "CFG_MAX_STEPS": 500,
                "CFG_PING_NOISE": 0.12,
                "SIM_SEED": 0,
            },
        },
        {
            "task": 1,
            "layout": "bottleneck",
            "media": "videos/tmp/task1_bottleneck_llm.mp4",
            "task_label": "Task 1: Cave Exit Navigation",
            "condition_label": "One LLM-Informed Bat with Rule-Based Bats",
            "layout_label": "Bottleneck",
            "env": {
                "CFG_N_BATS": 15,
                "CFG_N_LLM_BATS": 1,
                "CFG_MAX_STEPS": 500,
                "CFG_PING_NOISE": 0.12,
                "SIM_SEED": 1,
            },
        },
        {
            "task": 1,
            "layout": "zigzag",
            "media": "videos/tmp/task1_zigzag_llm.mp4",
            "task_label": "Task 1: Cave Exit Navigation",
            "condition_label": "One LLM-Informed Bat with Rule-Based Bats",
            "layout_label": "Zig-Zag Tunnel",
            "env": {
                "CFG_N_BATS": 15,
                "CFG_N_LLM_BATS": 1,
                "CFG_MAX_STEPS": 600,
                "CFG_PING_NOISE": 0.12,
                "SIM_SEED": 2,
            },
        },
        {
            "task": 1,
            "layout": "culdesac",
            "media": "videos/tmp/task1_culdesac_llm.mp4",
            "task_label": "Task 1: Cave Exit Navigation",
            "condition_label": "One LLM-Informed Bat with Rule-Based Bats",
            "layout_label": "Cul-de-Sac",
            "env": {
                "CFG_N_BATS": 15,
                "CFG_N_LLM_BATS": 1,
                "CFG_MAX_STEPS": 600,
                "CFG_PING_NOISE": 0.12,
                "SIM_SEED": 3,
            },
        },
        {
            "task": 2,
            "layout": None,
            "media": "videos/tmp/task2_rule_based_stigmergy_disabled.mp4",
            "task_label": "Task 2: Predator-Prey Foraging",
            "condition_label": "All Rule-Based Bats with Stigmergy Disabled",
            "layout_label": "",
            "env": {
                "CFG_N_BATS": 15,
                "CFG_N_LLM_BATS": 0,
                "CFG_N_PREY": 50,
                "CFG_N_PREDATORS": 3,
                "CFG_MAX_STEPS": 700,
                "CFG_STIGMERGY_ON": 0,
                "CFG_PRIVILEGED_OBS": 0,
                "CFG_RECRUITMENT_ON": 0,
                "SIM_SEED": 10,
            },
        },
        {
            "task": 2,
            "layout": None,
            "media": "videos/tmp/task2_rule_based_stigmergy_enabled.mp4",
            "task_label": "Task 2: Predator-Prey Foraging",
            "condition_label": "All Rule-Based Bats with Stigmergy Enabled",
            "layout_label": "",
            "env": {
                "CFG_N_BATS": 15,
                "CFG_N_LLM_BATS": 0,
                "CFG_N_PREY": 50,
                "CFG_N_PREDATORS": 3,
                "CFG_MAX_STEPS": 700,
                "CFG_STIGMERGY_ON": 1,
                "CFG_PRIVILEGED_OBS": 0,
                "CFG_RECRUITMENT_ON": 0,
                "SIM_SEED": 11,
            },
        },
        {
            "task": 2,
            "layout": None,
            "media": "videos/tmp/task2_llm_privileged_observation_recruitment_enabled.mp4",
            "task_label": "Task 2: Predator-Prey Foraging",
            "condition_label": "One LLM-Informed Bat with Rule-Based Bats, Stigmergy Enabled, Privileged Observation Enabled, Recruitment Enabled",
            "layout_label": "",
            "env": {
                "CFG_N_BATS": 15,
                "CFG_N_LLM_BATS": 1,
                "CFG_N_PREY": 50,
                "CFG_N_PREDATORS": 3,
                "CFG_MAX_STEPS": 700,
                "CFG_STIGMERGY_ON": 1,
                "CFG_PRIVILEGED_OBS": 1,
                "CFG_RECRUITMENT_ON": 1,
                "SIM_SEED": 12,
            },
        },
        {
            "task": 2,
            "layout": None,
            "media": "videos/tmp/task2_llm_local_only_recruitment_enabled.mp4",
            "task_label": "Task 2: Predator-Prey Foraging",
            "condition_label": "One LLM-Informed Bat with Rule-Based Bats, Stigmergy Enabled, Local-Only Observation, Recruitment Enabled",
            "layout_label": "",
            "env": {
                "CFG_N_BATS": 15,
                "CFG_N_LLM_BATS": 1,
                "CFG_N_PREY": 50,
                "CFG_N_PREDATORS": 3,
                "CFG_MAX_STEPS": 700,
                "CFG_STIGMERGY_ON": 1,
                "CFG_PRIVILEGED_OBS": 0,
                "CFG_RECRUITMENT_ON": 1,
                "SIM_SEED": 13,
            },
        },
        {
            "task": 2,
            "layout": None,
            "media": "videos/tmp/task2_llm_privileged_observation_recruitment_disabled.mp4",
            "task_label": "Task 2: Predator-Prey Foraging",
            "condition_label": "One LLM-Informed Bat with Rule-Based Bats, Stigmergy Enabled, Privileged Observation Enabled, Recruitment Disabled",
            "layout_label": "",
            "env": {
                "CFG_N_BATS": 15,
                "CFG_N_LLM_BATS": 1,
                "CFG_N_PREY": 50,
                "CFG_N_PREDATORS": 3,
                "CFG_MAX_STEPS": 700,
                "CFG_STIGMERGY_ON": 1,
                "CFG_PRIVILEGED_OBS": 1,
                "CFG_RECRUITMENT_ON": 0,
                "SIM_SEED": 14,
            },
        },
    ]

    rendered = []
    for sc in scenarios:
        run_scenario(
            sc["task"],
            sc["media"],
            layout=sc["layout"],
            env_overrides=sc["env"],
            task_label=sc["task_label"],
            condition_label=sc["condition_label"],
            layout_label=sc["layout_label"],
        )
        rendered.append(sc["media"])

    concat_mp4s(rendered, "videos/bat_stigmergy_swarm_demo.mp4", fps=12)
    print("\nDone. Combined MP4 saved to videos/bat_stigmergy_swarm_demo.mp4")


if __name__ == "__main__":
    main()