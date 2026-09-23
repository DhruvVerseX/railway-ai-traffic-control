import sys
import csv
from pathlib import Path
from statistics import mean, stdev

# ============================================================
# PROJECT PATH
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ============================================================
# PROJECT IMPORTS
# ============================================================

from railway_ai.scenarios.mixed_scenario_builder import (
    MixedScenarioBuilder
)

from railway_ai.input.input_state import TrainDatabase

from railway_ai.simulation.network import RailwayNetwork

from railway_ai.simulation.simulator import RailwaySimulator

from railway_ai.simulation.conflict_detector import (
    ConflictDetector
)

from railway_ai.controller.baseline_controller import (
    BaselineController
)

from railway_ai.controller.ai_controller import (
    AITrainTrafficController
)

from railway_ai.metrics.metrics import SimulationMetrics


# ============================================================
# EXPERIMENT SETTINGS
# ============================================================

NUM_SCENARIOS = 100
NUM_TRAINS = 6

SCENARIO_TYPE = "competition"

SIMULATION_TIME_MIN = 240.0
DECISION_INTERVAL_MIN = 5.0


# ============================================================
# RUN ONE CONTROLLER
# ============================================================

def run_controller(
    traffic_state,
    controller_type
):

    network = RailwayNetwork()
    train_database = TrainDatabase()

    simulator = RailwaySimulator(network)

    simulator.load_traffic(
        traffic_state,
        train_database
    )

    # --------------------------------------------------------
    # Create controller
    # --------------------------------------------------------

    if controller_type == "baseline":

        conflict_detector = ConflictDetector(
            simulator
        )

        controller = BaselineController(
            network=network,
            simulator=simulator,
            conflict_detector=conflict_detector,
            train_database=train_database
        )

    elif controller_type == "ai":

        controller = AITrainTrafficController(
            network,
            train_database
        )

    else:

        raise ValueError(
            f"Unknown controller type: {controller_type}"
        )

    # --------------------------------------------------------
    # Decision statistics
    # --------------------------------------------------------

    release_decisions = 0
    hold_decisions = 0
    executed_releases = 0

    # ========================================================
    # SIMULATION LOOP
    # ========================================================

    while (
        simulator.current_time_min
        <
        SIMULATION_TIME_MIN
    ):

        # ----------------------------------------------------
        # Controller decision
        # ----------------------------------------------------

        if controller_type == "baseline":

            results = controller.control_waiting_trains(
                execute=True
            )

            for result in results:

                decision = result["decision"]

                execution = result["execution"]

                action = decision["action"]

                if action == "RELEASE":

                    release_decisions += 1

                    if (
                        execution is not None
                        and
                        execution.get(
                            "executed",
                            False
                        )
                    ):

                        executed_releases += 1

                elif action == "HOLD":

                    hold_decisions += 1

        else:

            result = controller.control_step(
                simulator
            )

            selected = result["selected_action"]

            if selected is not None:

                action = selected["final_action"]

                if action == "RELEASE":

                    release_decisions += 1
                    executed_releases += 1

                elif action == "HOLD":

                    hold_decisions += 1

        # ----------------------------------------------------
        # Advance simulation
        # ----------------------------------------------------

        remaining_time = (
            SIMULATION_TIME_MIN
            -
            simulator.current_time_min
        )

        advance_time = min(
            DECISION_INTERVAL_MIN,
            remaining_time
        )

        if advance_time <= 0:
            break

        simulator.advance_time(
            advance_time
        )

    # ========================================================
    # METRICS
    # ========================================================

    metrics = SimulationMetrics(
        simulator
    ).calculate_all()

    return {
        "metrics": metrics,
        "release_count": executed_releases,
        "release_decisions": release_decisions,
        "hold_decisions": hold_decisions,
        "total_decisions":
            release_decisions + hold_decisions
    }


# ============================================================
# HELPER
# ============================================================

def average(results, key):

    return mean(
        result["metrics"][key]
        for result in results
    )


def standard_deviation(results, key):

    values = [
        result["metrics"][key]
        for result in results
    ]

    if len(values) < 2:
        return 0.0

    return stdev(values)


# ============================================================
# MAIN EXPERIMENT
# ============================================================

