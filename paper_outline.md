# Paper Outline — LLM-Augmented Bat Stigmergy Swarm

---

## Header
- Title: "LLM-Augmented Stigmergy: Embedding a Language Model Agent in a Bio-Inspired Swarm"
- Authors: Joel Carlson, Yuri Fung 
- Course: CSCI 5423 — Biologically Inspired Computing

---

## 1. Introduction (~0.75 page)
- Swarm intelligence relies on simple local rules and indirect communication (stigmergy) to produce collective behavior
- Limitation: purely rule-based agents cannot reason about novel or complex situations
- Research question: can a single LLM-controlled agent embedded in a rule-based swarm improve collective performance?
- Two tasks test complementary aspects: navigation under uncertainty (Task 1) and foraging/predator avoidance (Task 2)
- Brief roadmap of the paper

---

## 2. Background & Related Work (~1 page)
- **Stigmergy**: Grasse 1959; indirect coordination via environment modification (pheromone trails, sound fields)
- **Bat echolocation and social calls**: biosonar for navigation; feeding buzzes serve as eavesdropping cues for nearby bats to locate prey (Bohn et al. 2009); dual navigation + social coordination role directly motivates buzz/alarm stigmergy field
- **Swarm robotics**: Reynolds boids model; ant colony optimization; particle swarm optimization
- **LLMs as agents**: Guo et al. 2024 survey of LLM multi-agent systems; LLM2Swarm (2024) — closest prior work, embeds LLMs in robot swarms for real-time reasoning
- **Informed individuals in animal groups**: Couzin et al. 2005 — a minority of informed individuals can steer an entire group without explicit signaling; theoretical basis for the LLM bat design
- Gap: no prior work embeds an LLM as an informed individual within a stigmergy-based swarm simulation

---

## 3. Methods (~1.5 pages)

### 3.1 Simulation Environment
- 2D grid world, 220×110 cells, implemented in Python/Pygame
- Acoustic soundscape: two-channel stigmergy field (buzz = food, alarm = danger), decay rate 0.985, diffusion 0.18
- Echolocation: 8-direction ray casting with configurable noise (σ = 0.08, 0.12, 0.20)

### 3.2 Agent Types
- **RuleBasedBat**: gradient-following agent; moves toward buzz, away from alarm; emits calls based on local field values
- **LLMBat**: queries Qwen3.5-0.8B via LM Studio API every 5 steps; receives structured observation (distances, sound levels, predator bearing if privileged); outputs directional action + social call + rationale

### 3.3 Task 1 — Cave Exit Navigation
- Bats spawn inside a cave, must reach exit on right side of grid
- 4 layouts: corridor, bottleneck, zigzag, cul-de-sac
- Conditions: rule-only (0 LLM bats) vs. one-LLM (1 LLM bat, 14 rule-based)
- 3 noise levels × 4 layouts × 2 conditions × 20 seeds = 480 episodes
- Metrics: escape rate, mean time to exit, path efficiency, jam events

### 3.4 Task 2 — Open-World Foraging
- Toroidal open world; 50 prey items, 3 predators
- 5 conditions varying stigmergy, privileged observation, and recruitment on/off
- 20 seeds per condition = 100 episodes
- Metrics: prey collected, survival rate, predator incidents, bats eaten, time to first/all prey

### 3.5 LLM Configuration
- Model: Qwen3.5-0.8B (GGUF), served locally via LM Studio at 127.0.0.1:1234
- Temperature: 0.2, max tokens: 80–140
- Prompt structure: system role + structured observation + output format constraint

---

## 4. Results (~1.5 pages)

### 4.1 Task 1 Results
- **Escape rate**: LLM improves escape rate across all layouts
  - Bottleneck: 51% → 91% (largest gain, most constrained layout)
  - Corridor: 80% → 96%
  - Cul-de-sac: 79% → 97%
  - Zigzag: 69% → 90%
- **Time to exit**: LLM ~2x faster across all layouts
  - Bottleneck: 475 → 216 steps
  - Corridor: 294 → 162 steps
- **Path efficiency**: LLM ~2x more efficient (bottleneck: 0.26 → 0.60)
- **Jam events**: marginally higher with LLM — trade-off of faster throughput through narrow passages
- Include figures: escape rate bar chart, time to exit bar chart, path efficiency bar chart (per layout)

### 4.2 Task 2 Results
- Stigmergy alone (rule_stig_on vs rule_stig_off): modest improvement in survival, similar prey collection
- LLM with privileged observation + recruitment: higher predator incidents and lower survival than rule-only
  - Interpretation: LLM aggressively recruits bats toward prey, exposing them to predators
- LLM with recruitment off: better survival, comparable prey collection — recruitment is the key variable
- LLM local-only (no privileged obs): intermediate performance
- Include figures: survival rate, bats eaten, prey collected bar charts

---

## 5. Discussion (~0.5 page)
- Task 1: a single LLM agent reliably improves swarm navigation — bottleneck result is the clearest evidence
- Task 2: LLM coordination trades safety for foraging efficiency; privileged observation amplifies this effect
- The informed-individual effect (Couzin et al.) holds: one agent with better information shapes collective behavior
- Limitations: small LLM (0.8B), no learning across episodes, fixed prompt structure, headless batch vs. interactive sim
- Future work: larger models, fine-tuning on simulation traces, multi-LLM swarms

---

## 6. Project Contributions
- [Your name]: [list tasks]
- [Partner name]: [list tasks]

---

## 7. Bibliography (6–10 entries)
- Grasse, P.P. (1959). La reconstruction du nid... [stigmergy origin]
- Couzin, I.D., Krause, J., Franks, N.R., & Levin, S.A. (2005). Effective leadership and decision-making in animal groups on the move. *Nature*, 433, 513–516. https://www.nature.com/articles/nature03236
- Reynolds, C. (1987). Flocks, herds and schools: A distributed behavioral model. *SIGGRAPH*
- Dorigo, M. & Stützle, T. (2004). *Ant Colony Optimization*. MIT Press
- Bohn, K.M., Moss, C.F., & Wilkinson, G.S. (2009). Experimental evidence for group hunting via eavesdropping in echolocating bats. *Proceedings of the Royal Society B*. https://pmc.ncbi.nlm.nih.gov/articles/PMC2839959/
- Guo, T., et al. (2024). Large Language Model based Multi-Agents: A Survey of Progress and Challenges. *IJCAI 2024*. https://arxiv.org/abs/2402.01680
- Jürgen, S., et al. (2024). LLM2Swarm: Robot Swarms that Responsively Reason, Plan, and Collaborate through LLMs. *arXiv:2410.11387*. https://arxiv.org/html/2410.11387v2
- Pygame / simulation implementation reference

---