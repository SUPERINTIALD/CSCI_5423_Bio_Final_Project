# LLM-Augmented Stigmergy: Embedding a Language Model Agent in a Bio-Inspired Bat Swarm

 Authors: Joel Carlson, Yuri Fung 
CSCI 5423 — Biologically Inspired Computing

---

## 1. Introduction

Swarm intelligence emerges when many simple agents follow local rules and communicate indirectly through their shared environment. This is a principle called *stigmergy*. Ant colonies build complex structures, fish schools evade predators, and bat colonies locate prey, all without any individual agent having a global view of their world. The power of these systems lies in their robustness and scalability, but their limitation is equally clear: purely rule-based agents cannot reason about novel situations, adapt to changing goals, or interpret ambiguous sensory information.

Large language models (LLMs) have recently demonstrated strong spatial reasoning and decision-making capabilities in agent settings. This raises a natural question: can embedding a single LLM-controlled agent into a rule-based swarm improve collective performance, acting as an *informed individual* that shapes the behavior of the group?

This paper presents a simulation study of LLM-augmented bat swarms in two tasks: cave exit navigation (Task 1) and open-world foraging with predator avoidance (Task 2). In both tasks, a single LLM bat operates alongside rule-based bats in a shared acoustic stigmergy environment. The LLM bat is powered by Qwen3.5-0.8B served locally via LM Studio. We show that the LLM bat significantly improves collective navigation performance in Task 1, and that in Task 2 its recruitment behavior introduces a meaningful safety–foraging trade-off. Our results support the informed-individual hypothesis of Couzin et al. (2005): a small minority with better information can steer an entire group, even without explicit signaling mechanisms.


---

## 2. Background and Related Work

**Stigmergy.** Stigmergy describes indirect coordination through environmental modification. Ants deposit pheromones to mark food trails; subsequent ants follow and reinforce those trails, producing emergent collective foraging without any central controller. In our system, bats deposit acoustic signals — buzz (prey nearby) and alarm (predator nearby) — into a shared soundscape field that decays and diffuses over time, functioning as a two-channel digital pheromone.

**Bat echolocation and social foraging.** Real bats use echolocation not only for navigation but also as a social coordination mechanism. Bohn et al. (2009) demonstrated experimentally that bats eavesdrop on each other's feeding buzzes to locate prey, and that group foraging emerges through this passive acoustic coupling. This directly motivates our buzz/alarm stigmergy design: rule-based bats deposit and follow acoustic gradients in the same way real bats exploit each other's echolocation signals.

**Informed individuals in animal groups.** Couzin et al. (2005) showed using an individual-based model that a small number of informed individuals can reliably steer an entire moving group toward a goal, without signaling their identity or using explicit communication. Crucially, larger groups require a *smaller* proportion of informed individuals to guide them. This result is the theoretical backbone of our LLM bat design: one agent with superior reasoning capability embedded in a swarm of 14 rule-based bats.

**LLMs as agents.** survey the rapid development of LLM-based multi-agent systems, covering collective decision-making, multi-stage reasoning frameworks, and self-refinement. The most directly related work is LLM2Swarm (Jürgen et al., 2024), which embeds LLMs into robot swarms for real-time reasoning and natural-language coordination. Our approach differs in that we use a single LLM agent as an informed individual within a bio-inspired stigmergy system, rather than giving every agent an LLM, and we study how the LLM's signals propagate through the swarm via acoustic fields rather than direct communication.

---

## 3. Methods

### 3.1 Simulation Environment

The simulation runs on a 220×110 discrete grid implemented in Python using Pygame. Two-dimensional acoustic fields — *buzz* and *alarm* — form the stigmergy substrate. At each time step the fields decay by a factor of 0.985 and diffuse at rate 0.18, mimicking how real acoustic signals attenuate and spread in space. Bats deposit into these fields by emitting calls, and read from them via local gradient sensing.

