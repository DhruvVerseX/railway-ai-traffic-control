import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from simulation.network import RailwayNetwork
from simulation.simulator import RailwaySimulator
from input.input_state import TrainDatabase
from scenarios.mixed_scenario_builder import MixedScenarioBuilder

from controller.ai_safety_controller import AISafetyController


def print_result(result):

    print("\n" + "-" * 60)

    print(f"Train: {result['train_id']}")
    print(f"Next section: {result['next_section']}")

    print(f"ML recommendation: {result['ml_action']}")
    print(f"FINAL ACTION:       {result['final_action']}")

    print(f"Safe: {result['safe']}")

    print(f"Reason: {result['reason']}")

    if "conflict_reason" in result:
        print(
            f"Conflict reason: "
            f"{result['conflict_reason']}"
        )

    if "conflicting_train_id" in result:
        print(
            f"Conflicting train: "
            f"{result['conflicting_train_id']}"
        )

    print("Probabilities:")

    for action, probability in (
        result["probabilities"].items()
    ):
        print(
            f"  {action}: {probability:.4f}"
        )


def main():

    print("\n" + "=" * 60)
    print("TESTING AI + SAFETY CONTROLLER")
    print("=" * 60)

    # --------------------------------------------------------
    # Load components
    # --------------------------------------------------------

    network = RailwayNetwork()
    train_database = TrainDatabase()

    builder = MixedScenarioBuilder(
        network,
        train_database
    )

    # --------------------------------------------------------
    # Generate deliberate conflict scenario
    # --------------------------------------------------------

    traffic_state = builder.generate_mixed_scenario(
        scenario_id="AI_SAFETY_TEST",
        num_trains=6,
        scenario_type="conflict",
        decision_time_min=5,
        running_advance_min=5,
        seed=42
    )

    print("\nConflict scenario generated.")

    # --------------------------------------------------------
    # Create simulator
    # --------------------------------------------------------

    simulator = RailwaySimulator(network)

    simulator.load_traffic(
        traffic_state,
        train_database
    )

    # --------------------------------------------------------
    # Advance to decision point
    # --------------------------------------------------------

    simulator.advance_time(25)

    print(
        f"\nCurrent simulation time: "
        f"{simulator.current_time_min:.1f} min"
    )

    # --------------------------------------------------------
    # Show train states
    # --------------------------------------------------------

    print("\nTrain states:")

    for train_id, train in simulator.trains.items():

        if train.status in ["WAITING", "RUNNING"]:

            print(
                f"  {train_id} | "
                f"{train.status} | "
                f"station={train.current_station} | "
                f"section={train.current_section}"
            )

    # --------------------------------------------------------
    # Create AI safety controller
    # --------------------------------------------------------

    controller = AISafetyController(
        network,
        train_database
    )

    print("\nAI + safety controller loaded.")

    # --------------------------------------------------------
    # Test T026
    # --------------------------------------------------------

    print("\n" + "=" * 60)
    print("CONFLICT TEST: T026")
    print("=" * 60)

    result = controller.decide(
        simulator,
        "T026"
    )

    print_result(result)

    # --------------------------------------------------------
    # Test T004
    # --------------------------------------------------------

    print("\n" + "=" * 60)
    print("CONFLICT TEST: T004")
    print("=" * 60)

    result = controller.decide(
        simulator,
        "T004"
    )

    print_result(result)

    # --------------------------------------------------------
    # Complete
    # --------------------------------------------------------

    print("\n" + "=" * 60)
    print("AI + SAFETY TEST COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()