import os

# Prevent excessive parallel threads from
# scikit-learn / OpenBLAS on some systems.
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from input.input_state import TrainDatabase
from simulation.network import RailwayNetwork
from simulation.simulator import RailwaySimulator
from scenarios.mixed_scenario_builder import MixedScenarioBuilder
from controller.ai_controller import AITrainTrafficController


# ============================================================
# SETUP
# ============================================================

network = RailwayNetwork()
database = TrainDatabase()

builder = MixedScenarioBuilder(
    network,
    database
)

traffic_state = builder.generate_mixed_scenario(
    scenario_id="AI_DIAGNOSTIC",
    num_trains=6,
    scenario_type="competition",
    decision_time_min=5.0,
    running_advance_min=5.0,
    seed=42
)

simulator = RailwaySimulator(network)

simulator.load_traffic(
    traffic_state,
    database
)

controller = AITrainTrafficController(
    network,
    database
)


# ============================================================
# ADVANCE TO FIRST DECISION POINT
# ============================================================

simulator.advance_time(5.0)


# ============================================================
# GET RECOMMENDATIONS
# ============================================================

decision = controller.make_decision(
    simulator
)


# ============================================================
# PRINT CURRENT STATE
# ============================================================

print("\n=== CURRENT SIMULATION STATE ===")

print(
    "Current time:",
    simulator.current_time_min
)

print("\nEligible/recommended trains:")

for recommendation in decision["recommendations"]:

    print("\n------------------------------")

    print(
        "Train:",
        recommendation["train_id"]
    )

    print(
        "ML action:",
        recommendation["ml_action"]
    )

    print(
        "Final action:",
        recommendation["final_action"]
    )

    print(
        "Safe:",
        recommendation["safe"]
    )

    print(
        "Next section:",
        recommendation["next_section"]
    )

    print(
        "Reason:",
        recommendation["reason"]
    )

    print(
        "Probabilities:",
        recommendation["probabilities"]
    )

    if "conflict_reason" in recommendation:

        print(
            "Conflict reason:",
            recommendation["conflict_reason"]
        )

    if "required_wait_min" in recommendation:

        print(
            "Required wait:",
            recommendation["required_wait_min"]
        )


# ============================================================
# SELECTED ACTION
# ============================================================

print("\n==============================")

print("SELECTED ACTION")

print("==============================")

print(
    decision["selected_action"]
)