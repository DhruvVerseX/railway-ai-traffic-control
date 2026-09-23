import csv
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
RESULTS_FILE = PROJECT_ROOT / "ml" / "results" / "controller_comparison.csv"


def main():
    if not RESULTS_FILE.exists():
        raise FileNotFoundError(f"Results file not found: {RESULTS_FILE}")

    with open(RESULTS_FILE, "r", newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    losses = []

    for row in rows:
        baseline_tp = float(row["baseline_throughput"])
        ai_tp = float(row["ai_throughput"])

        if ai_tp < baseline_tp:
            losses.append(row)

    print("=" * 75)
    print("AI THROUGHPUT LOSS ANALYSIS")
    print("=" * 75)

    print(f"Total scenarios: {len(rows)}")
    print(f"AI throughput losses: {len(losses)}")
    print()

    for row in losses:
        print(
            f"Seed {row['seed']:>3} | "
            f"Baseline TP: {float(row['baseline_throughput']):.2f} | "
            f"AI TP: {float(row['ai_throughput']):.2f} | "
            f"Baseline waiting: {float(row['baseline_waiting']):.2f} | "
            f"AI waiting: {float(row['ai_waiting']):.2f} | "
            f"Baseline conflicts: {int(float(row['baseline_conflicts']))} | "
            f"AI conflicts: {int(float(row['ai_conflicts']))}"
        )

    print()
    print("=" * 75)
    print("AVERAGE OF LOSS SCENARIOS")
    print("=" * 75)

    def avg(column):
        return sum(float(row[column]) for row in losses) / len(losses)

    print(f"Baseline throughput : {avg('baseline_throughput'):.3f}")
    print(f"AI throughput       : {avg('ai_throughput'):.3f}")
    print(f"Baseline waiting    : {avg('baseline_waiting'):.2f}")
    print(f"AI waiting          : {avg('ai_waiting'):.2f}")
    print(f"Baseline conflicts  : {avg('baseline_conflicts'):.2f}")
    print(f"AI conflicts        : {avg('ai_conflicts'):.2f}")

    print()
    print("=" * 75)
    print("DONE")
    print("=" * 75)


if __name__ == "__main__":
    main()