import os

# Prevent excessive parallel threads from scikit-learn / OpenBLAS.
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from input.input_state import TrainDatabase
from simulation.network import RailwayNetwork
from simulation.simulator import RailwaySimulator
from scenarios.mixed_scenario_builder import MixedScenarioBuilder
from controller.ai_controller import AITrainTrafficController
from optimizer.optimizer import TrainTrafficOptimizer


# ============================================================
# SETTINGS
# ============================================================

NUM_SCENARIOS = 25
SIMULATION_HORIZON = 240
DECISION_INTERVAL = 5


# ============================================================
# SETUP
# ============================================================

network = RailwayNetwork()
database = TrainDatabase()

builder = MixedScenarioBuilder(
    network,
    database
)


# ============================================================
# STATISTICS
# ============================================================

total_decisions = 0
decisions_with_multiple_releases = 0
agreements = 0
disagreements = 0

score_gaps = []

disagreement_details = []


# ============================================================
# RUN SCENARIOS
# ============================================================

for seed in range(NUM_SCENARIOS):

    traffic_state = builder.generate_mixed_scenario(
        scenario_id=f"AGREE_{seed}",
        num_trains=6,
        scenario_type="competition",
        decision_time_min=5.0,
        running_advance_min=5.0,
        seed=seed
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
        evaluation_horizon_min=SIMULATION_HORIZON
    )

    # --------------------------------------------------------
    # Decision loop
    # --------------------------------------------------------

    while simulator.current_time_min < SIMULATION_HORIZON:

        remaining_time = (
            SIMULATION_HORIZON
            - simulator.current_time_min
        )

        step = min(
            DECISION_INTERVAL,
            remaining_time
        )

        simulator.advance_time(step)

        # Get current AI recommendations.
        decision = ai_controller.make_decision(
            simulator
        )

        recommendations = decision["recommendations"]

        # ----------------------------------------------------
        # Find safe RELEASE candidates.
        # ----------------------------------------------------

        safe_releases = [
            result
            for result in recommendations
            if (
                result["final_action"] == "RELEASE"
                and result["safe"]
            )
        ]

        if len(safe_releases) < 2:
            # We only care about decision points where
            # there are at least two competing safe RELEASE
            # choices.
            continue

        decisions_with_multiple_releases += 1
        total_decisions += 1

        # ----------------------------------------------------
        # Current AI choice.
        # ----------------------------------------------------

        ai_choice = max(
            safe_releases,
            key=lambda result:
                result["probabilities"].get(
                    "RELEASE",
                    0.0
                )
        )

        ai_train_id = ai_choice["train_id"]

        # ----------------------------------------------------
        # Evaluate every safe RELEASE with optimizer.
        # ----------------------------------------------------

        optimizer_results = []

        for recommendation in safe_releases:

            train_id = recommendation["train_id"]

            train_data = database.get_train(
                train_id
            )

            action = {
                "train_id": train_id,
                "action": "RELEASE",
                "section_id": recommendation["next_section"],
                "priority": float(
                    train_data["priority"]
                )
            }

            evaluation = optimizer.evaluate_action(
                action
            )

            optimizer_results.append(
                {
                    "train_id": train_id,
                    "ml_probability": (
                        recommendation["probabilities"]
                        .get("RELEASE", 0.0)
                    ),
                    "score": evaluation["score"]
                }
            )

        # ----------------------------------------------------
        # Optimizer choice.
        # ----------------------------------------------------

        optimizer_choice = max(
            optimizer_results,
            key=lambda result:
                result["score"]
        )

        optimizer_train_id = (
            optimizer_choice["train_id"]
        )

        # ----------------------------------------------------
        # Compare choices.
        # ----------------------------------------------------

        if ai_train_id == optimizer_train_id:

            agreements += 1

        else:

            disagreements += 1

            best_score = optimizer_choice["score"]

            ai_score = next(
                result["score"]
                for result in optimizer_results
                if result["train_id"] == ai_train_id
            )

            score_gap = best_score - ai_score

            score_gaps.append(score_gap)

            disagreement_details.append(
                {
                    "seed": seed,
                    "time_min": simulator.current_time_min,
                    "ai_train": ai_train_id,
                    "optimizer_train": optimizer_train_id,
                    "ai_score": ai_score,
                    "best_score": best_score,
                    "score_gap": score_gap,
                    "candidates": optimizer_results
                }
            )

        # ----------------------------------------------------
        # Execute the actual AI decision.
        # ----------------------------------------------------

        ai_controller.execute_action(
            simulator,
            ai_choice
        )


# ============================================================
# RESULTS
# ============================================================

print("\n==========================================")
print("AI VS OPTIMIZER SELECTOR AGREEMENT")
print("==========================================")

print(
    "Scenarios:",
    NUM_SCENARIOS
)

print(
    "Decision points with multiple safe releases:",
    decisions_with_multiple_releases
)

print(
    "Agreements:",
    agreements
)

print(
    "Disagreements:",
    disagreements
)

if total_decisions > 0:

    agreement_rate = (
        agreements
        / total_decisions
        * 100
    )

    disagreement_rate = (
        disagreements
        / total_decisions
        * 100
    )

    print(
        "Agreement rate:",
        round(agreement_rate, 2),
        "%"
    )

    print(
        "Disagreement rate:",
        round(disagreement_rate, 2),
        "%"
    )


# ============================================================
# DISAGREEMENT ANALYSIS
# ============================================================

if score_gaps:

    average_gap = (
        sum(score_gaps)
        / len(score_gaps)
    )

    maximum_gap = max(score_gaps)

    print("\n=== DISAGREEMENT SCORE ANALYSIS ===")

    print(
        "Average optimizer score gap:",
        round(average_gap, 4)
    )

    print(
        "Maximum optimizer score gap:",
        round(maximum_gap, 4)
    )


# ============================================================
# SHOW FIRST 10 DISAGREEMENTS
# ============================================================

if disagreement_details:

    print("\n=== FIRST 10 DISAGREEMENTS ===")

    for detail in disagreement_details[:10]:

        print("\n------------------------------")

        print(
            "Seed:",
            detail["seed"]
        )

        print(
            "Time:",
            detail["time_min"]
        )

        print(
            "AI choice:",
            detail["ai_train"],
            "| Score:",
            detail["ai_score"]
        )

        print(
            "Optimizer choice:",
            detail["optimizer_train"],
            "| Score:",
            detail["best_score"]
        )

        print(
            "Score gap:",
            detail["score_gap"]
        )

        print(
            "Candidates:"
        )

        for candidate in detail["candidates"]:

            print(
                " ",
                candidate["train_id"],
                "| P(RELEASE):",
                round(
                    candidate["ml_probability"],
                    4
                ),
                "| Score:",
                candidate["score"]
            )

else:

    print("\nNo disagreements found.")