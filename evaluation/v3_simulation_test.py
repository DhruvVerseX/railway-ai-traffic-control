import os

os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from simulation.network import RailwayNetwork
from simulation.simulator import RailwaySimulator
from simulation.conflict_detector import ConflictDetector
from input.input_state import TrainDatabase
from scenarios.mixed_scenario_builder import MixedScenarioBuilder
from controller.ai_controller import AITrainTrafficController
from metrics.metrics import SimulationMetrics
from controller.ml_controller import MLTrainController


# ============================================================
# CONFIGURATION
# ============================================================

V3_MODEL_PATH = (
    PROJECT_ROOT
    / "ml"
    / "models"
    / "train_controller_v3.pkl"
)

HORIZON_MIN = 240.0
DECISION_INTERVAL_MIN = 5.0


# ============================================================
# LOAD SYSTEM
# ============================================================

network = RailwayNetwork()
database = TrainDatabase()

builder = MixedScenarioBuilder(
    network,
    database
)


# ============================================================
# GENERATE SEED 66 SCENARIO
# ============================================================

traffic_state = builder.generate_mixed_scenario(
    scenario_id="V3_TEST_66",
    num_trains=6,
    scenario_type="competition",
    decision_time_min=5.0,
    running_advance_min=5.0,
    seed=66
)


# ============================================================
# CREATE SIMULATOR
# ============================================================

simulator = RailwaySimulator(
    network
)

simulator.load_traffic(
    traffic_state,
    database
)


# ============================================================
# CREATE V3 ML CONTROLLER
# ============================================================

# We create the ML controller explicitly with V3,
# so the existing controller does not need to be modified.

ml_controller = MLTrainController(
    network,
    database,
    model_path=V3_MODEL_PATH
)


# ============================================================
# CREATE AI SAFETY CONTROLLER
# ============================================================

controller = AITrainTrafficController(
    network,
    database
)

# Replace its default V2 model with V3.
controller.ai_safety_controller.ml_controller = (
    ml_controller
)


# ============================================================
# INITIAL INFORMATION
# ============================================================

print()
print("=" * 70)
print("V3 AI SIMULATION TEST — SEED 66")
print("=" * 70)

print()
print("Initial traffic state:")

for train_id, train in simulator.trains.items():

    print(
        f"{train_id}: "
        f"status={train.status}, "
        f"station={train.current_station}, "
        f"entry={train.entry_time_min:.2f}, "
        f"delay={train.delay_min:.2f}"
    )


# ============================================================
# SIMULATION LOOP
# ============================================================

decision_count = 0
release_count = 0

while (
    simulator.current_time_min
    < HORIZON_MIN
):

    # --------------------------------------------------------
    # ADVANCE TO NEXT DECISION TIME
    # --------------------------------------------------------

    remaining = (
        HORIZON_MIN
        - simulator.current_time_min
    )

    advance_amount = min(
        DECISION_INTERVAL_MIN,
        remaining
    )

    simulator.advance_time(
        advance_amount
    )

    if (
        simulator.current_time_min
        >= HORIZON_MIN
    ):
        break

    decision_count += 1

    # --------------------------------------------------------
    # AI CONTROL STEP
    # --------------------------------------------------------

    decision = controller.control_step(
        simulator
    )

    selected = decision.get(
        "selected_action"
    )

    print()
    print(
        f"[t={simulator.current_time_min:.2f}]"
    )

    if selected is None:

        print(
            "  No action selected."
        )

        continue

    train_id = selected.get(
        "train_id"
    )

    final_action = selected.get(
        "final_action"
    )

    ml_action = selected.get(
        "ml_action"
    )

    probabilities = selected.get(
        "probabilities",
        {}
    )

    print(
        f"  Train: {train_id}"
    )

    print(
        f"  ML action: {ml_action}"
    )

    print(
        f"  Final action: {final_action}"
    )

    print(
        f"  RELEASE probability: "
        f"{probabilities.get('RELEASE', 0.0):.4f}"
    )

    print(
        f"  HOLD probability: "
        f"{probabilities.get('HOLD', 0.0):.4f}"
    )

    print(
        f"  Next section: "
        f"{selected.get('next_section')}"
    )

    if final_action == "RELEASE":

        release_count += 1


# ============================================================
# FINAL METRICS
# ============================================================

metrics_engine = SimulationMetrics(
    simulator
)

metrics = metrics_engine.calculate_all()


# ============================================================
# FINAL RESULTS
# ============================================================

print()
print("=" * 70)
print("V3 FINAL RESULTS — SEED 66")
print("=" * 70)

print(
    f"\nDecision steps: "
    f"{decision_count}"
)

print(
    f"RELEASE decisions: "
    f"{release_count}"
)

print(
    f"Completed trains: "
    f"{metrics['completed_trains']}"
)

print(
    f"Throughput: "
    f"{metrics['throughput_trains_per_hour']:.2f} "
    f"trains/hour"
)

print(
    f"Total waiting time: "
    f"{metrics['total_waiting_time_min']:.2f} min"
)

print(
    f"Average waiting time: "
    f"{metrics['average_waiting_time_min']:.2f} min"
)

print(
    f"Initial delay: "
    f"{metrics['initial_delay_min']:.2f} min"
)

print(
    f"Conflicts: "
    f"{metrics['conflicts']}"
)


# ============================================================
# FINAL TRAIN STATES
# ============================================================

print()
print("=" * 70)
print("FINAL TRAIN STATES")
print("=" * 70)

for train_id, train in simulator.trains.items():

    print(
        f"{train_id}: "
        f"status={train.status}, "
        f"station={train.current_station}, "
        f"section={train.current_section}, "
        f"section_index={train.section_index}"
    )


print()
print("=" * 70)
print("V3 TEST COMPLETE")
print("=" * 70)