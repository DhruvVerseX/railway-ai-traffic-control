import os

# Prevent excessive parallel threads from scikit-learn / OpenBLAS.
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"

import sys
import csv
import random

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

NUM_SCENARIOS = 100
NUM_TRAINS = 6

SIMULATION_HORIZON = 240
DECISION_INTERVAL = 5

OUTPUT_FILE = (
    PROJECT_ROOT
    / "ml"
    / "data"
    / "ranking_training_data.csv"
)


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
# STORAGE
# ============================================================

rows = []

decision_points = 0
candidate_count = 0


# ============================================================
# SCENARIO TYPES
# ============================================================

scenario_types = [
    "random",
    "competition",
    "occupied",
    "conflict",
    "delay_priority"
]


# ============================================================
# RUN SCENARIOS
# ============================================================

for seed in range(NUM_SCENARIOS):

    print(
        f"Running scenario "
        f"{seed + 1}/{NUM_SCENARIOS}..."
    )


    # --------------------------------------------------------
    # Choose scenario type
    # --------------------------------------------------------

    scenario_type = scenario_types[
        seed % len(scenario_types)
    ]


    # --------------------------------------------------------
    # Generate scenario
    # --------------------------------------------------------

    traffic_state = builder.generate_mixed_scenario(
        scenario_id=f"RANKING_{seed}",
        num_trains=NUM_TRAINS,
        scenario_type=scenario_type,
        decision_time_min=5.0,
        running_advance_min=5.0,
        seed=seed
    )


    # --------------------------------------------------------
    # Create simulator
    # --------------------------------------------------------

    simulator = RailwaySimulator(
        network
    )

    simulator.load_traffic(
        traffic_state,
        database
    )


    # --------------------------------------------------------
    # Create AI controller
    # --------------------------------------------------------

    ai_controller = AITrainTrafficController(
        network,
        database
    )


    # --------------------------------------------------------
    # Create optimizer
    # --------------------------------------------------------

    optimizer = TrainTrafficOptimizer(
        simulator,
        database,
        evaluation_horizon_min=SIMULATION_HORIZON
    )


    # ========================================================
    # DECISION LOOP
    # ========================================================

    while simulator.current_time_min < SIMULATION_HORIZON:

        remaining_time = (
            SIMULATION_HORIZON
            - simulator.current_time_min
        )

        step = min(
            DECISION_INTERVAL,
            remaining_time
        )

        simulator.advance_time(
            step
        )


        # ----------------------------------------------------
        # Get AI recommendations.
        #
        # We use the existing V2 model to obtain the feature
        # representation and safety decision.
        # ----------------------------------------------------

        decision = ai_controller.make_decision(
            simulator
        )

        recommendations = (
            decision["recommendations"]
        )


        # ----------------------------------------------------
        # Keep only safe RELEASE candidates.
        # ----------------------------------------------------

        safe_releases = [
            result
            for result in recommendations
            if (
                result["final_action"] == "RELEASE"
                and result["safe"]
            )
        ]


        # We need at least two candidates for ranking.
        if len(safe_releases) < 2:
            continue


        decision_points += 1


        # ====================================================
        # EVALUATE EVERY SAFE CANDIDATE
        # ====================================================

        for recommendation in safe_releases:

            train_id = (
                recommendation["train_id"]
            )

            section_id = (
                recommendation["next_section"]
            )


            # ------------------------------------------------
            # Extract the SAME features used by V2.
            # ------------------------------------------------

            features = (
                ai_controller
                .ai_safety_controller
                .ml_controller
                .extract_features(
                    simulator,
                    train_id
                )
            )


            # ------------------------------------------------
            # Get train priority.
            # ------------------------------------------------

            train_data = database.get_train(
                train_id
            )

            priority = float(
                train_data["priority"]
            )


            # ------------------------------------------------
            # Create RELEASE action.
            # ------------------------------------------------

            action = {
                "train_id":
                    train_id,

                "action":
                    "RELEASE",

                "section_id":
                    section_id,

                "priority":
                    priority
            }


            # ------------------------------------------------
            # Let the optimizer simulate this action.
            # ------------------------------------------------

            evaluation = (
                optimizer.evaluate_action(
                    action
                )
            )


            # ------------------------------------------------
            # Store feature vector + target.
            # ------------------------------------------------

            row = dict(features)

            row.update(
                {
                    "train_id":
                        train_id,

                    "scenario_id":
                        seed,

                    "scenario_type":
                        scenario_type,

                    "decision_time_min":
                        simulator.current_time_min,

                    "section_id":
                        section_id,

                    "target_score":
                        evaluation["score"]
                }
            )


            rows.append(
                row
            )

            candidate_count += 1


# ============================================================
# CHECK DATA
# ============================================================

if not rows:

    print(
        "\nERROR: No ranking data was generated."
    )

    sys.exit(1)


# ============================================================
# DETERMINE FEATURE COLUMNS
# ============================================================

metadata_columns = {
    "train_id",
    "scenario_id",
    "scenario_type",
    "decision_time_min",
    "section_id",
    "target_score"
}

feature_columns = [
    key
    for key in rows[0].keys()
    if key not in metadata_columns
]


# ============================================================
# SAVE DATASET
# ============================================================

OUTPUT_FILE.parent.mkdir(
    parents=True,
    exist_ok=True
)


with open(
    OUTPUT_FILE,
    "w",
    newline="",
    encoding="utf-8"
) as file:

    writer = csv.DictWriter(
        file,
        fieldnames=(
            feature_columns
            + [
                "train_id",
                "scenario_id",
                "scenario_type",
                "decision_time_min",
                "section_id",
                "target_score"
            ]
        )
    )

    writer.writeheader()

    writer.writerows(
        rows
    )


# ============================================================
# SUMMARY
# ============================================================

print("\n==========================================")
print("RANKING DATASET GENERATION COMPLETE")
print("==========================================")

print(
    "Scenarios:",
    NUM_SCENARIOS
)

print(
    "Decision points:",
    decision_points
)

print(
    "Candidate actions:",
    candidate_count
)

print(
    "Features:",
    len(feature_columns)
)

print(
    "Rows:",
    len(rows)
)

print("\nFeature columns:")

for feature in feature_columns:
    print(
        " ",
        feature
    )

print("\nDataset saved to:")
print(
    OUTPUT_FILE
)