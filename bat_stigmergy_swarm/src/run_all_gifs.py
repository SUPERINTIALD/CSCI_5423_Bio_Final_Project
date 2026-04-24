import os
import sys
import subprocess


PYTHON = sys.executable


def run_scenario(task: int, gif_name: str, *, layout=None, env_overrides=None):
    env = os.environ.copy()
    env["GIF_RECORD"] = "1"
    env["GIF_NAME"] = gif_name
    env["SIM_SEED"] = env_overrides.get("SIM_SEED", "0") if env_overrides else "0"

    if env_overrides:
        for k, v in env_overrides.items():
            env[k] = str(v)

    cmd = [PYTHON, "-m", "src.main", str(task)]
    if task == 1 and layout is not None:
        cmd.append(layout)

    print(f"\n=== Running: {' '.join(cmd)} ===")
    print(f"GIF -> {gif_name}")
    subprocess.run(cmd, env=env, check=True)


def main():
    os.makedirs("gifs", exist_ok=True)

    scenarios = [
        # -------------------------
        # Task 1: one GIF per layout, with 1 LLM bat
        # -------------------------
        {
            "task": 1,
            "layout": "corridor",
            "gif": "gifs/task1_corridor_llm.gif",
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
            "gif": "gifs/task1_bottleneck_llm.gif",
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
            "gif": "gifs/task1_zigzag_llm.gif",
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
            "gif": "gifs/task1_culdesac_llm.gif",
            "env": {
                "CFG_N_BATS": 15,
                "CFG_N_LLM_BATS": 1,
                "CFG_MAX_STEPS": 600,
                "CFG_PING_NOISE": 0.12,
                "SIM_SEED": 3,
            },
        },

        # -------------------------
        # Task 2: one GIF per main condition
        # -------------------------
        {
            "task": 2,
            "layout": None,
            "gif": "gifs/task2_rule_stig_off.gif",
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
            "gif": "gifs/task2_rule_stig_on.gif",
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
            "gif": "gifs/task2_llm_priv_on_recruit_on.gif",
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
            "gif": "gifs/task2_llm_local_only.gif",
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
            "gif": "gifs/task2_llm_recruit_off.gif",
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

    for sc in scenarios:
        run_scenario(
            sc["task"],
            sc["gif"],
            layout=sc["layout"],
            env_overrides=sc["env"],
        )

    print("\nDone. GIFs saved in ./gifs")


if __name__ == "__main__":
    main()