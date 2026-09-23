import csv
import statistics
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent

RESULTS_FILE = (
    PROJECT_ROOT
    / "ml"
    / "results"
    / "controller_comparison.csv"
)


def load_results():
    with open(
        RESULTS_FILE,
        "r",
        encoding="utf-8"
    ) as file:
        return list(csv.DictReader(file))


def get_values(results, key):
    return [
        float(row[key])
        for row in results
    ]


def summarize(name, values):
    print(f"\n{name}")
    print("-" * 50)

    print(f"Mean:   {statistics.mean(values):.3f}")
    print(f"Median: {statistics.median(values):.3f}")
    print(f"Std:    {statistics.stdev(values):.3f}")
    print(f"Min:    {min(values):.3f}")
    print(f"Max:    {max(values):.3f}")


def main():

    results = load_results()

    print("=" * 70)
    print("CONTROLLER EXPERIMENT STATISTICAL ANALYSIS")
    print("=" * 70)

    print(f"\nScenarios analyzed: {len(results)}")

    # --------------------------------------------------------
    # Extract data
    # --------------------------------------------------------

    baseline_throughput = get_values(
        results,
        "baseline_throughput"
    )

    ai_throughput = get_values(
        results,
        "ai_throughput"
    )

    baseline_waiting = get_values(
        results,
        "baseline_waiting"
    )

    ai_waiting = get_values(
        results,
        "ai_waiting"
    )

    baseline_conflicts = get_values(
        results,
        "baseline_conflicts"
    )

    ai_conflicts = get_values(
        results,
        "ai_conflicts"
    )

    # --------------------------------------------------------
    # Summary statistics
    # --------------------------------------------------------

    summarize(
        "BASELINE THROUGHPUT",
        baseline_throughput
    )

    summarize(
        "AI THROUGHPUT",
        ai_throughput
    )

    summarize(
        "BASELINE WAITING TIME",
        baseline_waiting
    )

    summarize(
        "AI WAITING TIME",
        ai_waiting
    )

    summarize(
        "BASELINE CONFLICTS",
        baseline_conflicts
    )

    summarize(
        "AI CONFLICTS",
        ai_conflicts
    )

    # --------------------------------------------------------
    # Scenario-by-scenario comparison
    # --------------------------------------------------------

    throughput_wins = 0
    throughput_ties = 0
    throughput_losses = 0

    waiting_wins = 0
    waiting_ties = 0
    waiting_losses = 0

    conflict_wins = 0
    conflict_ties = 0
    conflict_losses = 0

    throughput_improvements = []
    waiting_reductions = []
    conflict_reductions = []

    for row in results:

        b_tp = float(row["baseline_throughput"])
        a_tp = float(row["ai_throughput"])

        b_wait = float(row["baseline_waiting"])
        a_wait = float(row["ai_waiting"])

        b_conf = float(row["baseline_conflicts"])
        a_conf = float(row["ai_conflicts"])

        # Throughput
        if a_tp > b_tp:
            throughput_wins += 1
        elif a_tp == b_tp:
            throughput_ties += 1
        else:
            throughput_losses += 1

        # Waiting
        if a_wait < b_wait:
            waiting_wins += 1
        elif a_wait == b_wait:
            waiting_ties += 1
        else:
            waiting_losses += 1

        # Conflicts
        if a_conf < b_conf:
            conflict_wins += 1
        elif a_conf == b_conf:
            conflict_ties += 1
        else:
            conflict_losses += 1

        # Percentage changes
        if b_tp > 0:
            throughput_improvements.append(
                ((a_tp - b_tp) / b_tp) * 100
            )

        if b_wait > 0:
            waiting_reductions.append(
                ((b_wait - a_wait) / b_wait) * 100
            )

        if b_conf > 0:
            conflict_reductions.append(
                ((b_conf - a_conf) / b_conf) * 100
            )

    # --------------------------------------------------------
    # Win / tie / loss
    # --------------------------------------------------------

    print("\n" + "=" * 70)
    print("SCENARIO-BY-SCENARIO RESULTS")
    print("=" * 70)

    print("\nTHROUGHPUT")
    print(f"AI wins:   {throughput_wins}")
    print(f"Ties:      {throughput_ties}")
    print(f"AI loses:  {throughput_losses}")

    print("\nWAITING TIME")
    print(f"AI better: {waiting_wins}")
    print(f"Ties:      {waiting_ties}")
    print(f"AI worse:  {waiting_losses}")

    print("\nCONFLICTS")
    print(f"AI better: {conflict_wins}")
    print(f"Ties:      {conflict_ties}")
    print(f"AI worse:  {conflict_losses}")

    # --------------------------------------------------------
    # Per-scenario improvement statistics
    # --------------------------------------------------------

    print("\n" + "=" * 70)
    print("PER-SCENARIO IMPROVEMENT")
    print("=" * 70)

    if throughput_improvements:
        summarize(
            "THROUGHPUT IMPROVEMENT (%)",
            throughput_improvements
        )

    if waiting_reductions:
        summarize(
            "WAITING-TIME REDUCTION (%)",
            waiting_reductions
        )

    if conflict_reductions:
        summarize(
            "CONFLICT REDUCTION (%)",
            conflict_reductions
        )

    print("\n" + "=" * 70)
    print("ANALYSIS COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()