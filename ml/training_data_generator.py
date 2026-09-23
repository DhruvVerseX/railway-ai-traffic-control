import sys
import csv
import random
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from simulation.network import RailwayNetwork
from simulation.simulator import RailwaySimulator
from simulation.train_movement import TrainMovementModel
from input.input_state import TrainDatabase
from optimizer.optimizer import TrainTrafficOptimizer
from scenarios.mixed_scenario_builder import MixedScenarioBuilder


class TrainingDataGenerator:

    def __init__(self, network, train_database):
        self.network = network
        self.train_database = train_database
        self.movement_model = TrainMovementModel(
            network,
            train_database
        )

    # ---------------------------------------------------------
    # Extract features for one candidate train
    # ---------------------------------------------------------

    def extract_candidate_features(
        self,
        simulator,
        train_id
    ):

        sim_train = simulator.trains.get(train_id)

        if sim_train is None:
            return None

        train_data = self.train_database.get_train(
            train_id
        )

        if train_data is None:
            return None

        # --------------------------------------------------
        # MOVEMENT INFORMATION
        # --------------------------------------------------

        movement = self.movement_model.build_movement(
            train_id
        )

        section_index = sim_train.section_index

        if section_index >= len(
            movement.section_sequence
        ):
            next_section = None
        else:
            next_section = movement.section_sequence[
                section_index
            ]

        # --------------------------------------------------
        # BASIC TRAIN FEATURES
        # --------------------------------------------------

        priority = float(
            train_data["priority"]
        )

        delay_min = float(
            sim_train.delay_min
        )

        entry_time_min = float(
            sim_train.entry_time_min
        )

        # --------------------------------------------------
        # WAITING TRAINS
        # --------------------------------------------------

        waiting_trains = []

        for (
            other_train_id,
            other_train
        ) in simulator.trains.items():

            if other_train_id == train_id:
                continue

            if other_train.status != "WAITING":
                continue

            if (
                simulator.current_time_min
                < other_train.entry_time_min
            ):
                continue

            waiting_trains.append(
                other_train_id
            )

        waiting_train_count = len(
            waiting_trains
        )

        # --------------------------------------------------
        # SAME-SECTION COMPETITORS
        # --------------------------------------------------

        same_section_competitors = []

        if next_section is not None:

            for other_train_id in waiting_trains:

                other_movement = (
                    self.movement_model.build_movement(
                        other_train_id
                    )
                )

                other_train = simulator.trains[
                    other_train_id
                ]

                other_index = (
                    other_train.section_index
                )

                if other_index >= len(
                    other_movement.section_sequence
                ):
                    continue

                other_next_section = (
                    other_movement.section_sequence[
                        other_index
                    ]
                )

                if (
                    other_next_section
                    == next_section
                ):
                    same_section_competitors.append(
                        other_train_id
                    )

        # --------------------------------------------------
        # COMPETITOR INFORMATION
        # --------------------------------------------------

        competitor_priorities = []
        competitor_delays = []

        for competitor_id in (
            same_section_competitors
        ):

            competitor_data = (
                self.train_database.get_train(
                    competitor_id
                )
            )

            competitor_train = (
                simulator.trains[
                    competitor_id
                ]
            )

            competitor_priorities.append(
                float(
                    competitor_data["priority"]
                )
            )

            competitor_delays.append(
                float(
                    competitor_train.delay_min
                )
            )

        if competitor_priorities:

            highest_competitor_priority = max(
                competitor_priorities
            )

            highest_competitor_delay = max(
                competitor_delays
            )

        else:

            highest_competitor_priority = 0.0
            highest_competitor_delay = 0.0

        # --------------------------------------------------
        # RELATIVE ADVANTAGES
        # --------------------------------------------------

        priority_advantage = (
            priority
            - highest_competitor_priority
        )

        delay_advantage = (
            delay_min
            - highest_competitor_delay
        )

        # --------------------------------------------------
        # NEXT SECTION OCCUPANCY
        # --------------------------------------------------

        if next_section is not None:

            next_section_occupied = int(
                simulator.get_section_occupant(
                    next_section
                ) is not None
            )

        else:

            next_section_occupied = 0

        # --------------------------------------------------
        # ALL SECTION OCCUPANCY
        # --------------------------------------------------

        section_occupancy = {}

        # Section occupancy features
        # Explicitly create a 0/1 feature for every section in the network.
        # This prevents missing values when a section is currently unoccupied.

        for section_id in self.network.sections:
            section_occupancy[f"section_{section_id}_occupied"] = (
                1 if simulator.get_section_occupant(section_id) is not None else 0
            )

        # --------------------------------------------------
        # FINAL FEATURES
        # --------------------------------------------------

        features = {

            "train_id": train_id,

            "priority": priority,

            "delay_min": delay_min,

            "entry_time_min": entry_time_min,

            "waiting": int(
                sim_train.status == "WAITING"
            ),

            "running": int(
                sim_train.status == "RUNNING"
            ),

            "arrived": int(
                sim_train.status == "ARRIVED"
            ),

            "current_time_min":
                float(
                    simulator.current_time_min
                ),

            "max_speed_kmph": float(
                train_data["max_speed_kmph"]
            ),

            "length_m": float(
                train_data["length_m"]
            ),

            "is_freight": int(
                train_data["train_type"].lower()
                == "freight"
            ),

            "next_section": next_section,

            "next_section_occupied":
                next_section_occupied,

            # NEW TRAFFIC FEATURES

            "waiting_train_count":
                waiting_train_count,

            "same_section_competitors":
                len(
                    same_section_competitors
                ),

            "highest_competitor_priority":
                highest_competitor_priority,

            "highest_competitor_delay":
                highest_competitor_delay,

            "priority_advantage":
                priority_advantage,

            "delay_advantage":
                delay_advantage,

            **section_occupancy,
        }

        return features

    # ---------------------------------------------------------
    # Generate training rows for one scenario
    # ---------------------------------------------------------

    def generate_for_scenario(
        self,
        traffic_state,
        scenario_type
    ):

        simulator = RailwaySimulator(self.network)

        simulator.load_traffic(
            traffic_state,
            self.train_database
        )

        rows = []

        # -----------------------------------------------------
        # Multiple decision points.
        #
        # At each checkpoint:
        # 1. Observe current traffic state.
        # 2. Generate candidate actions.
        # 3. Find globally best action.
        # 4. Create training examples.
        # 5. Apply the selected RELEASE, if any.
        # 6. Continue simulation.
        # -----------------------------------------------------

        decision_times = list(
            range(5, 61, 5)
        )

        for decision_time in decision_times:

            # -------------------------------------------------
            # Advance simulator to this decision point.
            # -------------------------------------------------

            time_to_advance = (
                decision_time
                - simulator.current_time_min
            )

            if time_to_advance > 0:

                simulator.advance_time(
                    time_to_advance
                )

            # -------------------------------------------------
            # Create optimizer for current traffic state.
            # -------------------------------------------------

            optimizer = TrainTrafficOptimizer(
                simulator,
                self.train_database,
                evaluation_horizon_min=240.0
            )

            result = optimizer.find_best_action()

            evaluations = result.get(
                "evaluations",
                []
            )

            best_action = result.get(
                "best_action"
            )

            # -------------------------------------------------
            # No valid decision at this time.
            #
            # Continue to the next checkpoint because trains
            # may become eligible later.
            # -------------------------------------------------

            if not evaluations or best_action is None:
                continue

            # -------------------------------------------------
            # Create one example for every eligible candidate
            # train at this decision point.
            #
            # The GLOBAL optimizer decision determines the label.
            # -------------------------------------------------

            for train in simulator.trains.values():

                if train.status != "WAITING":
                    continue

                if (
                    simulator.current_time_min
                    < train.entry_time_min
                ):
                    continue

                train_evaluations = [
                    evaluation
                    for evaluation in evaluations
                    if evaluation["train_id"]
                    == train.train_id
                ]

                if not train_evaluations:
                    continue

                features = (
                    self.extract_candidate_features(
                        simulator,
                        train.train_id
                    )
                )

                if features is None:
                    continue

                # -------------------------------------------------
                # Only the globally selected RELEASE gets
                # a RELEASE label.
                #
                # Every other candidate receives HOLD.
                # -------------------------------------------------

                if (
                    best_action["train_id"]
                    == train.train_id
                    and best_action["action"]
                    == "RELEASE"
                ):

                    target_action = "RELEASE"

                else:

                    target_action = "HOLD"

                # -------------------------------------------------
                # Best score obtained by this candidate train.
                # -------------------------------------------------

                best_train_evaluation = max(
                    train_evaluations,
                    key=lambda item: item["score"]
                )

                row = {
                    **features,
                    "scenario_type": scenario_type,
                    "target_action": target_action,
                    "target_score":
                        best_train_evaluation["score"],
                }

                rows.append(row)

            # -------------------------------------------------
            # APPLY GLOBAL BEST ACTION
            #
            # We only physically execute RELEASE.
            # HOLD means we simply leave the train waiting.
            # -------------------------------------------------

            if (
                best_action["action"]
                == "RELEASE"
            ):

                simulator.start_train(
                    best_action["train_id"]
                )

        return rows

    # ---------------------------------------------------------
    # Generate many scenarios
    # ---------------------------------------------------------

    def generate_dataset(
        self,
        num_scenarios=500,
        min_trains=4,
        max_trains=8,
        seed=42
    ):

        random.seed(seed)

        builder = MixedScenarioBuilder(
            self.network,
            self.train_database
        )

        all_rows = []

        scenario_counts = {
            "random": 0,
            "competition": 0,
            "occupied": 0,
            "conflict": 0,
            "delay_priority": 0,
        }

        for i in range(1, num_scenarios + 1):

            num_trains = random.randint(
                min_trains,
                max_trains
            )

            scenario_type = random.choices(
                [
                    "random",
                    "competition",
                    "occupied",
                    "conflict",
                    "delay_priority",
                ],
                weights=[
                    30,
                    25,
                    20,
                    15,
                    10,
                ],
                k=1
            )[0]

            scenario_counts[scenario_type] += 1

            traffic_state = builder.generate_mixed_scenario(
                scenario_id=f"ML_{i:04d}",
                num_trains=num_trains,
                scenario_type=scenario_type,
                decision_time_min=5.0,
                running_advance_min=5.0,
                seed=seed + i
            )

            rows = self.generate_for_scenario(
                traffic_state,
                scenario_type
            )

            all_rows.extend(rows)

            if i % 50 == 0:
                print(
                    f"Processed {i}/{num_scenarios} "
                    f"scenarios | Rows: {len(all_rows)}"
                )

        return all_rows, scenario_counts

    # ---------------------------------------------------------
    # Save dataset
    # ---------------------------------------------------------

    def save_to_csv(self, rows, output_path):
        """
        Save generated training rows to a CSV file.
        Field names are taken automatically from the generated data.
        """
        if not rows:
            print("No rows to save.")
            return

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        fieldnames = []
        seen = set()

        for row in rows:
            for key in row.keys():
                if key not in seen:
                    fieldnames.append(key)
                    seen.add(key)

        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=fieldnames,
                extrasaction="ignore"
            )

            writer.writeheader()
            writer.writerows(rows)

        print(f"Training data saved to: {output_path}")
        print(f"Rows: {len(rows)}")
        print(f"Columns: {len(fieldnames)}")


