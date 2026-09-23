import sys
import random
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from simulation.network import RailwayNetwork
from simulation.simulator import RailwaySimulator
from input.input_state import TrainDatabase, TrainState, TrafficState
from scenarios.scenario_generator import ScenarioGenerator


class MixedScenarioBuilder:

    def __init__(self, network, train_database):
        self.network = network
        self.train_database = train_database
        self.scenario_generator = ScenarioGenerator(
            train_database=train_database,
            network=network
        )

    # ---------------------------------------------------------
    # Basic helpers
    # ---------------------------------------------------------

    def get_first_section(self, train_id):
        movement = self.scenario_generator.movement_model.build_movement(train_id)
        return movement.section_sequence[0]

    def get_direction(self, train_id):
        return self.scenario_generator.get_train_direction(train_id)

    def get_trains_by_first_section(self):
        groups = {}

        for train_id in self.train_database.trains.keys():
            section_id = self.get_first_section(train_id)

            if section_id not in groups:
                groups[section_id] = []

            groups[section_id].append(train_id)

        return groups

    # ---------------------------------------------------------
    # Main scenario generator
    # ---------------------------------------------------------

    def generate_mixed_scenario(
        self,
        scenario_id,
        num_trains=6,
        scenario_type="random",
        decision_time_min=5.0,
        running_advance_min=5.0,
        seed=None
    ):

        if seed is not None:
            random.seed(seed)

        if num_trains < 2:
            raise ValueError("num_trains must be at least 2.")

        valid_types = {
            "random",
            "competition",
            "occupied",
            "conflict",
            "delay_priority"
        }

        if scenario_type not in valid_types:
            raise ValueError(
                f"Invalid scenario_type '{scenario_type}'. "
                f"Choose from {sorted(valid_types)}."
            )

        # -----------------------------------------------------
        # Generate a basic random scenario first
        # -----------------------------------------------------

        scenario = self.scenario_generator.generate_scenario(
            scenario_id=scenario_id,
            num_trains=num_trains,
            simulation_time_min=240.0,
            seed=seed
        )

        _, traffic_state = self._scenario_to_traffic_state(scenario)

        # -----------------------------------------------------
        # Adjust scenario according to scenario type
        # -----------------------------------------------------

        if scenario_type == "competition":
            traffic_state = self._make_competition_scenario(
                traffic_state,
                num_trains
            )

        elif scenario_type == "occupied":
            traffic_state = self._make_occupied_scenario(
                traffic_state,
                num_trains
            )

        elif scenario_type == "conflict":
            traffic_state = self._make_conflict_scenario(
                traffic_state,
                num_trains
            )

        elif scenario_type == "delay_priority":
            traffic_state = self._make_delay_priority_scenario(
                traffic_state,
                num_trains
            )

        # -----------------------------------------------------
        # Load into simulator
        # -----------------------------------------------------

        simulator = RailwaySimulator(self.network)

        simulator.load_traffic(
            traffic_state,
            self.train_database
        )

        # Move simulation to decision point
        simulator.advance_time(decision_time_min)

        # -----------------------------------------------------
        # Start selected running trains
        # -----------------------------------------------------

        running_train_ids = self._select_running_trains(
            traffic_state,
            scenario_type
        )

        for train_id in running_train_ids:
            simulator.start_train(train_id)

        # Give running trains some time to progress
        if running_train_ids:
            simulator.advance_time(running_advance_min)

        return self._simulator_to_traffic_state(simulator)

    # ---------------------------------------------------------
    # Scenario type: competition
    # ---------------------------------------------------------

    def _make_competition_scenario(self, traffic_state, num_trains):

        groups = self.get_trains_by_first_section()

        valid_groups = [
            ids for ids in groups.values()
            if len(ids) >= 3
        ]

        if not valid_groups:
            return traffic_state

        selected_group = random.choice(valid_groups)

        selected_ids = random.sample(
            selected_group,
            min(num_trains, len(selected_group))
        )

        # Keep selected trains and fill remaining slots randomly
        all_ids = [
            train.train_id
            for train in traffic_state.trains
        ]

        remaining_ids = [
            train_id
            for train_id in all_ids
            if train_id not in selected_ids
        ]

        while len(selected_ids) < num_trains and remaining_ids:
            selected_ids.append(
                random.choice(remaining_ids)
            )
            remaining_ids.remove(selected_ids[-1])

        for train in traffic_state.trains:

            if train.train_id in selected_ids:

                # Make all competing trains eligible at the
                # decision point.
                train.entry_time_min = round(
                    random.uniform(0.0, 3.0),
                    2
                )

                train.delay_min = train.entry_time_min

        return traffic_state

    # ---------------------------------------------------------
    # Scenario type: occupied section
    # ---------------------------------------------------------

    def _make_occupied_scenario(self, traffic_state, num_trains):

        groups = self.get_trains_by_first_section()

        valid_groups = [
            ids for ids in groups.values()
            if len(ids) >= 2
        ]

        if not valid_groups:
            return traffic_state

        selected_group = random.choice(valid_groups)

        selected_ids = random.sample(
            selected_group,
            min(num_trains, len(selected_group))
        )

        for train in traffic_state.trains:

            if train.train_id in selected_ids:
                train.entry_time_min = round(
                    random.uniform(0.0, 3.0),
                    2
                )

                train.delay_min = train.entry_time_min

        return traffic_state

    # ---------------------------------------------------------
    # Scenario type: opposite-direction conflict
    # ---------------------------------------------------------

    def _make_conflict_scenario(self, traffic_state, num_trains):

        # T004: MTJ -> NDLS
        # T026: PWL -> MTJ
        #
        # Both use S03 but approach it from opposite directions.

        conflict_pair = ["T004", "T026"]

        # Create completely correct states for the two
        # conflict trains.

        conflict_states = []

        for train_id in conflict_pair:

            train_data = self.train_database.get_train(train_id)

            direction = self.get_direction(train_id)

            conflict_states.append(
                TrainState(
                    train_id=train_id,
                    location=train_data["entry_station"],
                    direction=direction,
                    status="WAITING",
                    delay_min=0.0,
                    entry_time_min=0.0,
                    current_section=None,
                    next_station=None
                )
            )

        # Remove any existing copies of T004/T026.
        remaining_trains = [
            train
            for train in traffic_state.trains
            if train.train_id not in conflict_pair
        ]

        # Add the correctly constructed conflict pair.
        remaining_trains.extend(conflict_states)

        # Keep requested scenario size.
        # Always keep both conflict trains.
        other_trains = [
            train
            for train in remaining_trains
            if train.train_id not in conflict_pair
        ]

        other_trains = other_trains[:max(0, num_trains - 2)]

        final_trains = conflict_states + other_trains

        return TrafficState(trains=final_trains)
    def _make_delay_priority_scenario(
        self,
        traffic_state,
        num_trains
    ):

        for train in traffic_state.trains:

            train_data = self.train_database.get_train(
                train.train_id
            )

            priority = float(train_data["priority"])

            if priority >= 4:
                train.delay_min = round(
                    random.uniform(8.0, 20.0),
                    2
                )
            else:
                train.delay_min = round(
                    random.uniform(0.0, 5.0),
                    2
                )

            train.entry_time_min = train.delay_min

        return traffic_state

    # ---------------------------------------------------------
    # Select running trains
    # ---------------------------------------------------------

    def _select_running_trains(
        self,
        traffic_state,
        scenario_type
    ):

        eligible = [
            train
            for train in traffic_state.trains
            if train.status == "WAITING"
            and train.entry_time_min <= 5.0
        ]

        if not eligible:
            return []

        # For conflict scenarios, specifically start T004.
        if scenario_type == "conflict":

            for train in eligible:
                if train.train_id == "T004":
                    return ["T004"]

        # For occupied scenarios, start one train.
        if scenario_type == "occupied":
            selected = random.choice(eligible)
            return [selected.train_id]

        # Competition scenarios deliberately leave all
        # competing trains waiting.
        if scenario_type == "competition":
            return []

        # Normal/random case: start 1–2 trains.
        count = min(
            random.randint(1, 2),
            len(eligible)
        )

        selected = random.sample(
            eligible,
            count
        )

        return [
            train.train_id
            for train in selected
        ]

    # ---------------------------------------------------------
    # Convert scenario dictionary to TrafficState
    # ---------------------------------------------------------

    def _scenario_to_traffic_state(self, scenario):

        train_states = []

        for train_data in scenario["trains"]:

            train_states.append(
                TrainState(
                    train_id=train_data["train_id"],
                    location=train_data["location"],
                    direction=train_data["direction"],
                    status=train_data["status"],
                    delay_min=train_data["delay_min"],
                    entry_time_min=train_data["entry_time_min"],
                    current_section=train_data["current_section"],
                    next_station=train_data["next_station"]
                )
            )

        return (
            scenario,
            TrafficState(trains=train_states)
        )

    # ---------------------------------------------------------
    # Convert simulator state back to TrafficState
    # ---------------------------------------------------------

    def _simulator_to_traffic_state(self, simulator):

        train_states = []

        for train in simulator.trains.values():

            train_states.append(
                TrainState(
                    train_id=train.train_id,
                    location=train.current_station
                    or "UNKNOWN",
                    direction=train.direction,
                    status=(
                        "RUNNING"
                        if train.status == "RUNNING"
                        else "WAITING"
                        if train.status in {"WAITING", "NOT_ENTERED"}
                        else "ARRIVED"
                    ),
                    delay_min=train.delay_min,
                    entry_time_min=train.entry_time_min,
                    current_section=train.current_section,
                    next_station=train.next_station
                )
            )

        return TrafficState(trains=train_states)


# -------------------------------------------------------------
# Test
# -------------------------------------------------------------

if __name__ == "__main__":

    print("=== MIXED SCENARIO BUILDER TEST ===")

    network = RailwayNetwork()
    database = TrainDatabase()

    builder = MixedScenarioBuilder(
        network,
        database
    )

    scenario_types = [
        "random",
        "competition",
        "occupied",
        "conflict",
        "delay_priority"
    ]

    for scenario_type in scenario_types:

        print()
        print(f"--- {scenario_type.upper()} ---")

        traffic_state = builder.generate_mixed_scenario(
            scenario_id=f"TEST_{scenario_type}",
            num_trains=6,
            scenario_type=scenario_type,
            seed=42
        )

        for train in traffic_state.trains:

            print(
                f"{train.train_id} | "
                f"{train.status} | "
                f"station: {train.location} | "
                f"section: {train.current_section} | "
                f"next: {train.next_station} | "
                f"delay: {train.delay_min}"
            )

        print()