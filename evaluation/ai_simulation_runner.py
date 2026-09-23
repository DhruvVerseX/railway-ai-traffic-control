import sys
from pathlib import Path

from sklearn import metrics

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from metrics import metrics
from simulation.network import RailwayNetwork
from simulation.simulator import RailwaySimulator
from input.input_state import TrainDatabase
from scenarios.mixed_scenario_builder import MixedScenarioBuilder
from metrics.metrics import SimulationMetrics

from controller.ai_controller import AITrainTrafficController


def run_ai_simulation(
    scenario_type="competition",
    num_trains=6,
    seed=42,
    simulation_time_min=240.0,
    decision_interval_min=5.0
):
    """
    Run one complete simulation using the AI controller.
    """

    # --------------------------------------------------------
    # Load project components
    # --------------------------------------------------------

    network = RailwayNetwork()
    train_database = TrainDatabase()

    builder = MixedScenarioBuilder(
        network,
        train_database
    )

    # --------------------------------------------------------
    # Generate scenario
    # --------------------------------------------------------

    traffic_state = builder.generate_mixed_scenario(
        scenario_id="AI_SIM_TEST",
        num_trains=num_trains,
        scenario_type=scenario_type,
        decision_time_min=5.0,
        running_advance_min=5.0,
        seed=seed
    )

    # --------------------------------------------------------
    # Create simulator
    # --------------------------------------------------------

    simulator = RailwaySimulator(network)

    simulator.load_traffic(
        traffic_state,
        train_database
    )

    # --------------------------------------------------------
    # Create AI controller
    # --------------------------------------------------------

    controller = AITrainTrafficController(
        network,
        train_database
    )

    # --------------------------------------------------------
    # Control loop
    # --------------------------------------------------------

    print("\n" + "=" * 60)
    print("AI SIMULATION")
    print("=" * 60)

    print(f"\nScenario type: {scenario_type}")
    print(f"Trains: {num_trains}")
    print(f"Seed: {seed}")
    print(
        f"Simulation horizon: "
        f"{simulation_time_min} min"
    )

    decision_count = 0
    release_count = 0

    while simulator.current_time_min < simulation_time_min:

        # ----------------------------------------------------
        # AI decision
        # ----------------------------------------------------

        decision = controller.control_step(
            simulator
        )

        decision_count += 1

        selected = decision["selected_action"]

        if selected is not None:

            train_id = selected["train_id"]
            action = selected["final_action"]

            print(
                f"\n[t={simulator.current_time_min:.1f}] "
                f"{train_id} → {action}"
            )

            if action == "RELEASE":
                release_count += 1

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

    # --------------------------------------------------------
    # Calculate metrics
    # --------------------------------------------------------

    metrics_engine = SimulationMetrics(
        simulator
    )

    metrics = metrics_engine.calculate_all()

    print("\n" + "=" * 60)
    print("AI SIMULATION RESULTS")
    print("=" * 60)

    print(
        f"\nDecision steps: {decision_count}"
    )

    print(
    f"AI releases: {release_count}"
    )

    print(
    f"Completed trains: "
    f"{metrics['completed_trains']}"
    )

    print(
        f"Throughput: "
        f"{metrics['throughput_trains_per_hour']:.2f} trains/hour"
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
            f"  {section_id}: {utilization:.2f}%"
        )

    print("\n" + "=" * 60)
    print("AI SIMULATION COMPLETE")
    print("=" * 60)

    return simulator, metrics


def main():

    run_ai_simulation(
        scenario_type="competition",
        num_trains=6,
        seed=42,
        simulation_time_min=240.0,
        decision_interval_min=5.0
    )


if __name__ == "__main__":
    main()