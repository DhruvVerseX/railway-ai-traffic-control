import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from simulation.network import RailwayNetwork
from simulation.simulator import RailwaySimulator
from input.input_state import TrainDatabase
from scenarios.mixed_scenario_builder import MixedScenarioBuilder
from controller.ai_controller import AITrainTrafficController


def print_train_states(simulator):

    print("\nTRAIN STATES")
    print("-" * 80)

    for train_id, train in simulator.trains.items():

        if train.status not in ["WAITING", "RUNNING"]:
            continue

        if train.status == "WAITING":

            print(
                f"{train_id:5} | "
                f"WAITING | "
                f"station={train.current_station}"
            )

        else:

            print(
                f"{train_id:5} | "
                f"RUNNING  | "
                f"section={train.current_section}"
            )


def print_section_occupancy(simulator):

    print("\nSECTION OCCUPANCY")
    print("-" * 80)

    occupied = False

    for section_id, train_id in simulator.section_occupancy.items():

        if train_id is not None:

            print(
                f"{section_id}: {train_id}"
            )

            occupied = True

    if not occupied:
        print("No sections occupied.")


def main():

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
    # GENERATE SAME SCENARIO AS AI TEST
    # ========================================================

    traffic_state = builder.generate_mixed_scenario(
        scenario_id="AI_DEBUG",
        num_trains=6,
        scenario_type="competition",
        decision_time_min=5.0,
        running_advance_min=5.0,
        seed=42
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
    # CREATE AI CONTROLLER
    # ========================================================

    controller = AITrainTrafficController(
        network,
        train_database
    )

    # ========================================================
    # DIAGNOSTIC LOOP
    # ========================================================

    print("=" * 80)
    print("AI CONTROLLER DIAGNOSTIC")
    print("=" * 80)

    while simulator.current_time_min < 120:

        print("\n\n")
        print("=" * 80)

        print(
            f"SIMULATION TIME: "
            f"{simulator.current_time_min:.1f} min"
        )

        print("=" * 80)

        # ----------------------------------------------------
        # Current trains
        # ----------------------------------------------------

        print_train_states(
            simulator
        )

        # ----------------------------------------------------
        # Current section occupancy
        # ----------------------------------------------------

        print_section_occupancy(
            simulator
        )

        # ----------------------------------------------------
        # AI recommendations
        # ----------------------------------------------------

        recommendations = controller.get_recommendations(
            simulator
        )

        print("\nAI RECOMMENDATIONS")
        print("-" * 80)

        if not recommendations:

            print("No eligible trains.")

        else:

            for recommendation in recommendations:

                train_id = recommendation[
                    "train_id"
                ]

                final_action = recommendation[
                    "final_action"
                ]

                safe = recommendation[
                    "safe"
                ]

                probabilities = recommendation.get(
                    "probabilities",
                    {}
                )

                release_probability = probabilities.get(
                    "RELEASE",
                    0.0
                )

                hold_probability = probabilities.get(
                    "HOLD",
                    0.0
                )

                next_section = recommendation.get(
                    "next_section",
                    "N/A"
                )

                print(
                    f"{train_id:5} | "
                    f"next={next_section:4} | "
                    f"P(RELEASE)="
                    f"{release_probability:.3f} | "
                    f"P(HOLD)="
                    f"{hold_probability:.3f} | "
                    f"FINAL={final_action:7} | "
                    f"SAFE={safe}"
                )

                # Print safety information if available

                if "reason" in recommendation:

                    print(
                        f"       Reason: "
                        f"{recommendation['reason']}"
                    )

        # ----------------------------------------------------
        # Select action
        # ----------------------------------------------------

        selected = controller.select_action(
            recommendations
        )

        print("\nSELECTED ACTION")
        print("-" * 80)

        if selected is None:

            print("No action selected.")

        else:

            print(
                f"Train: "
                f"{selected['train_id']}"
            )

            print(
                f"Action: "
                f"{selected['final_action']}"
            )

            print(
                f"Section: "
                f"{selected.get('next_section', 'N/A')}"
            )

            probabilities = selected.get(
                "probabilities",
                {}
            )

            print(
                f"P(RELEASE): "
                f"{probabilities.get('RELEASE', 0.0):.3f}"
            )

            print(
                f"P(HOLD): "
                f"{probabilities.get('HOLD', 0.0):.3f}"
            )

        # ----------------------------------------------------
        # Execute
        # ----------------------------------------------------

        execution = controller.execute_action(
            simulator,
            selected
        )

        print("\nEXECUTION")
        print("-" * 80)

        print(
            execution
        )

        # ----------------------------------------------------
        # Advance
        # ----------------------------------------------------

        simulator.advance_time(
            5.0
        )

    print("\n\n")
    print("=" * 80)
    print("DIAGNOSTIC COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()