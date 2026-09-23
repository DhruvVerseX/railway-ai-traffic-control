import os

os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"

import sys
import csv
from pathlib import Path
from statistics import mean

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from simulation.network import RailwayNetwork
from simulation.simulator import RailwaySimulator
from simulation.conflict_detector import ConflictDetector

from input.input_state import TrainDatabase

from scenarios.mixed_scenario_builder import (
    MixedScenarioBuilder
)

from controller.baseline_controller import (
    BaselineController
)

from controller.ai_controller import (
    AITrainTrafficController
)

from controller.ml_controller import (
    MLTrainController
)

from metrics.metrics import (
    SimulationMetrics
)


# ============================================================
# CONFIGURATION
# ============================================================

NUM_SCENARIOS = 100
NUM_TRAINS = 6

HORIZON_MIN = 240.0
DECISION_INTERVAL_MIN = 5.0

V2_MODEL_PATH = (
    PROJECT_ROOT
    / "ml"
    / "models"
    / "train_controller_v2.pkl"
)

V3_MODEL_PATH = (
    PROJECT_ROOT
    / "ml"
    / "models"
    / "train_controller_v3.pkl"
)

RESULTS_DIR = (
    PROJECT_ROOT
    / "ml"
    / "results"
)

RESULTS_PATH = (
    RESULTS_DIR
    / "controller_comparison_v2_v3.csv"
)


# ============================================================
# RUN ONE CONTROLLER
# ============================================================

def run_controller(
    traffic_state,
    controller_type
):

    network = RailwayNetwork()

    database = TrainDatabase()

    simulator = RailwaySimulator(
        network
    )

    simulator.load_traffic(
        traffic_state,
        database
    )

    # --------------------------------------------------------
    # CREATE CONTROLLER
    # --------------------------------------------------------

    if controller_type == "baseline":

        conflict_detector = ConflictDetector(
            simulator
        )

        controller = BaselineController(
            network,
            simulator,
            conflict_detector,
            database
        )

    elif controller_type == "v2":

        controller = AITrainTrafficController(
            network,
            database
        )

        controller.ai_safety_controller.ml_controller = (
            MLTrainController(
                network,
                database,
                model_path=V2_MODEL_PATH
            )
        )

    elif controller_type == "v3":

        controller = AITrainTrafficController(
            network,
            database
        )

        controller.ai_safety_controller.ml_controller = (
            MLTrainController(
                network,
                database,
                model_path=V3_MODEL_PATH
            )
        )

    else:

        raise ValueError(
            f"Unknown controller type: "
            f"{controller_type}"
        )

    # --------------------------------------------------------
    # SIMULATION
    # --------------------------------------------------------

    release_count = 0
    decision_count = 0

    while (
        simulator.current_time_min
        < HORIZON_MIN
    ):

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

        # ----------------------------------------------------
        # BASELINE
        # ----------------------------------------------------

        if controller_type == "baseline":

            results = (
                controller.control_waiting_trains(
                    execute=True
                )
            )

            for result in results:

                decision = result[
                    "decision"
                ]

                execution = result[
                    "execution"
                ]

                if (
                    decision["action"]
                    == "RELEASE"
                    and execution is not None
                    and execution.get(
                        "executed",
                        False
                    )
                ):

                    release_count += 1

        # ----------------------------------------------------
        # AI V2 / V3
        # ----------------------------------------------------

        else:

            decision = (
                controller.control_step(
                    simulator
                )
            )

            selected = decision.get(
                "selected_action"
            )

            if selected is not None:

                if (
                    selected.get(
                        "final_action"
                    )
                    == "RELEASE"
                ):

                    release_count += 1

    # --------------------------------------------------------
    # METRICS
    # --------------------------------------------------------

    metrics_engine = SimulationMetrics(
        simulator
    )

    metrics = (
        metrics_engine.calculate_all()
    )

    return {

        "controller":
            controller_type,

        "release_count":
            release_count,

        "decision_count":
            decision_count,

        "completed_trains":
            metrics[
                "completed_trains"
            ],

        "throughput":
            metrics[
                "throughput_trains_per_hour"
            ],

        "waiting":
            metrics[
                "total_waiting_time_min"
            ],

        "average_waiting":
            metrics[
                "average_waiting_time_min"
            ],

        "initial_delay":
            metrics[
                "initial_delay_min"
            ],

        "conflicts":
            metrics[
                "conflicts"
            ],
    }


