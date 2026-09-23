import sys
import csv
from pathlib import Path
from statistics import mean, stdev

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scenarios.mixed_scenario_builder import MixedScenarioBuilder
from input.input_state import TrainDatabase
from simulation.network import RailwayNetwork
from simulation.simulator import RailwaySimulator
from simulation.conflict_detector import ConflictDetector
from controller.baseline_controller import BaselineController
from controller.ai_controller import AITrainTrafficController
from metrics.metrics import SimulationMetrics


# ============================================================
# RUN ONE CONTROLLER ON ONE SCENARIO
# ============================================================

def run_controller(
    traffic_state,
    controller_type,
    simulation_time_min=240.0,
    decision_interval_min=5.0
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

    # --------------------------------------------------------
    # Actual release log
    # --------------------------------------------------------

    release_log = []

    # ========================================================
    # SIMULATION LOOP
    # ========================================================

    while simulator.current_time_min < simulation_time_min:

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
                        and execution.get("executed", False)
                    ):

                        executed_releases += 1

                        release_log.append({
                            "time_min":
                                simulator.current_time_min,

                            "train_id":
                                decision["train_id"],

                            "action":
                                "RELEASE",

                            "section_id":
                                decision.get("section_id"),

                            "priority":
                                decision.get("priority")
                        })

                elif action == "HOLD":

                    hold_decisions += 1

        else:

            decision = controller.control_step(
                simulator
            )

            selected = decision["selected_action"]

            if selected is not None:

                final_action = selected["final_action"]

                if final_action == "RELEASE":

                    release_decisions += 1
                    executed_releases += 1

                    release_log.append({
                        "time_min":
                            simulator.current_time_min,

                        "train_id":
                            selected["train_id"],

                        "action":
                            "RELEASE",

                        "section_id":
                            selected.get("section_id"),

                        "priority":
                            selected.get("priority")
                    })

                elif final_action == "HOLD":

                    hold_decisions += 1

        # ----------------------------------------------------
        # Advance simulation
        # ----------------------------------------------------

        remaining_time = (
            simulation_time_min
            - simulator.current_time_min
        )

        advance_time = min(
            decision_interval_min,
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

    metrics_engine = SimulationMetrics(
        simulator
    )

    metrics = metrics_engine.calculate_all()

    return {
        "release_count":
            executed_releases,

        "release_decisions":
            release_decisions,

        "hold_decisions":
            hold_decisions,

        "total_decisions":
            release_decisions + hold_decisions,

        "release_log":
            release_log,

        "metrics":
            metrics
    }

# ============================================================
# MAIN EXPERIMENT
# ============================================================

def run_experiment(
    num_scenarios=10,
    num_trains=6,
    scenario_type="competition",
    simulation_time_min=240.0,
    decision_interval_min=5.0
):

    print("\n" + "=" * 70)
    print("AI vs BASELINE EXPERIMENT")
    print("=" * 70)

    print(
        f"\nScenarios: {num_scenarios}"
    )

    print(
        f"Trains per scenario: {num_trains}"
    )

    print(
        f"Scenario type: {scenario_type}"
    )

    print(
        f"Simulation horizon: "
        f"{simulation_time_min} min"
    )

    print(
        f"Decision interval: "
        f"{decision_interval_min} min"
    )

    network = RailwayNetwork()
    train_database = TrainDatabase()

    builder = MixedScenarioBuilder(
        network,
        train_database
    )

    baseline_results = []
    ai_results = []
    experiment_rows = []

    # ========================================================
    # RUN SCENARIOS
    # ========================================================

    for scenario_number in range(
        1,
        num_scenarios + 1
    ):

        seed = scenario_number

        print(
            f"\nScenario "
            f"{scenario_number}/{num_scenarios}"
            f"  | seed={seed}"
        )

        # ----------------------------------------------------
        # Generate ONE scenario
        # ----------------------------------------------------

        traffic_state = (
            builder.generate_mixed_scenario(
                scenario_id=f"EXP_{seed}",
                num_trains=num_trains,
                scenario_type=scenario_type,
                decision_time_min=5.0,
                running_advance_min=5.0,
                seed=seed
            )
        )

        # ----------------------------------------------------
        # Baseline
        # ----------------------------------------------------

        baseline = run_controller(
            traffic_state=traffic_state,
            controller_type="baseline",
            simulation_time_min=simulation_time_min,
            decision_interval_min=decision_interval_min
        )

        # ----------------------------------------------------
        # AI
        # ----------------------------------------------------

        ai = run_controller(
            traffic_state=traffic_state,
            controller_type="ai",
            simulation_time_min=simulation_time_min,
            decision_interval_min=decision_interval_min
        )

        baseline_results.append(
            baseline
        )

        ai_results.append(
            ai
        )
        experiment_rows.append({
    "scenario": scenario_number,
    "seed": seed,

    "baseline_throughput":
        baseline["metrics"]["throughput_trains_per_hour"],

    "ai_throughput":
        ai["metrics"]["throughput_trains_per_hour"],

    "baseline_completed":
        baseline["metrics"]["completed_trains"],

    "ai_completed":
        ai["metrics"]["completed_trains"],

    "baseline_waiting":
        baseline["metrics"]["total_waiting_time_min"],

    "ai_waiting":
        ai["metrics"]["total_waiting_time_min"],

    "baseline_conflicts":
        baseline["metrics"]["conflicts"],

    "ai_conflicts":
        ai["metrics"]["conflicts"],

    "baseline_releases":
        baseline["release_count"],

    "ai_releases":
        ai["release_count"],

    "baseline_release_decisions":
        baseline["release_decisions"],

    "ai_release_decisions":
        ai["release_decisions"],

    "baseline_hold_decisions":
        baseline["hold_decisions"],

    "ai_hold_decisions":
        ai["hold_decisions"],

    "baseline_total_decisions":
        baseline["total_decisions"],

    "ai_total_decisions":
        ai["total_decisions"],
})

        # ----------------------------------------------------
        # Scenario result
        # ----------------------------------------------------

        baseline_throughput = (
            baseline["metrics"]
            ["throughput_trains_per_hour"]
        )

        ai_throughput = (
            ai["metrics"]
            ["throughput_trains_per_hour"]
        )

        print(
            f"  Baseline throughput: "
            f"{baseline_throughput:.2f}"
        )

        print(
            f"  AI throughput:       "
            f"{ai_throughput:.2f}"
        )

        print(
            f"  Baseline conflicts:  "
            f"{baseline['metrics']['conflicts']}"
        )

        print(
            f"  AI conflicts:        "
            f"{ai['metrics']['conflicts']}"
        )

    # ========================================================
    # AGGREGATE RESULTS
    # ========================================================

    baseline_throughputs = [
        result["metrics"]
        ["throughput_trains_per_hour"]
        for result in baseline_results
    ]

    ai_throughputs = [
        result["metrics"]
        ["throughput_trains_per_hour"]
        for result in ai_results
    ]

    baseline_waiting = [
        result["metrics"]
        ["total_waiting_time_min"]
        for result in baseline_results
    ]

    ai_waiting = [
        result["metrics"]
        ["total_waiting_time_min"]
        for result in ai_results
    ]

    baseline_conflicts = [
        result["metrics"]
        ["conflicts"]
        for result in baseline_results
    ]

    ai_conflicts = [
        result["metrics"]
        ["conflicts"]
        for result in ai_results
    ]

    baseline_completed = [
        result["metrics"]
        ["completed_trains"]
        for result in baseline_results
    ]

    ai_completed = [
        result["metrics"]
        ["completed_trains"]
        for result in ai_results
    ]

    # ========================================================
    # PRINT SUMMARY
    # ========================================================

    print("\n" + "=" * 70)
    print("EXPERIMENT SUMMARY")
    print("=" * 70)

    print("\nAverage performance:")

    print(
        f"\nBaseline throughput: "
        f"{mean(baseline_throughputs):.3f} trains/hour"
    )

    print(
        f"AI throughput:       "
        f"{mean(ai_throughputs):.3f} trains/hour"
    )

    print(
        f"\nBaseline completed: "
        f"{mean(baseline_completed):.2f}"
    )

    print(
        f"AI completed:       "
        f"{mean(ai_completed):.2f}"
    )

    print(
        f"\nBaseline waiting: "
        f"{mean(baseline_waiting):.2f} min"
    )

    print(
        f"AI waiting:       "
        f"{mean(ai_waiting):.2f} min"
    )

    print(
        f"\nBaseline conflicts: "
        f"{mean(baseline_conflicts):.2f}"
    )

    print(
        f"AI conflicts:       "
        f"{mean(ai_conflicts):.2f}"
    )

    # ========================================================
    # IMPROVEMENTS
    # ========================================================

    baseline_avg_throughput = mean(
        baseline_throughputs
    )

    ai_avg_throughput = mean(
        ai_throughputs
    )

    baseline_avg_waiting = mean(
        baseline_waiting
    )

    ai_avg_waiting = mean(
        ai_waiting
    )

    baseline_avg_conflicts = mean(
        baseline_conflicts
    )

    ai_avg_conflicts = mean(
        ai_conflicts
    )

    print("\n" + "-" * 70)
    print("AI IMPROVEMENT")
    print("-" * 70)

    if baseline_avg_throughput > 0:

        throughput_improvement = (
            (
                ai_avg_throughput
                - baseline_avg_throughput
            )
            / baseline_avg_throughput
        ) * 100

        print(
            f"\nThroughput improvement: "
            f"{throughput_improvement:.2f}%"
        )

    else:

        print(
            "\nThroughput improvement: "
            "Baseline average is zero"
        )

    if baseline_avg_waiting > 0:

        waiting_reduction = (
            (
                baseline_avg_waiting
                - ai_avg_waiting
            )
            / baseline_avg_waiting
        ) * 100

        print(
            f"Waiting-time reduction: "
            f"{waiting_reduction:.2f}%"
        )

    if baseline_avg_conflicts > 0:

        conflict_reduction = (
            (
                baseline_avg_conflicts
                - ai_avg_conflicts
            )
            / baseline_avg_conflicts
        ) * 100

        print(
            f"Conflict reduction: "
            f"{conflict_reduction:.2f}%"
        )

    # ========================================================
    # WIN RATE
    # ========================================================

    throughput_wins = sum(
        1
        for baseline, ai
        in zip(
            baseline_results,
            ai_results
        )
        if (
            ai["metrics"]
            ["throughput_trains_per_hour"]
            >
            baseline["metrics"]
            ["throughput_trains_per_hour"]
        )
    )

    print(
        f"\nAI throughput wins: "
        f"{throughput_wins}/{num_scenarios}"
    )

    print("\n" + "=" * 70)
    print("EXPERIMENT COMPLETE")
    print("=" * 70)
    # ========================================================
    # SAVE RESULTS
    # ========================================================

    results_dir = (
        PROJECT_ROOT
        / "ml"
        / "results"
    )

    results_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    results_file = (
        results_dir
        / "controller_comparison.csv"
    )

    fieldnames = [
    "scenario",
    "seed",

    "baseline_throughput",
    "ai_throughput",

    "baseline_completed",
    "ai_completed",

    "baseline_waiting",
    "ai_waiting",

    "baseline_conflicts",
    "ai_conflicts",

    "baseline_releases",
    "ai_releases",

    "baseline_release_decisions",
    "ai_release_decisions",

    "baseline_hold_decisions",
    "ai_hold_decisions",

    "baseline_total_decisions",
    "ai_total_decisions",
]

    with open(
        results_file,
        "w",
        newline="",
        encoding="utf-8"
    ) as csv_file:

        writer = csv.DictWriter(
            csv_file,
            fieldnames=fieldnames
        )

        writer.writeheader()

        writer.writerows(
            experiment_rows
        )

    print(
        f"\nResults saved to:"
        f"\n{results_file}"
    )


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    run_experiment(
        num_scenarios=100,
        num_trains=6,
        scenario_type="competition",
        simulation_time_min=240.0,
        decision_interval_min=5.0
    )