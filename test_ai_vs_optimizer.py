import os

# Prevent excessive parallel threads from scikit-learn / OpenBLAS.
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"

import sys
from pathlib import Path
from copy import deepcopy

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from input.input_state import TrainDatabase
from simulation.network import RailwayNetwork
from simulation.simulator import RailwaySimulator
from scenarios.mixed_scenario_builder import MixedScenarioBuilder
from controller.ai_controller import AITrainTrafficController
from optimizer.optimizer import TrainTrafficOptimizer


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
    scenario_id="AI_OPT_DIAGNOSTIC",
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

ai_controller = AITrainTrafficController(
    network,
    database
)

optimizer = TrainTrafficOptimizer(
    simulator,
    database,
    evaluation_horizon_min=240
)


# ============================================================
# MOVE TO DECISION POINT
# ============================================================

simulator.advance_time(5.0)

print("\n=== CURRENT TIME ===")
print(simulator.current_time_min)


# ============================================================
# GET AI RECOMMENDATIONS
# ============================================================

decision = ai_controller.make_decision(
    simulator
)

recommendations = decision["recommendations"]


print("\n=== AI RECOMMENDATIONS ===")

for result in recommendations:

    print(
        result["train_id"],
        "| Section:",
        result["next_section"],
        "| ML:",
        result["ml_action"],
        "| P(RELEASE):",
        round(
            result["probabilities"].get(
                "RELEASE",
                0.0
            ),
            4
        ),
        "| Safe:",
        result["safe"]
    )


# ============================================================
# EVALUATE SAFE RELEASE ACTIONS WITH OPTIMIZER
# ============================================================

print("\n=== OPTIMIZER EVALUATION ===")

optimizer_results = []

for recommendation in recommendations:

    if (
        recommendation["final_action"] != "RELEASE"
        or not recommendation["safe"]
    ):
        continue

    action = {
        "train_id": recommendation["train_id"],
        "action": "RELEASE",
        "section_id": recommendation["next_section"],
        "priority": database.get_train(
            recommendation["train_id"]
        )["priority"]
    }

    evaluation = optimizer.evaluate_action(
        action
    )

    optimizer_results.append(
        {
            "train_id": recommendation["train_id"],
            "section_id": recommendation["next_section"],
            "ml_release_probability": (
                recommendation["probabilities"]
                .get("RELEASE", 0.0)
            ),
            "optimizer_score": evaluation["score"],
            "metrics": evaluation["metrics"]
        }
    )


# ============================================================
# PRINT COMPARISON
# ============================================================

print("\n=== ML VS OPTIMIZER ===")

for result in optimizer_results:

    metrics = result["metrics"]

    print("\n------------------------------")

    print(
        "Train:",
        result["train_id"]
    )

    print(
        "Section:",
        result["section_id"]
    )

    print(
        "ML P(RELEASE):",
        round(
            result["ml_release_probability"],
            4
        )
    )

    print(
        "Optimizer score:",
        result["optimizer_score"]
    )

    print(
        "Throughput:",
        metrics["throughput_trains_per_hour"]
    )

    print(
        "Waiting:",
        metrics["total_waiting_time_min"]
    )

    print(
        "Conflicts:",
        metrics["conflicts"]
    )


# ============================================================
# RANKINGS
# ============================================================

print("\n=== ML RANKING ===")

ml_ranked = sorted(
    optimizer_results,
    key=lambda x: x["ml_release_probability"],
    reverse=True
)

for i, result in enumerate(
    ml_ranked,
    start=1
):

    print(
        i,
        ".",
        result["train_id"],
        "→",
        round(
            result["ml_release_probability"],
            4
        )
    )


print("\n=== OPTIMIZER RANKING ===")

optimizer_ranked = sorted(
    optimizer_results,
    key=lambda x: x["optimizer_score"],
    reverse=True
)

for i, result in enumerate(
    optimizer_ranked,
    start=1
):

    print(
        i,
        ".",
        result["train_id"],
        "→",
        result["optimizer_score"]
    )