# -------------------------------------------------------------
# Main
# -------------------------------------------------------------

if __name__ == "__main__":

    print(
        "=== TRAINING DATASET GENERATION TEST ==="
    )

    network = RailwayNetwork()
    database = TrainDatabase()

    generator = TrainingDataGenerator(
        network,
        database
    )

    rows, scenario_counts = generator.generate_dataset(
        num_scenarios=500,
        min_trains=4,
        max_trains=8,
        seed=42
    )

    output_path = (
        PROJECT_ROOT
        / "ml"
        / "data"
        / "training_data_v2.csv"
    )

    generator.save_to_csv(
        rows,
        output_path
    )

    release_count = sum(
        row["target_action"] == "RELEASE"
        for row in rows
    )

    hold_count = sum(
        row["target_action"] == "HOLD"
        for row in rows
    )

    occupied_count = sum(
        int(row["next_section_occupied"]) == 1
        for row in rows
    )

    hold_occupied = sum(
        row["target_action"] == "HOLD"
        and int(row["next_section_occupied"]) == 1
        for row in rows
    )

    hold_free = sum(
        row["target_action"] == "HOLD"
        and int(row["next_section_occupied"]) == 0
        for row in rows
    )

    release_occupied = sum(
        row["target_action"] == "RELEASE"
        and int(row["next_section_occupied"]) == 1
        for row in rows
    )

    release_free = sum(
        row["target_action"] == "RELEASE"
        and int(row["next_section_occupied"]) == 0
        for row in rows
    )

    print()
    print("=== SCENARIO DISTRIBUTION ===")

    for scenario_type, count in scenario_counts.items():
        print(
            f"{scenario_type}: {count}"
        )

    print()
    print("=== DATASET SUMMARY ===")

    print(
        f"Total training rows: {len(rows)}"
    )

    print(
        f"RELEASE rows: {release_count}"
    )

    print(
        f"HOLD rows: {hold_count}"
    )

    print(
        f"RELEASE percentage: "
        f"{release_count / len(rows) * 100:.2f}%"
    )

    print(
        f"HOLD percentage: "
        f"{hold_count / len(rows) * 100:.2f}%"
    )

    print()
    print("=== OCCUPANCY / ACTION BREAKDOWN ===")

    print(
        f"Occupied section rows: "
        f"{occupied_count}"
    )

    print(
        f"HOLD + occupied: "
        f"{hold_occupied}"
    )

    print(
        f"HOLD + free: "
        f"{hold_free}"
    )

    print(
        f"RELEASE + occupied: "
        f"{release_occupied}"
    )

    print(
        f"RELEASE + free: "
        f"{release_free}"
    )

    print()
    print("Saved to:")
    print(output_path)