def main():

    print("\n" + "=" * 70)
    print("FINAL BASELINE vs V2 AI EVALUATION")
    print("=" * 70)

    print(
        f"\nScenarios              : {NUM_SCENARIOS}"
    )

    print(
        f"Trains per scenario   : {NUM_TRAINS}"
    )

    print(
        f"Scenario type         : {SCENARIO_TYPE}"
    )

    print(
        f"Simulation horizon    : "
        f"{SIMULATION_TIME_MIN} min"
    )

    print(
        f"Decision interval     : "
        f"{DECISION_INTERVAL_MIN} min"
    )

    # ========================================================
    # INITIALIZE
    # ========================================================

    network = RailwayNetwork()

    train_database = TrainDatabase()

    builder = MixedScenarioBuilder(
        network,
        train_database
    )

    baseline_results = []
    ai_results = []

    csv_rows = []

    # ========================================================
    # RUN ALL SCENARIOS
    # ========================================================

    for scenario_number in range(
        1,
        NUM_SCENARIOS + 1
    ):

        seed = scenario_number

        # ----------------------------------------------------
        # Generate ONE scenario
        # ----------------------------------------------------

        traffic_state = (
            builder.generate_mixed_scenario(
                scenario_id=f"FINAL_{seed}",
                num_trains=NUM_TRAINS,
                scenario_type=SCENARIO_TYPE,
                decision_time_min=5.0,
                running_advance_min=5.0,
                seed=seed
            )
        )

        # ----------------------------------------------------
        # Baseline
        # ----------------------------------------------------

        baseline = run_controller(
            traffic_state,
            "baseline"
        )

        # ----------------------------------------------------
        # V2 AI
        # ----------------------------------------------------

        ai = run_controller(
            traffic_state,
            "ai"
        )

        baseline_results.append(
            baseline
        )

        ai_results.append(
            ai
        )

        # ----------------------------------------------------
        # Store row
        # ----------------------------------------------------

        csv_rows.append({

            "scenario":
                scenario_number,

            "seed":
                seed,

            "baseline_throughput":
                baseline["metrics"][
                    "throughput_trains_per_hour"
                ],

            "ai_throughput":
                ai["metrics"][
                    "throughput_trains_per_hour"
                ],

            "baseline_completed":
                baseline["metrics"][
                    "completed_trains"
                ],

            "ai_completed":
                ai["metrics"][
                    "completed_trains"
                ],

            "baseline_initial_delay":
                baseline["metrics"][
                    "initial_delay_min"
                ],

            "ai_initial_delay":
                ai["metrics"][
                    "initial_delay_min"
                ],

            "baseline_waiting":
                baseline["metrics"][
                    "total_waiting_time_min"
                ],

            "ai_waiting":
                ai["metrics"][
                    "total_waiting_time_min"
                ],

            "baseline_avg_waiting":
                baseline["metrics"][
                    "average_waiting_time_min"
                ],

            "ai_avg_waiting":
                ai["metrics"][
                    "average_waiting_time_min"
                ],

            "baseline_conflicts":
                baseline["metrics"][
                    "conflicts"
                ],

            "ai_conflicts":
                ai["metrics"][
                    "conflicts"
                ],

            "baseline_releases":
                baseline["release_count"],

            "ai_releases":
                ai["release_count"],

            "baseline_decisions":
                baseline["total_decisions"],

            "ai_decisions":
                ai["total_decisions"]
        })

        # ----------------------------------------------------
        # Progress
        # ----------------------------------------------------

        if (
            scenario_number % 10 == 0
            or
            scenario_number == 1
        ):

            print(
                f"Completed "
                f"{scenario_number}/{NUM_SCENARIOS}"
            )

    # ========================================================
    # AVERAGES
    # ========================================================

    baseline_tp = average(
        baseline_results,
        "throughput_trains_per_hour"
    )

    ai_tp = average(
        ai_results,
        "throughput_trains_per_hour"
    )

    baseline_completed = average(
        baseline_results,
        "completed_trains"
    )

    ai_completed = average(
        ai_results,
        "completed_trains"
    )

    baseline_delay = average(
        baseline_results,
        "initial_delay_min"
    )

    ai_delay = average(
        ai_results,
        "initial_delay_min"
    )

    baseline_waiting = average(
        baseline_results,
        "total_waiting_time_min"
    )

    ai_waiting = average(
        ai_results,
        "total_waiting_time_min"
    )

    baseline_avg_waiting = average(
        baseline_results,
        "average_waiting_time_min"
    )

    ai_avg_waiting = average(
        ai_results,
        "average_waiting_time_min"
    )

    baseline_conflicts = average(
        baseline_results,
        "conflicts"
    )

    ai_conflicts = average(
        ai_results,
        "conflicts"
    )

    # ========================================================
    # STANDARD DEVIATIONS
    # ========================================================

    baseline_tp_std = standard_deviation(
        baseline_results,
        "throughput_trains_per_hour"
    )

    ai_tp_std = standard_deviation(
        ai_results,
        "throughput_trains_per_hour"
    )

    baseline_wait_std = standard_deviation(
        baseline_results,
        "total_waiting_time_min"
    )

    ai_wait_std = standard_deviation(
        ai_results,
        "total_waiting_time_min"
    )

    baseline_conf_std = standard_deviation(
        baseline_results,
        "conflicts"
    )

    ai_conf_std = standard_deviation(
        ai_results,
        "conflicts"
    )

    # ========================================================
    # IMPROVEMENTS
    # ========================================================

    throughput_improvement = (
        (
            ai_tp - baseline_tp
        )
        /
        baseline_tp
    ) * 100

    waiting_change = (
        (
            ai_waiting - baseline_waiting
        )
        /
        baseline_waiting
    ) * 100

    conflict_reduction = (
        (
            baseline_conflicts - ai_conflicts
        )
        /
        baseline_conflicts
    ) * 100

    # ========================================================
    # WIN / TIE / LOSS
    # ========================================================

    throughput_wins = 0
    throughput_ties = 0
    throughput_losses = 0

    for baseline, ai in zip(
        baseline_results,
        ai_results
    ):

        b = baseline["metrics"][
            "throughput_trains_per_hour"
        ]

        a = ai["metrics"][
            "throughput_trains_per_hour"
        ]

        if a > b:
            throughput_wins += 1

        elif a < b:
            throughput_losses += 1

        else:
            throughput_ties += 1

    # ========================================================
    # PRINT FINAL RESULTS
    # ========================================================

    print("\n")
    print("=" * 70)
    print("FINAL RESULTS")
    print("=" * 70)

    print("\nBASELINE CONTROLLER")
    print("-" * 70)

    print(
        f"Throughput       : "
        f"{baseline_tp:.4f} "
        f"+/- {baseline_tp_std:.4f}"
    )

    print(
        f"Completed trains : "
        f"{baseline_completed:.2f}"
    )

    print(
        f"Initial delay    : "
        f"{baseline_delay:.2f} min"
    )

    print(
        f"Total waiting    : "
        f"{baseline_waiting:.2f} "
        f"+/- {baseline_wait_std:.2f} min"
    )

    print(
        f"Average waiting  : "
        f"{baseline_avg_waiting:.2f} min"
    )

    print(
        f"Conflicts        : "
        f"{baseline_conflicts:.2f} "
        f"+/- {baseline_conf_std:.2f}"
    )

    print("\nV2 AI CONTROLLER")
    print("-" * 70)

    print(
        f"Throughput       : "
        f"{ai_tp:.4f} "
        f"+/- {ai_tp_std:.4f}"
    )

    print(
        f"Completed trains : "
        f"{ai_completed:.2f}"
    )

    print(
        f"Initial delay    : "
        f"{ai_delay:.2f} min"
    )

    print(
        f"Total waiting    : "
        f"{ai_waiting:.2f} "
        f"+/- {ai_wait_std:.2f} min"
    )

    print(
        f"Average waiting  : "
        f"{ai_avg_waiting:.2f} min"
    )

    print(
        f"Conflicts        : "
        f"{ai_conflicts:.2f} "
        f"+/- {ai_conf_std:.2f}"
    )

    # ========================================================
    # IMPROVEMENT
    # ========================================================

    print("\n")
    print("=" * 70)
    print("AI IMPROVEMENT OVER BASELINE")
    print("=" * 70)

    print(
        f"\nThroughput improvement : "
        f"{throughput_improvement:.2f}%"
    )

    print(
        f"Waiting-time change    : "
        f"{waiting_change:.2f}%"
    )

    print(
        f"Conflict reduction     : "
        f"{conflict_reduction:.2f}%"
    )

    print(
        f"\nThroughput wins        : "
        f"{throughput_wins}/{NUM_SCENARIOS}"
    )

    print(
        f"Throughput ties        : "
        f"{throughput_ties}/{NUM_SCENARIOS}"
    )

    print(
        f"Throughput losses      : "
        f"{throughput_losses}/{NUM_SCENARIOS}"
    )

    # ========================================================
    # SAVE CSV
    # ========================================================

    results_dir = (
        PROJECT_ROOT
        / "evaluation"
        / "results"
    )

    results_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    results_file = (
        results_dir
        / "final_v2_evaluation.csv"
    )

    fieldnames = list(
        csv_rows[0].keys()
    )

    with open(
        results_file,
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames
        )

        writer.writeheader()

        writer.writerows(
            csv_rows
        )

    print("\n")
    print("=" * 70)
    print("RESULT FILE")
    print("=" * 70)

    print(
        f"\nSaved to:\n{results_file}"
    )

    print("\n")
    print("=" * 70)
    print("FINAL EVALUATION COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()