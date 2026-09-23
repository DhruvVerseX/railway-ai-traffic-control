import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from simulation.network import RailwayNetwork
from simulation.simulator import RailwaySimulator
from input.input_state import TrainDatabase
from scenarios.mixed_scenario_builder import MixedScenarioBuilder

from controller.ai_controller import AITrainTrafficController


def main():

    print("\n" + "=" * 60)
    print("TESTING AI TRAFFIC CONTROLLER")
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
    # Generate scenario
    # --------------------------------------------------------

    traffic_state = builder.generate_mixed_scenario(
        scenario_id="AI_CONTROLLER_TEST",
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

    simulator.load_traffic(
        traffic_state,
        train_database
    )

    simulator.advance_time(5)

    print(
        f"\nCurrent time: "
        f"{simulator.current_time_min:.1f} min"
    )

    # --------------------------------------------------------
    # Create AI controller
    # --------------------------------------------------------

    controller = AITrainTrafficController(
        network,
        train_database
    )

    print("\nAI controller loaded.")

    # --------------------------------------------------------
    # Perform control step
    # --------------------------------------------------------

    result = controller.control_step(
        simulator
    )

    # --------------------------------------------------------
    # Print recommendations
    # --------------------------------------------------------

    print("\n" + "=" * 60)
    print("AI RECOMMENDATIONS")
    print("=" * 60)

    for recommendation in result["recommendations"]:

        print(
            f"\nTrain: "
            f"{recommendation['train_id']}"
        )

        print(
            f"Next section: "
            f"{recommendation['next_section']}"
        )

        print(
            f"ML action: "
            f"{recommendation['ml_action']}"
        )

        print(
            f"Final action: "
            f"{recommendation['final_action']}"
        )

        print(
            f"Safe: "
            f"{recommendation['safe']}"
        )

        print(
            f"RELEASE probability: "
            f"{recommendation['probabilities']['RELEASE']:.4f}"
        )

    # --------------------------------------------------------
    # Selected action
    # --------------------------------------------------------

    print("\n" + "=" * 60)
    print("SELECTED ACTION")
    print("=" * 60)

    selected = result["selected_action"]

    if selected is None:

        print("\nNo action selected.")

    else:

        print(
            f"\nTrain: "
            f"{selected['train_id']}"
        )

        print(
            f"Action: "
            f"{selected['final_action']}"
        )

        print(
            f"Next section: "
            f"{selected['next_section']}"
        )

    # --------------------------------------------------------
    # Execution
    # --------------------------------------------------------

    print("\n" + "=" * 60)
    print("EXECUTION")
    print("=" * 60)

    print(
        f"\nExecuted: "
        f"{result['execution']['executed']}"
    )

    print(
        f"Reason: "
        f"{result['execution']['reason']}"
    )

    print("\n" + "=" * 60)
    print("AI CONTROLLER TEST COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()