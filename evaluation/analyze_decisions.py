import csv
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent

RESULTS_FILE = (
    PROJECT_ROOT
    / "ml"
    / "results"
    / "controller_comparison.csv"
)


def main():

    with open(
        RESULTS_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        results = list(
            csv.DictReader(file)
        )

    print("=" * 70)
    print("CONTROLLER DECISION ANALYSIS")
    print("=" * 70)

    print(
        f"\nScenarios analyzed: {len(results)}"
    )

    # --------------------------------------------------------
    # Aggregate decision counts
    # --------------------------------------------------------

    baseline_release = sum(
        int(row["baseline_release_decisions"])
        for row in results
    )

    ai_release = sum(
        int(row["ai_release_decisions"])
        for row in results
    )

    baseline_hold = sum(
        int(row["baseline_hold_decisions"])
        for row in results
    )

    ai_hold = sum(
        int(row["ai_hold_decisions"])
        for row in results
    )

    baseline_total = sum(
        int(row["baseline_total_decisions"])
        for row in results
    )

    ai_total = sum(
        int(row["ai_total_decisions"])
        for row in results
    )

    # --------------------------------------------------------
    # Release / HOLD rates
    # --------------------------------------------------------

    baseline_release_rate = (
        baseline_release / baseline_total * 100
        if baseline_total > 0
        else 0
    )

    ai_release_rate = (
        ai_release / ai_total * 100
        if ai_total > 0
        else 0
    )

    baseline_hold_rate = (
        baseline_hold / baseline_total * 100
        if baseline_total > 0
        else 0
    )

    ai_hold_rate = (
        ai_hold / ai_total * 100
        if ai_total > 0
        else 0
    )

    # --------------------------------------------------------
    # Decision statistics
    # --------------------------------------------------------

    print("\n" + "=" * 70)
    print("DECISION COUNTS")
    print("=" * 70)

    print("\nBASELINE")
    print("-" * 50)

    print(
        f"RELEASE decisions: {baseline_release}"
    )

    print(
        f"HOLD decisions:    {baseline_hold}"
    )

    print(
        f"Total decisions:    {baseline_total}"
    )

    print(
        f"RELEASE rate:       {baseline_release_rate:.2f}%"
    )

    print(
        f"HOLD rate:          {baseline_hold_rate:.2f}%"
    )

    print("\nAI")
    print("-" * 50)

    print(
        f"RELEASE decisions: {ai_release}"
    )

    print(
        f"HOLD decisions:    {ai_hold}"
    )

    print(
        f"Total decisions:    {ai_total}"
    )

    print(
        f"RELEASE rate:       {ai_release_rate:.2f}%"
    )

    print(
        f"HOLD rate:          {ai_hold_rate:.2f}%"
    )

    # --------------------------------------------------------
    # Average decisions per scenario
    # --------------------------------------------------------

    scenario_count = len(results)

    print("\n" + "=" * 70)
    print("AVERAGE DECISIONS PER SCENARIO")
    print("=" * 70)

    print(
        f"\nBaseline RELEASE: "
        f"{baseline_release / scenario_count:.2f}"
    )

    print(
        f"AI RELEASE:       "
        f"{ai_release / scenario_count:.2f}"
    )

    print(
        f"\nBaseline HOLD:    "
        f"{baseline_hold / scenario_count:.2f}"
    )

    print(
        f"AI HOLD:          "
        f"{ai_hold / scenario_count:.2f}"
    )

    # --------------------------------------------------------
    # Difference
    # --------------------------------------------------------

    release_difference = (
        ai_release - baseline_release
    )

    hold_difference = (
        ai_hold - baseline_hold
    )

    print("\n" + "=" * 70)
    print("AI vs BASELINE DECISION DIFFERENCE")
    print("=" * 70)

    print(
        f"\nDifference in RELEASE decisions: "
        f"{release_difference:+d}"
    )

    print(
        f"Difference in HOLD decisions:    "
        f"{hold_difference:+d}"
    )

    # --------------------------------------------------------
    # Interpretation
    # --------------------------------------------------------

    print("\n" + "=" * 70)
    print("INTERPRETATION")
    print("=" * 70)

    if ai_release_rate < baseline_release_rate:

        print(
            "\nAI releases trains less frequently "
            "than the baseline."
        )

        print(
            "This suggests the AI may be more conservative."
        )

    elif ai_release_rate > baseline_release_rate:

        print(
            "\nAI releases trains more frequently "
            "than the baseline."
        )

        print(
            "This suggests the AI is more aggressive "
            "with train releases."
        )

    else:

        print(
            "\nAI and baseline have the same release rate."
        )

    print(
        "\nThe next analysis will determine whether "
        "these different decisions actually correspond "
        "to better throughput, waiting time, and conflict "
        "performance."
    )

    print("\n" + "=" * 70)
    print("ANALYSIS COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()