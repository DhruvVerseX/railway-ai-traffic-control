import os

# Prevent excessive parallel threads from scikit-learn / OpenBLAS.
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"

import sys
import csv

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

OUTPUT_FILE = (
    PROJECT_ROOT
    / "ml"
    / "results"
    / "selector_disagreements.csv"
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

disagreements = []

total_decisions = 0
agreements = 0


# ============================================================
# RUN SCENARIOS
# ============================================================

for seed in range(NUM_SCENARIOS):

    print(
        f"Running scenario {seed + 1}/{NUM_SCENARIOS}..."
    )

    traffic_state = builder.generate_mixed_scenario(
        scenario_id=f"ANALYSIS_{seed}",
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

        simulator.advance_time(step)

        decision = ai_controller.make_decision(
            simulator
        )

        recommendations = decision["recommendations"]


        # ----------------------------------------------------
        # Safe RELEASE candidates
        # ----------------------------------------------------

        safe_releases = [
            result
            for result in recommendations
            if (
                result["final_action"] == "RELEASE"
                and result["safe"]
            )
        ]

        # We only compare choices when there are at least
        # two safe RELEASE candidates.
        if len(safe_releases) < 2:
            continue


        total_decisions += 1


        # ----------------------------------------------------
        # Current AI choice
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
        # Evaluate candidates with optimizer
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

                    "section_id":
                        recommendation["next_section"],

                    "ml_probability": (
                        recommendation["probabilities"]
                        .get("RELEASE", 0.0)
                    ),

                    "score":
                        evaluation["score"],

                    "metrics":
                        evaluation["metrics"],

                    # Keep the original evaluation so that
                    # we can inspect the exact objective
                    # calculation later.
                    "evaluation":
                        evaluation,

                    "action":
                        action
                }
            )


        # ----------------------------------------------------
        # Optimizer choice
        # ----------------------------------------------------

        optimizer_choice = max(
            optimizer_results,
            key=lambda result:
                result["score"]
        )

        optimizer_train_id = (
            optimizer_choice["train_id"]
        )


        # ====================================================
        # AGREEMENT
        # ====================================================

        if ai_train_id == optimizer_train_id:

            agreements += 1


        # ====================================================
        # DISAGREEMENT
        # ====================================================

        else:

            # ------------------------------------------------
            # Find the exact optimizer evaluation corresponding
            # to the AI-selected train.
            # ------------------------------------------------

            ai_result = next(
                result
                for result in optimizer_results
                if result["train_id"] == ai_train_id
            )

            optimizer_result = optimizer_choice


            # ------------------------------------------------
            # Exact scores
            # ------------------------------------------------

            ai_score = ai_result["score"]

            optimizer_score = (
                optimizer_result["score"]
            )

            score_gap = (
                optimizer_score
                - ai_score
            )


            # ------------------------------------------------
            # Get train information
            # ------------------------------------------------

            ai_train = database.get_train(
                ai_train_id
            )

            optimizer_train = database.get_train(
                optimizer_train_id
            )


            # ------------------------------------------------
            # EXACT OBJECTIVE BREAKDOWN
            #
            # IMPORTANT:
            # These come directly from the exact evaluations
            # that produced the disagreement.
            # ------------------------------------------------

            ai_breakdown = optimizer.objective.explain_score(
                ai_result["metrics"],
                ai_result["action"]
            )

            optimizer_breakdown = (
                optimizer.objective.explain_score(
                    optimizer_result["metrics"],
                    optimizer_result["action"]
                )
            )


            # ------------------------------------------------
            # Record disagreement
            # ------------------------------------------------

            disagreements.append(
                {
                    "seed":
                        seed,

                    "time_min":
                        simulator.current_time_min,

                    "ai_train":
                        ai_train_id,

                    "optimizer_train":
                        optimizer_train_id,

                    "ai_section":
                        ai_result["section_id"],

                    "optimizer_section":
                        optimizer_result["section_id"],

                    "ai_probability":
                        ai_result["ml_probability"],

                    "optimizer_probability":
                        optimizer_result[
                            "ml_probability"
                        ],

                    "ai_score":
                        ai_score,

                    "optimizer_score":
                        optimizer_score,

                    "score_gap":
                        score_gap,

                    # ------------------------------------------------
                    # AI objective components
                    # ------------------------------------------------

                    "ai_throughput_contribution":
                        ai_breakdown[
                            "throughput_contribution"
                        ],

                    "ai_waiting_penalty":
                        ai_breakdown[
                            "waiting_penalty"
                        ],

                    "ai_delay_penalty":
                        ai_breakdown[
                            "delay_penalty"
                        ],

                    "ai_conflict_penalty":
                        ai_breakdown[
                            "conflict_penalty"
                        ],

                    "ai_priority_bonus":
                        ai_breakdown[
                            "priority_bonus"
                        ],

                    # ------------------------------------------------
                    # Optimizer objective components
                    # ------------------------------------------------

                    "optimizer_throughput_contribution":
                        optimizer_breakdown[
                            "throughput_contribution"
                        ],

                    "optimizer_waiting_penalty":
                        optimizer_breakdown[
                            "waiting_penalty"
                        ],

                    "optimizer_delay_penalty":
                        optimizer_breakdown[
                            "delay_penalty"
                        ],

                    "optimizer_conflict_penalty":
                        optimizer_breakdown[
                            "conflict_penalty"
                        ],

                    "optimizer_priority_bonus":
                        optimizer_breakdown[
                            "priority_bonus"
                        ],

                    # ------------------------------------------------
                    # Train information
                    # ------------------------------------------------

                    "ai_priority":
                        float(
                            ai_train["priority"]
                        ),

                    "optimizer_priority":
                        float(
                            optimizer_train["priority"]
                        ),

                    "ai_delay":
                        float(
                            simulator.get_train_state(
                                ai_train_id
                            ).delay_min
                        ),

                    "optimizer_delay":
                        float(
                            simulator.get_train_state(
                                optimizer_train_id
                            ).delay_min
                        ),

                    "ai_train_type":
                        ai_train["train_type"],

                    "optimizer_train_type":
                        optimizer_train[
                            "train_type"
                        ],

                    "ai_entry_station":
                        ai_train["entry_station"],

                    "optimizer_entry_station":
                        optimizer_train[
                            "entry_station"
                        ],

                    "ai_exit_station":
                        ai_train["exit_station"],

                    "optimizer_exit_station":
                        optimizer_train[
                            "exit_station"
                        ],

                    "candidate_count":
                        len(optimizer_results)
                }
            )


        # ----------------------------------------------------
        # Execute actual AI decision
        # ----------------------------------------------------

        ai_controller.execute_action(
            simulator,
            ai_choice
        )


