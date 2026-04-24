import os
import pandas as pd
import matplotlib.pyplot as plt


def summarize_and_plot(input_csv, out_prefix):
    os.makedirs("results", exist_ok=True)

    df = pd.read_csv(input_csv)

    condition_order = [
        "rule_stig_off",
        "rule_stig_on",
        "llm_priv_on_recruit_on",
        "llm_local_only_recruit_on",
        "llm_priv_on_recruit_off",
    ]
    df["condition"] = pd.Categorical(df["condition"], categories=condition_order, ordered=True)
    df = df.sort_values("condition")

    summary = (
        df.groupby("condition")
        .agg(
            total_prey_collected_mean=("total_prey_collected", "mean"),
            total_prey_collected_std=("total_prey_collected", "std"),

            predator_incidents_mean=("predator_incidents", "mean"),
            predator_incidents_std=("predator_incidents", "std"),

            survival_rate_mean=("survival_rate", "mean"),
            survival_rate_std=("survival_rate", "std"),

            time_to_first_prey_mean=("time_to_first_prey", "mean"),
            time_to_first_prey_std=("time_to_first_prey", "std"),

            prey_completion_rate_mean=("prey_completion_rate", "mean"),
            prey_completion_rate_std=("prey_completion_rate", "std"),

            all_prey_collected_mean=("all_prey_collected", "mean"),
            all_prey_collected_std=("all_prey_collected", "std"),

            time_to_all_prey_mean=("time_to_all_prey", "mean"),
            time_to_all_prey_std=("time_to_all_prey", "std"),

            bats_eaten_mean=("bats_eaten", "mean"),
            bats_eaten_std=("bats_eaten", "std"),

            llm_survived_mean=("llm_survived", "mean"),
            llm_survived_std=("llm_survived", "std"),

            timeout_mean=("timeout", "mean"),
            timeout_std=("timeout", "std"),

            episodes_with_zero_deaths_mean=("episodes_with_zero_deaths", "mean"),
            episodes_with_zero_deaths_std=("episodes_with_zero_deaths", "std"),
        )
        .reset_index()
    )

    summary_csv = os.path.join("results", f"{out_prefix}_summary.csv")
    summary.to_csv(summary_csv, index=False)
    print(f"Saved {summary_csv}")

    summary = summary.fillna(0)

    metrics = [
        ("total_prey_collected_mean", "total_prey_collected_std", "Total Prey Collected"),
        ("predator_incidents_mean", "predator_incidents_std", "Predator Incidents"),
        ("survival_rate_mean", "survival_rate_std", "Survival Rate"),
        ("time_to_first_prey_mean", "time_to_first_prey_std", "Time to First Prey"),
        ("prey_completion_rate_mean", "prey_completion_rate_std", "Prey Completion Rate"),
        ("all_prey_collected_mean", "all_prey_collected_std", "All Prey Collected Rate"),
        ("time_to_all_prey_mean", "time_to_all_prey_std", "Time to All Prey"),
        ("bats_eaten_mean", "bats_eaten_std", "Bats Eaten"),
        ("llm_survived_mean", "llm_survived_std", "LLM Survived Rate"),
        ("timeout_mean", "timeout_std", "Timeout Rate"),
        ("episodes_with_zero_deaths_mean", "episodes_with_zero_deaths_std", "Zero-Death Episode Rate"),
    ]

    for mean_col, std_col, title in metrics:
        plt.figure(figsize=(10, 5))
        plt.bar(summary["condition"], summary[mean_col], yerr=summary[std_col], capsize=5)
        plt.xticks(rotation=25, ha="right")
        plt.ylabel(title)
        plt.title(f"{title} by Condition")
        plt.tight_layout()

        out_png = os.path.join("results", f"{out_prefix}_{mean_col}.png")
        plt.savefig(out_png, dpi=160)
        plt.close()
        print(f"Saved {out_png}")


if __name__ == "__main__":
    summarize_and_plot("results/task2_results.csv", "task2")