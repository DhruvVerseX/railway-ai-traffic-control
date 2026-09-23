import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

input_file = (
    PROJECT_ROOT
    / "evaluation"
    / "results"
    / "final_v2_evaluation.csv"
)

output_dir = (
    PROJECT_ROOT
    / "evaluation"
    / "results"
    / "plots"
)

output_dir.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# LOAD DATA
# ============================================================

df = pd.read_csv(input_file)

print("=" * 60)
print("FINAL RESULTS VISUALIZATION")
print("=" * 60)

print(f"\nLoaded {len(df)} scenarios.")

print(f"Input file:\n{input_file}")


# ============================================================
# CALCULATE AVERAGES
# ============================================================

baseline_throughput = df[
    "baseline_throughput"
].mean()

ai_throughput = df[
    "ai_throughput"
].mean()

baseline_waiting = df[
    "baseline_waiting"
].mean()

ai_waiting = df[
    "ai_waiting"
].mean()

baseline_conflicts = df[
    "baseline_conflicts"
].mean()

ai_conflicts = df[
    "ai_conflicts"
].mean()


# ============================================================
# 1. THROUGHPUT COMPARISON
# ============================================================

plt.figure(figsize=(8, 6))

plt.bar(
    ["Baseline", "V2 AI"],
    [
        baseline_throughput,
        ai_throughput
    ]
)

plt.ylabel("Throughput (trains/hour)")
plt.title("Average Section Throughput")

plt.tight_layout()

plt.savefig(
    output_dir / "01_throughput_comparison.png",
    dpi=300
)

plt.close()


# ============================================================
# 2. CONFLICT COMPARISON
# ============================================================

plt.figure(figsize=(8, 6))

plt.bar(
    ["Baseline", "V2 AI"],
    [
        baseline_conflicts,
        ai_conflicts
    ]
)

plt.ylabel("Average conflicts")
plt.title("Average Detected Conflicts")

plt.tight_layout()

plt.savefig(
    output_dir / "02_conflict_comparison.png",
    dpi=300
)

plt.close()


# ============================================================
# 3. WAITING TIME COMPARISON
# ============================================================

plt.figure(figsize=(8, 6))

plt.bar(
    ["Baseline", "V2 AI"],
    [
        baseline_waiting,
        ai_waiting
    ]
)

plt.ylabel("Total waiting time (min)")
plt.title("Average Total Waiting Time")

plt.tight_layout()

plt.savefig(
    output_dir / "03_waiting_comparison.png",
    dpi=300
)

plt.close()


# ============================================================
# 4. THROUGHPUT ACROSS ALL SCENARIOS
# ============================================================

plt.figure(figsize=(12, 6))

plt.plot(
    df["scenario"],
    df["baseline_throughput"],
    label="Baseline"
)

plt.plot(
    df["scenario"],
    df["ai_throughput"],
    label="V2 AI"
)

plt.xlabel("Scenario")
plt.ylabel("Throughput (trains/hour)")
plt.title("Throughput Across 100 Scenarios")

plt.legend()

plt.tight_layout()

plt.savefig(
    output_dir / "04_throughput_all_scenarios.png",
    dpi=300
)

plt.close()


# ============================================================
# 5. CONFLICTS ACROSS ALL SCENARIOS
# ============================================================

plt.figure(figsize=(12, 6))

plt.plot(
    df["scenario"],
    df["baseline_conflicts"],
    label="Baseline"
)

plt.plot(
    df["scenario"],
    df["ai_conflicts"],
    label="V2 AI"
)

plt.xlabel("Scenario")
plt.ylabel("Detected conflicts")
plt.title("Conflicts Across 100 Scenarios")

plt.legend()

plt.tight_layout()

plt.savefig(
    output_dir / "05_conflicts_all_scenarios.png",
    dpi=300
)

plt.close()


# ============================================================
# 6. COMPLETED TRAINS COMPARISON
# ============================================================

baseline_completed = df[
    "baseline_completed"
].mean()

ai_completed = df[
    "ai_completed"
].mean()

plt.figure(figsize=(8, 6))

plt.bar(
    ["Baseline", "V2 AI"],
    [
        baseline_completed,
        ai_completed
    ]
)

plt.ylabel("Average completed trains")
plt.title("Average Completed Trains")

plt.tight_layout()

plt.savefig(
    output_dir / "06_completed_trains_comparison.png",
    dpi=300
)

plt.close()


# ============================================================
# SUMMARY
# ============================================================

print("\nAverage values used for plots:")

print(
    f"\nThroughput:"
    f"\n  Baseline = {baseline_throughput:.4f}"
    f"\n  V2 AI    = {ai_throughput:.4f}"
)

print(
    f"\nWaiting:"
    f"\n  Baseline = {baseline_waiting:.2f} min"
    f"\n  V2 AI    = {ai_waiting:.2f} min"
)

print(
    f"\nConflicts:"
    f"\n  Baseline = {baseline_conflicts:.2f}"
    f"\n  V2 AI    = {ai_conflicts:.2f}"
)

print(
    f"\nCompleted trains:"
    f"\n  Baseline = {baseline_completed:.2f}"
    f"\n  V2 AI    = {ai_completed:.2f}"
)

print("\nPlots saved to:")
print(output_dir)

print("\n" + "=" * 60)
print("VISUALIZATION COMPLETE")
print("=" * 60)