# ============================================================
# SAVE CSV
# ============================================================

OUTPUT_FILE.parent.mkdir(
    parents=True,
    exist_ok=True
)

fieldnames = [

    "seed",
    "time_min",

    "ai_train",
    "optimizer_train",

    "ai_section",
    "optimizer_section",

    "ai_probability",
    "optimizer_probability",

    "ai_score",
    "optimizer_score",
    "score_gap",

    # --------------------------------------------------------
    # AI objective
    # --------------------------------------------------------

    "ai_throughput_contribution",
    "ai_waiting_penalty",
    "ai_delay_penalty",
    "ai_conflict_penalty",
    "ai_priority_bonus",

    # --------------------------------------------------------
    # Optimizer objective
    # --------------------------------------------------------

    "optimizer_throughput_contribution",
    "optimizer_waiting_penalty",
    "optimizer_delay_penalty",
    "optimizer_conflict_penalty",
    "optimizer_priority_bonus",

    # --------------------------------------------------------
    # Train information
    # --------------------------------------------------------

    "ai_priority",
    "optimizer_priority",

    "ai_delay",
    "optimizer_delay",

    "ai_train_type",
    "optimizer_train_type",

    "ai_entry_station",
    "optimizer_entry_station",

    "ai_exit_station",
    "optimizer_exit_station",

    "candidate_count"
]


with open(
    OUTPUT_FILE,
    "w",
    newline="",
    encoding="utf-8"
) as file:

    writer = csv.DictWriter(
        file,
        fieldnames=fieldnames
    )

    writer.writeheader()
    writer.writerows(disagreements)


