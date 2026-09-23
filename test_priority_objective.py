import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from optimizer.objective import OptimizationObjective


objective = OptimizationObjective()


metrics = {
    "throughput_trains_per_hour": 1.0,
    "total_waiting_time_min": 100.0,
    "initial_delay_min": 10.0,
    "conflicts": 0,
}


high_priority_action = {
    "train_id": "T001",
    "action": "RELEASE",
    "section_id": "S03",
    "priority": 5,
}


low_priority_action = {
    "train_id": "T029",
    "action": "RELEASE",
    "section_id": "S03",
    "priority": 1,
}


hold_action = {
    "train_id": "T001",
    "action": "HOLD",
    "section_id": "S03",
    "priority": 5,
}


print("=== PRIORITY OBJECTIVE TEST ===")

print(
    "\nHigh-priority RELEASE score:",
    objective.calculate_score(
        metrics,
        high_priority_action
    )
)

print(
    "Low-priority RELEASE score:",
    objective.calculate_score(
        metrics,
        low_priority_action
    )
)

print(
    "High-priority HOLD score:",
    objective.calculate_score(
        metrics,
        hold_action
    )
)


print("\n=== SCORE EXPLANATION ===")

print(
    objective.explain_score(
        metrics,
        high_priority_action
    )
)