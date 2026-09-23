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

        train = simulator.trains[train_id]
        train_data = self.train_database.get_train(train_id)

        movement = self.movement_model.build_movement(train_id)

        section_id = None

        if train.section_index < len(movement.section_sequence):
            section_id = movement.section_sequence[
                train.section_index
            ]

        waiting = int(train.status == "WAITING")
        running = int(train.status == "RUNNING")
        arrived = int(train.status == "ARRIVED")

        next_section_occupied = 0

        if section_id is not None:
            for other_train in simulator.trains.values():

                if other_train.train_id == train_id:
                    continue

                if (
                    other_train.status == "RUNNING"
                    and other_train.current_section == section_id
                ):
                    next_section_occupied = 1
                    break

        features = {
            "train_id": train_id,
            "priority": float(train_data["priority"]),
            "delay_min": float(train.delay_min),
            "entry_time_min": float(train.entry_time_min),

            "waiting": waiting,
            "running": running,
            "arrived": arrived,

            "current_time_min": float(
                simulator.current_time_min
            ),

            "max_speed_kmph": float(
                train_data["max_speed_kmph"]
            ),

            "length_m": float(
                train_data["length_m"]
            ),

            "is_freight": int(
                str(train_data["is_freight"]).lower()
                == "true"
            ),

            "next_section": section_id,
            "next_section_occupied": next_section_occupied,
        }

        # Add occupancy state for every section.
        for section in self.network.sections.values():

            occupied = 0

            for other_train in simulator.trains.values():

                if (
                    other_train.status == "RUNNING"
                    and other_train.current_section
                    == section.section_id
                ):
                    occupied = 1
                    break

            features[
                f"section_{section.section_id}_occupied"
            ] = occupied

        return features

    # ---------------------------------------------------------
    # Generate training rows for one scenario
    # ---------------------------------------------------------

    def extract_candidate_features(self, simulator, train_id):

        sim_train = simulator.trains.get(train_id)

        if sim_train is None:
            return None

        train_data = self.train_database.get_train(train_id)

        if train_data is None:
            return None

        # --------------------------------------------------
        # MOVEMENT INFORMATION
        # --------------------------------------------------

        movement = self.movement_model.build_movement(train_id)

        section_index = sim_train.section_index

        if section_index >= len(movement.section_sequence):
            next_section = None
        else:
            next_section = movement.section_sequence[section_index]

        # --------------------------------------------------
        # BASIC TRAIN FEATURES
        # --------------------------------------------------

        priority = float(train_data["priority"])

        delay_min = float(sim_train.delay_min)

        entry_time_min = float(sim_train.entry_time_min)

        # --------------------------------------------------
        # TRAFFIC STATE
        # --------------------------------------------------

        waiting_trains = []

        for other_train_id, other_train in simulator.trains.items():

            if other_train_id == train_id:
                continue

            if other_train.status != "WAITING":
                continue

            if simulator.current_time < other_train.entry_time_min:
                continue

            waiting_trains.append(other_train_id)

        waiting_train_count = len(waiting_trains)

        # --------------------------------------------------
        # COMPETITION FOR SAME SECTION
        # --------------------------------------------------

        same_section_competitors = []

        if next_section is not None:

            for other_train_id in waiting_trains:

                other_movement = (
                    self.movement_model.build_movement(
                        other_train_id
                    )
                )

                other_train = simulator.trains[other_train_id]

                other_index = other_train.section_index

                if other_index >= len(
                    other_movement.section_sequence
                ):
                    continue

                other_next_section = (
                    other_movement.section_sequence[
                        other_index
                    ]
                )

                if other_next_section == next_section:

                    same_section_competitors.append(
                        other_train_id
                    )

        # --------------------------------------------------
        # COMPETITOR INFORMATION
        # --------------------------------------------------

        competitor_priorities = []
        competitor_delays = []

        for competitor_id in same_section_competitors:

            competitor_data = (
                self.train_database.get_train(
                    competitor_id
                )
            )

            competitor_train = (
                simulator.trains[competitor_id]
            )

            competitor_priorities.append(
                float(competitor_data["priority"])
            )

            competitor_delays.append(
                float(competitor_train.delay_min)
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
            priority - highest_competitor_priority
        )

        delay_advantage = (
            delay_min - highest_competitor_delay
        )

        # --------------------------------------------------
        # SECTION OCCUPANCY
        # --------------------------------------------------

        if next_section is not None:

            next_section_occupied = int(
                simulator.is_section_occupied(
                    next_section
                )
            )

        else:

            next_section_occupied = 0

        section_occupancy = {}

        for section_id in self.network.sections:

            section_occupancy[
                f"section_{section_id}_occupied"
            ] = int(
                simulator.is_section_occupied(
                    section_id
                )
            )

        # --------------------------------------------------
        # FINAL FEATURE VECTOR
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

            "current_time_min": (
                float(simulator.current_time)
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
                len(same_section_competitors),

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

    def save_to_csv(
        self,
        rows,
        output_path
    ):

        output_path = Path(output_path)
        output_path.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        if not rows:
            raise ValueError(
                "No training rows were generated."
            )

        fieldnames = list(rows[0].keys())

        with open(
            output_path,
            "w",
            newline="",
            encoding="utf-8"
        ) as file:

            writer = csv.DictWriter(
                file,
                fieldnames=fieldnames
            )

            writer.writeheader()
            writer.writerows(rows)


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
        / "training_data.csv"
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