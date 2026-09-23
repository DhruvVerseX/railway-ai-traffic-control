import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
from simulation.network import RailwayNetwork
from input.input_state import TrainDatabase
from scenarios.mixed_scenario_builder import MixedScenarioBuilder
from simulation.simulator import RailwaySimulator

from ml_controller import MLTrainController


def main():

    print("\n" + "=" * 60)
    print("TESTING AUTOMATIC ML TRAIN PREDICTION")
    print("=" * 60)

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
    # Create a scenario
    # --------------------------------------------------------

    traffic_state = builder.generate_mixed_scenario(
        scenario_id="ML_CONTROLLER_TEST",
        num_trains=6,
        scenario_type="competition",
        decision_time_min=5,
        running_advance_min=5,
        seed=42
    )

    # --------------------------------------------------------
    # Create simulator
    # --------------------------------------------------------

    simulator = RailwaySimulator(network)

    simulator.load_traffic(traffic_state, train_database)

    # --------------------------------------------------------
    # Move simulator to decision point
    # --------------------------------------------------------

    simulator.advance_time(5)

    print(
        f"\nCurrent simulation time: "
        f"{simulator.current_time_min:.1f} min"
    )

    # --------------------------------------------------------
    # Create ML controller
    # --------------------------------------------------------

    controller = MLTrainController(
        network,
        train_database
    )

    print("\nML model loaded successfully.")

    # --------------------------------------------------------
    # Find waiting trains
    # --------------------------------------------------------

    waiting_trains = [
        train_id
        for train_id, train in simulator.trains.items()
        if train.status == "WAITING"
        and simulator.current_time_min >= train.entry_time_min
    ]

    print(
        f"\nEligible waiting trains: "
        f"{len(waiting_trains)}"
    )

    # --------------------------------------------------------
    # Predict for every waiting train
    # --------------------------------------------------------

    for train_id in waiting_trains:

        result = controller.predict_train(
            simulator,
            train_id
        )

        print("\n" + "-" * 50)

        print(f"Train: {train_id}")

        print(
            f"Next section: "
            f"{result['next_section']}"
        )

        print(
            f"Recommendation: "
            f"{result['action']}"
        )

        print("Probabilities:")

        for action, probability in (
            result["probabilities"].items()
        ):

            print(
                f"  {action}: "
                f"{probability:.4f}"
            )

    print("\n" + "=" * 60)
    print("AUTOMATIC ML PREDICTION TEST COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()