# ============================================================
# RUN EXPERIMENT
# ============================================================

def run_experiment():

    print()
    print("=" * 80)
    print("THREE-WAY CONTROLLER COMPARISON")
    print("=" * 80)

    print()
    print(
        f"Scenarios: {NUM_SCENARIOS}"
    )

    print(
        f"Trains per scenario: "
        f"{NUM_TRAINS}"
    )

    print(
        f"Horizon: "
        f"{HORIZON_MIN} minutes"
    )

    print()

    network = RailwayNetwork()

    database = TrainDatabase()

    builder = MixedScenarioBuilder(
        network,
        database
    )

    all_results = []

    # --------------------------------------------------------
    # GENERATE SAME SCENARIOS FOR ALL CONTROLLERS
    # --------------------------------------------------------

    for scenario_number in range(
        1,
        NUM_SCENARIOS + 1
    ):

        seed = scenario_number

        traffic_state = (
            builder.generate_mixed_scenario(

                scenario_id=
                    f"COMPARE_{scenario_number:03d}",

                num_trains=
                    NUM_TRAINS,

                scenario_type=
                    "competition",

                decision_time_min=5.0,

                running_advance_min=5.0,

                seed=seed
            )
        )

        baseline = run_controller(
            traffic_state,
            "baseline"
        )

        v2 = run_controller(
            traffic_state,
            "v2"
        )

        v3 = run_controller(
            traffic_state,
            "v3"
        )

        row = {

            "scenario":
                scenario_number,

            "seed":
                seed,

            "baseline_throughput":
                baseline["throughput"],

            "v2_throughput":
                v2["throughput"],

            "v3_throughput":
                v3["throughput"],

            "baseline_completed":
                baseline["completed_trains"],

            "v2_completed":
                v2["completed_trains"],

            "v3_completed":
                v3["completed_trains"],

            "baseline_waiting":
                baseline["waiting"],

            "v2_waiting":
                v2["waiting"],

            "v3_waiting":
                v3["waiting"],

            "baseline_conflicts":
                baseline["conflicts"],

            "v2_conflicts":
                v2["conflicts"],

            "v3_conflicts":
                v3["conflicts"],

            "baseline_releases":
                baseline["release_count"],

            "v2_releases":
                v2["release_count"],

            "v3_releases":
                v3["release_count"],
        }

        all_results.append(
            row
        )

        print(
            f"Scenario {scenario_number:3d}/"
            f"{NUM_SCENARIOS} | "
            f"TP: "
            f"B={baseline['throughput']:.2f} "
            f"V2={v2['throughput']:.2f} "
            f"V3={v3['throughput']:.2f} | "
            f"Conflicts: "
            f"B={baseline['conflicts']} "
            f"V2={v2['conflicts']} "
            f"V3={v3['conflicts']}"
        )

    return all_results


# ============================================================
# ANALYZE RESULTS
# ============================================================

