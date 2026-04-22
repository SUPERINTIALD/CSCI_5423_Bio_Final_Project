from pydantic import BaseModel


class SimConfig(BaseModel):
    # World size (in grid cells)
    grid_w: int = 220
    grid_h: int = 110
    # Display window size (camera shows only part of world)
    window_w: int = 1400
    window_h: int = 900
    cell_px: int = 8
    fps: int = 30

    # Bats
    n_bats: int = 15
    n_llm_bats: int = 1
    max_steps: int = 1000

    # Task
    task: int = 1  # 1 = cave exit, 2 = predator/prey outside cave

    # Cave / world generation
    obstacle_density: float = 0.08
    exit_width: int = 10

    # Task 2: prey / predator
    n_predators: int = 3

    n_prey: int = 50
    predator_radius: int = 3
    prey_reward: float = 15.0
    predator_penalty: float = 10.0
    # Soundscape (stigmergy)
    decay: float = 0.985
    diffuse: float = 0.18
    buzz_deposit: float = 2.5
    alarm_deposit: float = 3.0
    predator_move_period: int = 3
    # Echolocation
    ping_noise: float = 0.12

    # LLM (LM Studio)
    llm_base_url: str = "http://127.0.0.1:1234"
    llm_model: str = "qwen3.5-0.8b"
    llm_temperature: float = 0.2
    llm_decision_period: int = 5