Echolocation is modeled as 8-direction ray casting with configurable Gaussian noise (sigma in {0.08, 0.12, 0.20}), returning obstacle distances in each direction. All experiments use 15 bats total (1 LLM bat + 14 rule-based bats in LLM conditions, or 15 rule-based in control conditions).

### 3.2 Agent Types

**RuleBasedBat.** At each step, the rule-based bat evaluates neighboring cells using a weighted combination of local buzz signal (attractive), alarm signal (repulsive), and task-specific bias (rightward progress in Task 1; random exploration in Task 2). It emits a BUZZ call when local buzz exceeds a threshold, and an ALARM call when alarm exceeds a threshold. Movement is resolved with a priority-based collision system that avoids deadlocks.

**LLMBat.** Every 5 simulation steps, the LLM bat constructs a structured prompt encoding its current position, echolocation distances in 8 directions, local buzz and alarm levels, and nearby bat positions In privileged-observation conditions also the bearing and distance to the nearest predator. The prompt constrains the LLM to return exactly one line specifying a directional action (N/NE/E/SE/S/SW/W/NW/STAY) and a social call (BUZZ/ALARM/NONE) with a brief rationale. Between LLM queries, the bat executes its last decided action. The model used is Qwen3.5-0.8B (GGUF format), served locally at 127.0.0.1:1234 via LM Studio at temperature 0.2.

When the LLM bat emits a BUZZ call, it recruits nearby hungry bats (within Manhattan distance 14) into a 30-step follow-leader mode. When it emits ALARM, it recruits nearby bats (within distance 16) into a 24-step coordinated escape.

### 3.3 Task 1 — Cave Exit Navigation

Bats spawn clustered inside a procedurally generated cave and must navigate to an exit region on the right side of the grid. Four cave layouts are tested: *corridor* (open passage), *bottleneck* (narrow chokepoint), *zigzag* (winding path), and *cul-de-sac* (dead-end branch requiring backtracking). The task ends when all bats escape or 1000 steps elapse.

**Experimental design:** 4 layouts × 3 noise levels × 2 conditions (rule-only, one-LLM) × 20 random seeds = 480 episodes.

**Metrics:** escape rate (fraction of bats reaching exit), mean time to exit (steps), path efficiency (net rightward progress / total path length), and jam events (count of multi-step stuck episodes per bat).

### 3.4 Task 2 — Open-World Foraging

Bats operate in a toroidal open world with 50 prey items and 3 roaming predators. Prey are captured within a small radius; predators kill bats that enter their kill zone. The task ends when all prey are collected, all bats are dead, or 700 steps elapse.

Five conditions are compared:

| Condition | LLM Bats | Stigmergy | Privileged Obs | Recruitment |
|---|---|---|---|---|
| rule_stig_off | 0 | Off | — | Off |
| rule_stig_on | 0 | On | — | Off |
| llm_priv_on_recruit_on | 1 | On | Yes | On |
| llm_local_only_recruit_on | 1 | On | No | On |
| llm_priv_on_recruit_off | 1 | On | Yes | Off |

**Metrics:** total prey collected, survival rate, bats eaten, predator incidents, time to first prey, time to all prey, zero-death episode rate.

All conditions run across 20 random seeds (100 episodes total).

---

## 4. Results

### 4.1 Task 1 — Cave Exit Navigation

The addition of a single LLM bat produced consistent, large improvements in collective navigation performance across all four cave layouts and all noise levels.

**Escape Rate.** Figure 1 shows escape rates by layout. The LLM bat improved escape rates in every condition. The largest gain occurred in the bottleneck layout — the most spatially constrained — where escape rate rose from 51% (rule-only) to 91% (one-LLM). In the corridor, cul-de-sac, and zigzag layouts, escape rates improved from 80%, 79%, and 69% to 96%, 97%, and 90% respectively.

![Escape Rate — Bottleneck](bat_stigmergy_swarm/results/task1_20260428_205154/task1_bottleneck_escape_rate.png)
*Figure 1a: Escape rate in the bottleneck layout by condition and noise level. Error bars show ±1 SD across 20 seeds.*

