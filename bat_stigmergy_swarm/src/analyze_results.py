import os
import pandas as pd
import matplotlib.pyplot as plt


def summarize_and_plot(input_csv, out_prefix):
    os.makedirs("results", exist_ok=True)

    df = pd.read_csv(input_csv)

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
          )
          .reset_index()
    )

    summary_csv = os.path.join("results", f"{out_prefix}_summary.csv")
    summary.to_csv(summary_csv, index=False)
    print(f"Saved {summary_csv}")

    metrics = [
        ("total_prey_collected_mean", "total_prey_collected_std", "Total Prey Collected"),
        ("predator_incidents_mean", "predator_incidents_std", "Predator Incidents"),
        ("survival_rate_mean", "survival_rate_std", "Survival Rate"),
        ("time_to_first_prey_mean", "time_to_first_prey_std", "Time to First Prey"),
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