import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from simulation.network import RailwayNetwork
from input.input_state import TrainDatabase
from controller.ml_controller import MLTrainController
from scenarios.mixed_scenario_builder import MixedScenarioBuilder
from simulation.simulator import RailwaySimulator


# ============================================================
# PATHS
# ============================================================

V2_MODEL = (
    PROJECT_ROOT
    / "ml"
    / "models"
    / "train_controller_v2.pkl"
)

V3_MODEL = (
    PROJECT_ROOT
    / "ml"
    / "models"
    / "train_controller_v3.pkl"
)


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
# GENERATE EXACT SAME SEED-66 SCENARIO
# ============================================================

traffic_state = builder.generate_mixed_scenario(
    scenario_id="COMPARE66",
    num_trains=6,
    scenario_type="competition",
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

# Move to the first decision point.
simulator.advance_time(5.0)


# ============================================================
# CREATE V2 + V3 CONTROLLERS
# ============================================================

v2_controller = MLTrainController(
    network,
    database,
    model_path=V2_MODEL
)

v3_controller = MLTrainController(
    network,
    database,
    model_path=V3_MODEL
)


# ============================================================
# GET ELIGIBLE TRAINS
# ============================================================

eligible_trains = []

for train_id, train in simulator.trains.items():

    if train.status != "WAITING":
        continue

    if (
        simulator.current_time_min
        < train.entry_time_min
    ):
        continue

    eligible_trains.append(
        train_id
    )


# ============================================================
# PRINT COMPARISON
# ============================================================

print()
print("=" * 70)
print("V2 vs V3 MODEL COMPARISON — SEED 66")
print("=" * 70)

print(
    f"\nSimulation time: "
    f"{simulator.current_time_min:.2f} min"
)

print(
    f"Eligible trains: "
    f"{eligible_trains}"
)


for train_id in eligible_trains:

    v2 = v2_controller.predict_train(
        simulator,
        train_id
    )

    v3 = v3_controller.predict_train(
        simulator,
        train_id
    )

    print()
    print("-" * 70)

    print(
        f"TRAIN: {train_id}"
    )

    print(
        f"Next section: "
        f"{v2['next_section']}"
    )

    print()

    print("V2:")

    print(
        f"  Action: "
        f"{v2['action']}"
    )

    print(
        f"  HOLD probability: "
        f"{v2['probabilities'].get('HOLD', 0):.4f}"
    )

    print(
        f"  RELEASE probability: "
        f"{v2['probabilities'].get('RELEASE', 0):.4f}"
    )

    print()

    print("V3:")

    print(
        f"  Action: "
        f"{v3['action']}"
    )

    print(
        f"  HOLD probability: "
        f"{v3['probabilities'].get('HOLD', 0):.4f}"
    )

    print(
        f"  RELEASE probability: "
        f"{v3['probabilities'].get('RELEASE', 0):.4f}"
    )


print()
print("=" * 70)
print("COMPARISON COMPLETE")
print("=" * 70)