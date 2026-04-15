from pydantic import BaseModel


class SimConfig(BaseModel):
    # Window / grid
    grid_w: int = 80
    grid_h: int = 60
    cell_px: int = 12
    fps: int = 30

    # Bats
    n_bats: int = 20
    n_llm_bats: int = 1  # start with 1, optionally 2 later
    max_steps: int = 3000

    # Task toggles
    task: int = 1  # 1 = cave exit, 2 = predator/prey

    # Obstacles
    obstacle_density: float = 0.08  # fraction of cells obstacles

    # Exit (Task 1)
    exit_width: int = 6  # exit region width on right side

    # Prey / Predator (Task 2)
    n_prey: int = 60
    predator_radius: int = 6   # danger radius
    predator_penalty: float = 5.0
    prey_reward: float = 1.0

    # Soundscape (stigmergy)
    decay: float = 0.98         # per step
    diffuse: float = 0.20       # 0..1 (simple neighbor mixing)
    buzz_deposit: float = 2.5
    alarm_deposit: float = 3.0

    # Echolocation ping noise
    ping_noise: float = 0.15

    # LLM (LM Studio)
    llm_base_url: str = "http://127.0.0.1:1234"
    llm_model: str = "qwen3.5-0.8b"
    llm_temperature: float = 0.2
    llm_decision_period: int = 5  # call LLM every N steps (faster)