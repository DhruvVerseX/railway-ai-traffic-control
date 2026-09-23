from training_data_generator import TrainingDataGenerator
from scenarios.mixed_scenario_builder import MixedScenarioBuilder
from simulation.network import RailwayNetwork
from input.input_state import TrainDatabase


def main():

    print("\n" + "=" * 60)
    print("TESTING TRAINING DATA V2")
    print("=" * 60)

    network = RailwayNetwork()
    train_database = TrainDatabase()

    generator = TrainingDataGenerator(
        network,
        train_database
    )

    builder = MixedScenarioBuilder(
        network,
        train_database
    )

    traffic_state = builder.generate_mixed_scenario(
        scenario_id="V2_TEST",
        num_trains=6,
        seed=42,
        scenario_type="competition",
        decision_time_min=5,
        running_advance_min=5
    )

    rows = generator.generate_for_scenario(
        traffic_state,
        "competition"
    )

    print("\nRows generated:", len(rows))

    if rows:

        print("\nFirst row keys:")

        print(
            list(rows[0].keys())
        )

        print("\nFirst row:")

        print(
            rows[0]
        )

        print("\nDecision times found:")

        times = sorted(
            set(
                row["current_time_min"]
                for row in rows
            )
        )

        print(times)

    else:

        print(
            "\nNo training rows were generated."
        )

    print("\n" + "=" * 60)
    print("V2 TEST COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()