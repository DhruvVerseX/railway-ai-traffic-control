import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from simulation.network import RailwayNetwork
from simulation.simulator import RailwaySimulator
from input.input_state import TrainDatabase
from scenarios.mixed_scenario_builder import MixedScenarioBuilder
from metrics.metrics import SimulationMetrics
from simulation.conflict_detector import ConflictDetector
from controller.baseline_controller import BaselineController


def run_baseline_simulation(
    scenario_type="competition",
    num_trains=6,
    seed=42,
    simulation_time_min=240.0,
    decision_interval_min=5.0
):

    # ========================================================
    # LOAD SYSTEM
    # ========================================================

    network = RailwayNetwork()
    train_database = TrainDatabase()

    builder = MixedScenarioBuilder(
        network,
        train_database
    )

    # ========================================================
    # GENERATE SCENARIO
    # ========================================================

    traffic_state = builder.generate_mixed_scenario(
        scenario_id="BASELINE_TEST",
        num_trains=num_trains,
        scenario_type=scenario_type,
        decision_time_min=5.0,
        running_advance_min=5.0,
        seed=seed
    )

    # ========================================================
    # CREATE SIMULATOR
    # ========================================================

    simulator = RailwaySimulator(
        network
    )

    simulator.load_traffic(
        traffic_state,
        train_database
    )

    # ========================================================
    # CREATE BASELINE CONTROLLER
    # ========================================================

    conflict_detector = ConflictDetector(
        simulator
    )

    controller = BaselineController(
        network=network,
        simulator=simulator,
        conflict_detector=conflict_detector,
        train_database=train_database
    )

    # ========================================================
    # SIMULATION
    # ========================================================

    print("\n" + "=" * 60)
    print("BASELINE SIMULATION")
    print("=" * 60)

    print(
        f"\nScenario type: {scenario_type}"
    )

    print(
        f"Trains: {num_trains}"
    )

    print(
        f"Seed: {seed}"
    )

    print(
        f"Simulation horizon: "
        f"{simulation_time_min} min"
    )

    decision_steps = 0
    release_count = 0

    while simulator.current_time_min < simulation_time_min:

        # ----------------------------------------------------
        # Baseline controller
        # ----------------------------------------------------

        results = controller.control_waiting_trains(
            execute=True
        )

        decision_steps += 1

        # ----------------------------------------------------
        # Inspect nested decision/execution result
        # ----------------------------------------------------

        for result in results:

            decision = result["decision"]
            execution = result["execution"]

            train_id = decision["train_id"]
            action = decision["action"]

            if action == "RELEASE":

                if (
                    execution is not None
                    and execution.get("executed", False)
                ):

                    release_count += 1

                    print(
                        f"[t={simulator.current_time_min:.1f}] "
                        f"{train_id} → RELEASE"
                    )

            elif action == "HOLD":

                print(
                    f"[t={simulator.current_time_min:.1f}] "
                    f"{train_id} → HOLD"
                )

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

    # ========================================================
    # RESULTS
    # ========================================================

    print("\n" + "=" * 60)
    print("BASELINE SIMULATION RESULTS")
    print("=" * 60)

    print(
        f"\nDecision steps: "
        f"{decision_steps}"
    )

    print(
        f"Baseline releases: "
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
        f"Total waiting: "
        f"{metrics['total_waiting_time_min']:.2f} min"
    )

    print(
        f"Average waiting: "
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

    print("\nSection utilization:")

    for section_id, utilization in (
        metrics["section_utilization_percent"].items()
    ):

        print(
            f"  {section_id}: "
            f"{utilization:.2f}%"
        )
    print("\n=== FINAL TRAIN STATES ===")

    for train_id, train in simulator.trains.items():

        print(
            train_id,
            "| status:", train.status,
            "| section:", train.current_section,
            "| station:", train.current_station,
            "| next:", train.next_station,
            "| section_index:", train.section_index,
            "| remaining:", round(train.remaining_time_min, 2)
        )

    print("\n" + "=" * 60)
    print("BASELINE SIMULATION COMPLETE")
    print("=" * 60)

    return simulator, metrics


def main():

    run_baseline_simulation(
        scenario_type="competition",
        num_trains=6,
        seed=42,
        simulation_time_min=240.0,
        decision_interval_min=5.0
    )


if __name__ == "__main__":
    main()