from railway_ai.simulation.network import RailwayNetwork
from railway_ai.input.input_state import TrainDatabase
from railway_ai.simulation.simulator import RailwaySimulator
from railway_ai.scenarios.mixed_scenario_builder import MixedScenarioBuilder
from railway_ai.controller.ml_controller import MLTrainController
from railway_ai.controller.ai_controller import AISafetyController


def main():
    print("=" * 50)
    print("RANKING CANDIDATE DIAGNOSTIC")
    print("=" * 50)

    network = RailwayNetwork()
    train_database = TrainDatabase()

    builder = MixedScenarioBuilder(network, train_database)

    traffic_state = builder.generate_mixed_scenario(
        scenario_id="RANK_DIAG",
        num_trains=6,
        scenario_type="competition",
        decision_time_min=5.0,
        running_advance_min=5.0,
        seed=42
    )

    simulator = RailwaySimulator(network)
    simulator.load_traffic(traffic_state, train_database)

    ml_controller = MLTrainController(
        network,
        train_database
    )

    safety_controller = AISafetyController(
        network,
        train_database
    )

    print("\n=== TRAINS ===")

    for train in simulator.trains.values():
        print(
            f"{train.train_id} | "
            f"status={train.status} | "
            f"entry={train.entry_time_min:.2f} | "
            f"delay={train.delay_min:.2f}"
        )

    print("\n=== V2 PREDICTIONS ===")

    print(
        f"Number of simulator trains: "
        f"{len(simulator.trains)}"
    )

    for train_id, train in simulator.trains.items():

        print(
            f"\nChecking {train_id}: "
            f"status={train.status}"
        )

        if train.status != "WAITING":
            print("    SKIPPED: not WAITING")
            continue

        print("    Eligible for V2 prediction.")

        try:
            result = ml_controller.predict_train(
                simulator,
                train_id
            )

            print("    V2 prediction succeeded.")

            probabilities = result["probabilities"]

            print(
                f"    next={result.get('next_section')} | "
                f"P(RELEASE)="
                f"{probabilities.get('RELEASE', 0.0):.4f} | "
                f"P(HOLD)="
                f"{probabilities.get('HOLD', 0.0):.4f}"
            )

        except Exception as e:
            print(
                f"    V2 prediction ERROR: "
                f"{type(e).__name__}: {e}"
            )

    print("\n=== SAFETY CHECKS ===")

    for train_id, train in simulator.trains.items():

        if train.status != "WAITING":
            continue

        try:
            safety = safety_controller.decide(
                simulator,
                train_id
            )

            print(
                f"{train_id} | "
                f"FINAL={safety.get('final_action')} | "
                f"SAFE={safety.get('safe')} | "
                f"reason={safety.get('reason')}"
            )

        except Exception as e:
            print(
                f"{train_id} | "
                f"SAFETY ERROR: "
                f"{type(e).__name__}: {e}"
            )

    print("\n" + "=" * 50)
    print("DIAGNOSTIC COMPLETE")
    print("=" * 50)


if __name__ == "__main__":
    main()