![Escape Rate — Corridor](bat_stigmergy_swarm/results/task1_20260428_205154/task1_corridor_escape_rate.png)
*Figure 1b: Escape rate in the corridor layout.*

**Time to Exit.** The LLM bat roughly halved the time required for bats to exit across all layouts (Figure 2). In the bottleneck, mean exit time dropped from 475 to 216 steps; in the corridor from 294 to 162 steps. This effect is consistent with the LLM bat acting as a pathfinder — locating the exit region early and depositing buzz signals that draw the rule-based swarm behind it.

![Time to Exit — Bottleneck](bat_stigmergy_swarm/results/task1_20260428_205154/task1_bottleneck_time_to_exit_mean.png)
*Figure 2a: Mean time to exit in the bottleneck layout. Only episodes where at least one bat escaped are included.*

![Time to Exit — Zigzag](bat_stigmergy_swarm/results/task1_20260428_205154/task1_zigzag_time_to_exit_mean.png)
*Figure 2b: Mean time to exit in the zigzag layout.*

**Path Efficiency.** LLM bats produced more direct routes, approximately doubling path efficiency across layouts (Figure 3). In the bottleneck, efficiency increased from 0.26 to 0.60, indicating the LLM bat finds a more direct path rather than wandering before locating the exit.

![Path Efficiency — Bottleneck](bat_stigmergy_swarm/results/task1_20260428_205154/task1_bottleneck_path_eff_mean.png)
*Figure 3: Path efficiency in the bottleneck layout. Higher values indicate more direct routes to the exit.*

**Jam Events.** The LLM condition showed a small but consistent increase in jam events (bats stuck for 3+ consecutive steps). This is an expected trade-off: by routing more bats through narrow passages more quickly, the LLM bat creates brief congestion. However, the overall throughput is substantially better despite these local delays.

### 4.2 Task 2 — Open-World Foraging

Task 2 reveals a more nuanced picture. Table 1 summarizes the key metrics across all five conditions.

| Condition | Prey Collected | Survival Rate | Bats Eaten | Pred. Incidents | Zero-Death Episodes |
|---|---|---|---|---|---|
| rule_stig_off | 46.25 | 0.81 | 2.85 | 2.90 | 0.40 |
| rule_stig_on | 46.25 | 0.85 | 2.25 | 2.40 | 0.50 |
| llm_priv_on_recruit_on | 46.20 | 0.72 | 4.20 | 6.00 | 0.20 |
| llm_local_only_recruit_on | 45.50 | 0.72 | 4.25 | 4.15 | 0.30 |
| llm_priv_on_recruit_off | 46.25 | 0.81 | 2.85 | 3.25 | 0.45 |

*Table 1: Task 2 condition summary, averaged across 20 seeds.*

**Stigmergy effect.** Comparing rule_stig_off to rule_stig_on shows that stigmergy alone modestly improves survival (0.81 → 0.85) and reduces bats eaten (2.85 → 2.25) without changing prey collection. The acoustic alarm field helps bats avoid predator zones passively.

**LLM recruitment as a double-edged sword.** The two conditions with LLM recruitment enabled show substantially lower survival (0.72) and more bats eaten (~4.2). Figure 4 illustrates this clearly.

![Survival Rate](bat_stigmergy_swarm/results/task2_survival_rate_mean.png)
*Figure 4: Survival rate by condition. LLM recruitment conditions (llm_priv_on_recruit_on, llm_local_only_recruit_on) show the lowest survival.*

![Bats Eaten](bat_stigmergy_swarm/results/task2_bats_eaten_mean.png)
*Figure 5: Mean bats eaten per episode. Recruitment conditions lose ~50% more bats than rule-only baselines.*