def analyze_results(
    results
):

    baseline_tp = [
        row["baseline_throughput"]
        for row in results
    ]

    v2_tp = [
        row["v2_throughput"]
        for row in results
    ]

    v3_tp = [
        row["v3_throughput"]
        for row in results
    ]

    baseline_wait = [
        row["baseline_waiting"]
        for row in results
    ]

    v2_wait = [
        row["v2_waiting"]
        for row in results
    ]

    v3_wait = [
        row["v3_waiting"]
        for row in results
    ]

    baseline_conflicts = [
        row["baseline_conflicts"]
        for row in results
    ]

    v2_conflicts = [
        row["v2_conflicts"]
        for row in results
    ]

    v3_conflicts = [
        row["v3_conflicts"]
        for row in results
    ]

    # ========================================================
    # AVERAGES
    # ========================================================

    print()
    print("=" * 80)
    print("AVERAGE RESULTS")
    print("=" * 80)

    print()

    print(
        f"Baseline throughput: "
        f"{mean(baseline_tp):.4f}"
    )

    print(
        f"V2 throughput:       "
        f"{mean(v2_tp):.4f}"
    )

    print(
        f"V3 throughput:       "
        f"{mean(v3_tp):.4f}"
    )

    print()

    print(
        f"Baseline waiting: "
        f"{mean(baseline_wait):.2f}"
    )

    print(
        f"V2 waiting:       "
        f"{mean(v2_wait):.2f}"
    )

    print(
        f"V3 waiting:       "
        f"{mean(v3_wait):.2f}"
    )

    print()

    print(
        f"Baseline conflicts: "
        f"{mean(baseline_conflicts):.2f}"
    )

    print(
        f"V2 conflicts:       "
        f"{mean(v2_conflicts):.2f}"
    )

    print(
        f"V3 conflicts:       "
        f"{mean(v3_conflicts):.2f}"
    )

    # ========================================================
    # WIN / TIE / LOSS
    # ========================================================

    counters = {

        "v2_vs_baseline": {
            "tp_win": 0,
            "tp_tie": 0,
            "tp_loss": 0,
        },

        "v3_vs_baseline": {
            "tp_win": 0,
            "tp_tie": 0,
            "tp_loss": 0,
        },

        "v3_vs_v2": {
            "tp_win": 0,
            "tp_tie": 0,
            "tp_loss": 0,
        },
    }

    for row in results:

        comparisons = [

            (
                "v2_vs_baseline",
                row["v2_throughput"],
                row["baseline_throughput"]
            ),

            (
                "v3_vs_baseline",
                row["v3_throughput"],
                row["baseline_throughput"]
            ),

            (
                "v3_vs_v2",
                row["v3_throughput"],
                row["v2_throughput"]
            ),
        ]

        for (
            name,
            ours,
            other
        ) in comparisons:

            if ours > other:

                counters[name][
                    "tp_win"
                ] += 1

            elif ours == other:

                counters[name][
                    "tp_tie"
                ] += 1

            else:

                counters[name][
                    "tp_loss"
                ] += 1

    print()
    print(
        "=" * 80
    )

    print(
        "THROUGHPUT WIN / TIE / LOSS"
    )

    print(
        "=" * 80
    )

    for name, values in counters.items():

        print()

        print(
            f"{name}: "
            f"Wins={values['tp_win']} "
            f"Ties={values['tp_tie']} "
            f"Losses={values['tp_loss']}"
        )

    # ========================================================
    # WAITING COMPARISON
    # LOWER IS BETTER
    # ========================================================

    waiting_comparisons = {

        "v2_vs_baseline": [
            row["v2_waiting"]
            for row in results
        ],

        "v3_vs_baseline": [
            row["v3_waiting"]
            for row in results
        ],

        "v3_vs_v2": [
            row["v3_waiting"]
            for row in results
        ],
    }

    waiting_reference = {

        "v2_vs_baseline": [
            row["baseline_waiting"]
            for row in results
        ],

        "v3_vs_baseline": [
            row["baseline_waiting"]
            for row in results
        ],

        "v3_vs_v2": [
            row["v2_waiting"]
            for row in results
        ],
    }

    print()
    print("=" * 80)
    print(
        "WAITING TIME WIN / TIE / LOSS"
    )
    print("=" * 80)

    for name in waiting_comparisons:

        wins = 0
        ties = 0
        losses = 0

        for ours, other in zip(
            waiting_comparisons[name],
            waiting_reference[name]
        ):

            if ours < other:

                wins += 1

            elif ours == other:

                ties += 1

            else:

                losses += 1

        print()

        print(
            f"{name}: "
            f"Better={wins} "
            f"Ties={ties} "
            f"Worse={losses}"
        )

    # ========================================================
    # CONFLICT COMPARISON
    # LOWER IS BETTER
    # ========================================================

    conflict_comparisons = {

        "v2_vs_baseline": [
            row["v2_conflicts"]
            for row in results
        ],

        "v3_vs_baseline": [
            row["v3_conflicts"]
            for row in results
        ],

        "v3_vs_v2": [
            row["v3_conflicts"]
            for row in results
        ],
    }

    conflict_reference = {

        "v2_vs_baseline": [
            row["baseline_conflicts"]
            for row in results
        ],

        "v3_vs_baseline": [
            row["baseline_conflicts"]
            for row in results
        ],

        "v3_vs_v2": [
            row["v2_conflicts"]
            for row in results
        ],
    }

    print()
    print("=" * 80)
    print(
        "CONFLICT WIN / TIE / LOSS"
    )
    print("=" * 80)

    for name in conflict_comparisons:

        wins = 0
        ties = 0
        losses = 0

        for ours, other in zip(
            conflict_comparisons[name],
            conflict_reference[name]
        ):

            if ours < other:

                wins += 1

            elif ours == other:

                ties += 1

            else:

                losses += 1

        print()

        print(
            f"{name}: "
            f"Better={wins} "
            f"Ties={ties} "
            f"Worse={losses}"
        )

    # ========================================================
    # IMPROVEMENTS
    # ========================================================

    baseline_tp_mean = mean(
        baseline_tp
    )

    v2_tp_mean = mean(
        v2_tp
    )

    v3_tp_mean = mean(
        v3_tp
    )

    baseline_wait_mean = mean(
        baseline_wait
    )

    v2_wait_mean = mean(
        v2_wait
    )

    v3_wait_mean = mean(
        v3_wait
    )

    baseline_conflict_mean = mean(
        baseline_conflicts
    )

    v2_conflict_mean = mean(
        v2_conflicts
    )

    v3_conflict_mean = mean(
        v3_conflicts
    )

    print()
    print("=" * 80)
    print("IMPROVEMENT SUMMARY")
    print("=" * 80)

    print()

    print(
        f"V2 vs Baseline throughput: "
        f"{((v2_tp_mean - baseline_tp_mean) / baseline_tp_mean) * 100:.2f}%"
    )

    print(
        f"V3 vs Baseline throughput: "
        f"{((v3_tp_mean - baseline_tp_mean) / baseline_tp_mean) * 100:.2f}%"
    )

    print(
        f"V3 vs V2 throughput: "
        f"{((v3_tp_mean - v2_tp_mean) / v2_tp_mean) * 100:.2f}%"
    )

    print()

    print(
        f"V2 vs Baseline waiting reduction: "
        f"{((baseline_wait_mean - v2_wait_mean) / baseline_wait_mean) * 100:.2f}%"
    )

    print(
        f"V3 vs Baseline waiting reduction: "
        f"{((baseline_wait_mean - v3_wait_mean) / baseline_wait_mean) * 100:.2f}%"
    )

    print(
        f"V3 vs V2 waiting reduction: "
        f"{(v2_wait_mean - v3_wait_mean) / v2_wait_mean * 100:.2f}%"
    )

    print()

    print(
        f"V2 vs Baseline conflict reduction: "
        f"{(baseline_conflict_mean - v2_conflict_mean) / baseline_conflict_mean * 100:.2f}%"
    )

    print(
        f"V3 vs Baseline conflict reduction: "
        f"{(baseline_conflict_mean - v3_conflict_mean) / baseline_conflict_mean * 100:.2f}%"
    )

    print(
        f"V3 vs V2 conflict reduction: "
        f"{(v2_conflict_mean - v3_conflict_mean) / v2_conflict_mean * 100:.2f}%"
    )


# ============================================================
# SAVE RESULTS
# ============================================================

def save_results(
    results
):

    RESULTS_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    fieldnames = list(
        results[0].keys()
    )

    with open(
        RESULTS_PATH,
        "w",
        newline="",
        encoding="utf-8"
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames
        )

        writer.writeheader()

        writer.writerows(
            results
        )

    print()
    print(
        f"Detailed results saved to:"
    )

    print(
        RESULTS_PATH
    )


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    results = run_experiment()

    analyze_results(
        results
    )

    save_results(
        results
    )

    print()
    print("=" * 80)
    print(
        "THREE-WAY EXPERIMENT COMPLETE"
    )
    print("=" * 80)