# ============================================================
# SUMMARY
# ============================================================

print("\n==========================================")
print("SELECTOR DISAGREEMENT ANALYSIS")
print("==========================================")

print(
    "Total decision points:",
    total_decisions
)

print(
    "Agreements:",
    agreements
)

print(
    "Disagreements:",
    len(disagreements)
)

if total_decisions > 0:

    agreement_rate = (
        agreements
        / total_decisions
        * 100
    )

    disagreement_rate = (
        len(disagreements)
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
# SCORE-GAP ANALYSIS
# ============================================================

if disagreements:

    score_gaps = [
        row["score_gap"]
        for row in disagreements
    ]

    average_gap = (
        sum(score_gaps)
        / len(score_gaps)
    )

    meaningful = [
        gap
        for gap in score_gaps
        if gap > 1.0
    ]

    large = [
        gap
        for gap in score_gaps
        if gap > 20.0
    ]

    print("\n=== SCORE GAP ANALYSIS ===")

    print(
        "Average score gap:",
        round(average_gap, 2)
    )

    print(
        "Disagreements with gap > 1:",
        len(meaningful)
    )

    print(
        "Disagreements with gap > 20:",
        len(large)
    )


# ============================================================
# TOP 10 SCORE GAPS + EXACT OBJECTIVE BREAKDOWN
# ============================================================

if disagreements:

    print("\n=== TOP 10 SCORE GAPS ===")

    sorted_disagreements = sorted(
        disagreements,
        key=lambda row:
            row["score_gap"],
        reverse=True
    )


    for row in sorted_disagreements[:10]:

        print("\n------------------------------")

        print(
            "Seed:",
            row["seed"],
            "| Time:",
            row["time_min"]
        )

        print(
            "AI:",
            row["ai_train"],
            "| Section:",
            row["ai_section"],
            "| P(RELEASE):",
            round(
                row["ai_probability"],
                4
            )
        )

        print(
            "Optimizer:",
            row["optimizer_train"],
            "| Section:",
            row["optimizer_section"],
            "| P(RELEASE):",
            round(
                row["optimizer_probability"],
                4
            )
        )

        print(
            "AI score:",
            row["ai_score"]
        )

        print(
            "Optimizer score:",
            row["optimizer_score"]
        )

        print(
            "Score gap:",
            row["score_gap"]
        )


        # ----------------------------------------------------
        # AI objective
        # ----------------------------------------------------

        print("\nAI objective:")

        print(
            "  Throughput contribution:",
            row[
                "ai_throughput_contribution"
            ]
        )

        print(
            "  Waiting penalty:",
            row[
                "ai_waiting_penalty"
            ]
        )

        print(
            "  Delay penalty:",
            row[
                "ai_delay_penalty"
            ]
        )

        print(
            "  Conflict penalty:",
            row[
                "ai_conflict_penalty"
            ]
        )

        print(
            "  Priority bonus:",
            row[
                "ai_priority_bonus"
            ]
        )


        # ----------------------------------------------------
        # Optimizer objective
        # ----------------------------------------------------

        print("\nOptimizer objective:")

        print(
            "  Throughput contribution:",
            row[
                "optimizer_throughput_contribution"
            ]
        )

        print(
            "  Waiting penalty:",
            row[
                "optimizer_waiting_penalty"
            ]
        )

        print(
            "  Delay penalty:",
            row[
                "optimizer_delay_penalty"
            ]
        )

        print(
            "  Conflict penalty:",
            row[
                "optimizer_conflict_penalty"
            ]
        )

        print(
            "  Priority bonus:",
            row[
                "optimizer_priority_bonus"
            ]
        )


        # ----------------------------------------------------
        # Train information
        # ----------------------------------------------------

        print("\nTrain information:")

        print(
            "  AI priority:",
            row["ai_priority"],
            "| Optimizer priority:",
            row["optimizer_priority"]
        )

        print(
            "  AI delay:",
            row["ai_delay"],
            "| Optimizer delay:",
            row["optimizer_delay"]
        )

        print(
            "  Candidates:",
            row["candidate_count"]
        )


# ============================================================
# FINAL MESSAGE
# ============================================================

print("\nCSV saved to:")
print(OUTPUT_FILE)