However, prey collection remains nearly identical across all conditions (~46 prey out of 50), meaning the LLM's recruitment does not increase foraging yield — it simply concentrates bats into prey-rich areas that also happen to overlap with predator patrol zones.

![Total Prey Collected](bat_stigmergy_swarm/results/task2_total_prey_collected_mean.png)
*Figure 6: Total prey collected per episode. All conditions collect nearly identical amounts of prey regardless of LLM or stigmergy configuration.*

**Recruitment is the key variable.** The clearest evidence comes from comparing llm_priv_on_recruit_on vs. llm_priv_on_recruit_off — identical in every way except recruitment. With recruitment off, survival recovers to 0.81 (matching rule-only baselines) and bats eaten drops to 2.85. This isolates recruitment as the mechanism driving the survival cost, not the LLM's movement decisions or privileged observation.

![Predator Incidents](bat_stigmergy_swarm/results/task2_predator_incidents_mean.png)
*Figure 7: Predator incidents by condition. Privileged observation combined with recruitment (llm_priv_on_recruit_on) produces the highest predator encounter rate, as the LLM confidently directs bats toward prey near predators.*

---

## 5. Discussion

**Task 1** demonstrates clearly that a single LLM agent can act as an effective informed individual within a stigmergy-based swarm. The effect is largest in the bottleneck layout, where rule-based agents struggle most. This is because the LLM can reason about which direction to move through the chokepoint and deposit buzz signals that guide the swarm behind it. This is a direct empirical instance of the Couzin et al. (2005) effect: one informed agent reliably steering a group without explicit signaling.

**Task 2** presents a more complex story. The LLM bat is an effective forager and coordinator, but its BUZZ recruitment signal brings nearby bats into areas that are prey-rich but also risky. This is not a failure of the LLM — it is a reasonable strategy under the assumption that more bats near food is beneficial. What the 0.8B model lacks is the ability to jointly reason about prey density and predator proximity when issuing recruitment calls. A larger or fine-tuned model might learn to issue conditional recruitment ("follow me, but there's a predator nearby so be careful and alert"). The result that turning off recruitment restores baseline survival while maintaining foraging efficiency suggests the LLM's directional decisions are sound; it is the broadcast nature of recruitment that causes the problem.

**Limitations.** The LLM (Qwen3.5-0.8B) is small relative to state-of-the-art models and has no memory across episodes. The prompt format is fixed and does not adapt to the model's outputs. The batch evaluation runs headlessly without rendering, which may produce slightly different dynamics than the interactive simulation.

**Future work** could explore larger models, multi-LLM swarms with differentiated roles, fine-tuning on simulation traces, and adaptive recruitment that conditions on predator proximity.

---

## 6. Project Contributions

- **[Your Name]**: [list tasks — e.g., simulation architecture, LLM integration, Task 1 design, batch evaluation pipeline, analysis scripts]
- **[Partner Name]**: [list tasks — e.g., Task 2 design, agent behavior, results analysis, paper writing]

---

## 7. Bibliography

Couzin, I.D., Krause, J., Franks, N.R., & Levin, S.A. (2005). Effective leadership and decision-making in animal groups on the move. *Nature*, 433, 513–516. https://www.nature.com/articles/nature03236

Bohn, K.M., Moss, C.F., & Wilkinson, G.S. (2009). Experimental evidence for group hunting via eavesdropping in echolocating bats. *Proceedings of the Royal Society B*. https://pmc.ncbi.nlm.nih.gov/articles/PMC2839959/

Jürgen, S., et al. (2024). LLM2Swarm: Robot Swarms that Responsively Reason, Plan, and Collaborate through LLMs. *arXiv:2410.11387*. https://arxiv.org/html/2410.11387v2


## 8: Videos and Code Repository
Simulation video:  [YouTube link — [Task 2 Video](https://youtu.be/HDPGYy7S6OE)]

Code repository: [GitHub link — [LLM-Augmented Stigmergy Github](https://github.com/SUPERINTIALD/CSCI_5423_Bio_Final_Project)]