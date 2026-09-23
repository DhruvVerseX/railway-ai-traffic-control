import sys
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from simulation.network import RailwayNetwork
from simulation.train_movement import TrainMovementModel
from input.input_state import TrafficState


@dataclass
class SimulationTrain:
    train_id: str
    train_name: str
    direction: str

    entry_time_min: float
    delay_min: float = 0.0
    current_station: Optional[str] = None
    current_section: Optional[str] = None
    next_station: Optional[str] = None

    section_index: int = 0
    status: str = "NOT_ENTERED"

    remaining_time_min: float = 0.0


class RailwaySimulator:

    def __init__(self, network: RailwayNetwork):
        self.network = network

        self.movement_model = None

        self.current_time_min = 0.0

        self.trains = {}

        # Event history
        self.history = []

        # section_id -> train_id
        self.section_occupancy = {}
        # Conflict detector attached externally
        self._conflict_detector = None

    # ---------------------------------------------------------
    # EVENT LOGGING
    # ---------------------------------------------------------

    def log_event(self, event, train_id=None, section_id=None, **details):

        record = {
            "time_min": round(self.current_time_min, 2),
            "event": event,
            "train_id": train_id,
            "section_id": section_id,
        }

        record.update(details)

        self.history.append(record)

    # ---------------------------------------------------------
    # TRAIN MANAGEMENT
    # ---------------------------------------------------------

    def add_train(
        self,
        train_id,
        train_name,
        direction,
        entry_time_min=0.0,
        delay_min=0.0,
    ):

        self.trains[train_id] = SimulationTrain(
            train_id=train_id,
            train_name=train_name,
            direction=direction,
            entry_time_min=entry_time_min,
            delay_min=delay_min,
        )

    # ---------------------------------------------------------
    # SECTION HELPERS
    # ---------------------------------------------------------

    def _get_current_section_endpoints(self, section_id):

        section = self.network.get_section(section_id)

        return section.from_station, section.to_station

    # ---------------------------------------------------------
    # WAITING STATE
    # ---------------------------------------------------------

    def set_train_waiting(
        self,
        train_id,
        reason="",
        section_id=None,
    ):

        train = self.get_train_state(train_id)

        if train.status != "WAITING":

            train.status = "WAITING"

            self.log_event(
                "WAITING_STARTED",
                train_id=train_id,
                section_id=section_id,
                reason=reason,
            )

        else:

            # Useful for debugging/controller history,
            # but do not create repeated WAITING_STARTED events.
            pass

    def set_train_not_entered(self, train_id):

        train = self.get_train_state(train_id)

        train.status = "NOT_ENTERED"

    # ---------------------------------------------------------
    # START TRAIN
    # ---------------------------------------------------------

    def start_train(self, train_id):

        train = self.get_train_state(train_id)

        # Entry time has not been reached
        if self.current_time_min < train.entry_time_min:

            train.status = "NOT_ENTERED"

            return False

        if train.status not in (
            "NOT_ENTERED",
            "WAITING",
            "APPROACHING",
        ):

            return False

        # Create movement model
        movement = self.movement_model.build_movement(train_id)

        if train.section_index >= len(movement.section_sequence):

            train.status = "ARRIVED"

            return False

        section_id = movement.section_sequence[train.section_index]

        # Check whether section is occupied
        if section_id in self.section_occupancy:

            occupying_train = self.section_occupancy[section_id]

            self.set_train_waiting(
                train_id,
                reason="Section occupied",
                section_id=section_id,
            )

            self.log_event(
                "CONFLICT_DETECTED",
                train_id=train_id,
                section_id=section_id,
                conflicting_train_id=occupying_train,
                reason="Section occupied",
            )

            return False

        from_station, to_station = self._get_current_section_endpoints(
            section_id
        )

        # Determine movement direction
        if train.direction == "UP":

            train.current_station = from_station
            train.next_station = to_station

        elif train.direction == "DOWN":

            train.current_station = to_station
            train.next_station = from_station

        else:

            raise ValueError(
                f"Unknown direction for train {train_id}: "
                f"{train.direction}"
            )

        # If train was previously waiting, waiting has ended
        if train.status == "WAITING":

            self.log_event(
                "WAITING_ENDED",
                train_id=train_id,
                section_id=section_id,
            )

        # Occupy section
        self.section_occupancy[section_id] = train_id

        train.current_section = section_id
        train.status = "RUNNING"

        section = self.network.get_section(section_id)

        train_record = self.movement_model.train_database.get_train(
             train.train_id
        )

        train_speed = float(
             train_record["max_speed_kmph"]
        )

        train.remaining_time_min = section.travel_time(
             train_speed
        )

        # Use network travel time if section object does not
        # contain a train-specific method.
        if train.remaining_time_min <= 0:

            train.remaining_time_min = self.network.route_travel_time(
                train_id
            )

        self.log_event(
            "SECTION_ENTERED",
            train_id=train_id,
            section_id=section_id,
            from_station=train.current_station,
            to_station=train.next_station,
        )

        return True

    # ---------------------------------------------------------
    # ADVANCE TIME
    # ---------------------------------------------------------

    def advance_time(self, minutes):

        if minutes < 0:
            raise ValueError("Simulation time cannot move backwards.")

        target_time = self.current_time_min + minutes

        EPSILON = 1e-9

        while self.current_time_min < target_time - EPSILON:

            next_event_time = target_time

        # ---------------------------------------------
        # Find next section completion
        # ---------------------------------------------

            for train in self.trains.values():

                if (
                    train.status == "RUNNING"
                    and train.remaining_time_min > EPSILON
                ):

                    event_time = (
                        self.current_time_min
                        + train.remaining_time_min
                    )

                    if event_time < next_event_time - EPSILON:
                        next_event_time = event_time

        # ---------------------------------------------
        # Find next train entry time
        # ---------------------------------------------

            for train in self.trains.values():

                if (
                    train.status == "NOT_ENTERED"
                    and train.entry_time_min > self.current_time_min + EPSILON
                    and train.entry_time_min < next_event_time - EPSILON
                ):

                    next_event_time = train.entry_time_min

        # ---------------------------------------------
        # Advance time
        # ---------------------------------------------

            elapsed = next_event_time - self.current_time_min

            if elapsed > EPSILON:

                for train in self.trains.values():

                    if train.status == "RUNNING":

                        train.remaining_time_min -= elapsed

                        if train.remaining_time_min <= EPSILON:
                            train.remaining_time_min = 0.0

                self.current_time_min = next_event_time

        # ---------------------------------------------
        # Complete sections
        # ---------------------------------------------

            completed_trains = []

            for train in list(self.trains.values()):

                if (
                    train.status == "RUNNING"
                    and train.remaining_time_min <= EPSILON
                ):

                    completed_trains.append(train.train_id)

            for train_id in completed_trains:

                self.complete_current_section(train_id)

        # ---------------------------------------------
        # Entry events
        # ---------------------------------------------

            for train in self.trains.values():

                if (
                    train.status == "NOT_ENTERED"
                    and self.current_time_min >= train.entry_time_min - EPSILON
                ):

                    self.set_train_waiting(
                        train.train_id,
                        reason="Entry time reached",
                    )

        # ---------------------------------------------
        # Avoid infinite loop
        # ---------------------------------------------

            if elapsed <= EPSILON and not completed_trains:

                break
    def complete_current_section(self, train_id):

        train = self.get_train_state(train_id)

        section_id = train.current_section

        if section_id is None:
            return False

        # Release section
        if self.section_occupancy.get(section_id) == train_id:

            del self.section_occupancy[section_id]
            # Record section exit for headway tracking
            if self._conflict_detector is not None:

                self._conflict_detector.record_section_exit(
                    section_id
                )

        self.log_event(
            "SECTION_COMPLETED",
            train_id=train_id,
            section_id=section_id,
        )

        movement = self.movement_model.build_movement(train_id)

        # -----------------------------------------------------
        # FINAL DESTINATION
        # -----------------------------------------------------

        if train.section_index >= len(movement.section_sequence) - 1:

            train.current_station = train.next_station
            train.current_section = None
            train.next_station = None
            train.remaining_time_min = 0.0
            train.status = "ARRIVED"

            self.log_event(
                "TRAIN_ARRIVED",
                train_id=train_id,
                station_id=train.current_station,
            )

            return True

        # -----------------------------------------------------
        # MOVE TO NEXT SECTION
        # -----------------------------------------------------

        next_section_index = train.section_index + 1

        next_section_id = movement.section_sequence[
            next_section_index
        ]

        # Check whether next section is occupied
        if next_section_id in self.section_occupancy:

            occupying_train = self.section_occupancy[next_section_id]

            # IMPORTANT:
            # Do NOT increment section_index yet.
            # The train has not entered this section.

            train.current_section = None
            train.next_station = None
            train.remaining_time_min = 0.0

            self.set_train_waiting(
                train_id,
                reason="Next section occupied",
                section_id=next_section_id,
            )

            self.log_event(
                "CONFLICT_DETECTED",
                train_id=train_id,
                section_id=next_section_id,
                conflicting_train_id=occupying_train,
                reason="Next section occupied",
            )

            return False

        # -----------------------------------------------------
        # ENTER NEXT SECTION
        # -----------------------------------------------------

        train.section_index = next_section_index

        from_station, to_station = self._get_current_section_endpoints(
            next_section_id
        )

        if train.direction == "UP":

            train.current_station = from_station
            train.next_station = to_station

        else:

            train.current_station = to_station
            train.next_station = from_station

        self.section_occupancy[next_section_id] = train_id

        train.current_section = next_section_id
        train.status = "RUNNING"

        section = self.network.get_section(next_section_id)

        train_record = self.movement_model.train_database.get_train(
             train.train_id
        )

        train_speed = float(
             train_record["max_speed_kmph"]
        )

        train.remaining_time_min = section.travel_time(
             train_speed
        )

        if train.remaining_time_min <= 0:

            train.remaining_time_min = self.network.route_travel_time(
                train_id
            )

        self.log_event(
            "SECTION_ENTERED",
            train_id=train_id,
            section_id=next_section_id,
            from_station=train.current_station,
            to_station=train.next_station,
        )

        return True

    # ---------------------------------------------------------
    # LOAD TRAFFIC
    # ---------------------------------------------------------

    def load_traffic(
        self,
        traffic_state: TrafficState,
        train_database,
    ):

        self.trains.clear()
        self.section_occupancy.clear()
        self.history.clear()
        self.current_time_min = 0.0

        # Reset conflict timing for a fresh simulation
        if self._conflict_detector is not None:

            self._conflict_detector.last_exit_time.clear()

        self.movement_model = TrainMovementModel(
            self.network,
            train_database,
        )

        for train_state in traffic_state.trains:

            train_record = train_database.get_train(
                train_state.train_id
            )

            self.add_train(
                train_id=train_state.train_id,
                train_name=train_record["train_name"],
                direction=train_state.direction,
                entry_time_min=train_state.entry_time_min,
                delay_min=train_state.delay_min,
            )

            sim_train = self.trains[train_state.train_id]

            sim_train.current_station = train_state.location
            sim_train.current_section = train_state.current_section
            sim_train.next_station = train_state.next_station
            sim_train.status = train_state.status
            if sim_train.status == "WAITING":

                 self.log_event(
                    "WAITING_STARTED",
                    train_id=train_state.train_id,
                    section_id=train_state.current_section,
                    reason="Initial scenario waiting state",
             )

            # Determine section index
            movement = self.movement_model.build_movement(
                train_state.train_id
            )

            if train_state.current_section is not None:

                if train_state.current_section in movement.section_sequence:

                    sim_train.section_index = (
                        movement.section_sequence.index(
                            train_state.current_section
                        )
                    )

            else:

                # If the train is at its entry station,
                # section_index remains 0.
                sim_train.section_index = 0

            # Register existing section occupancy
            if (
                train_state.current_section is not None
                and sim_train.status == "RUNNING"
            ):

                self.section_occupancy[
                    train_state.current_section
                ] = train_state.train_id

            self.log_event(
                "SCENARIO_LOADED",
                train_id=train_state.train_id,
                section_id=train_state.current_section,
                status=sim_train.status,
            )

    # ---------------------------------------------------------
    # GETTERS
    # ---------------------------------------------------------

    def get_section_occupant(self, section_id):

        return self.section_occupancy.get(section_id)

    def get_train_state(self, train_id):

        if train_id not in self.trains:

            raise KeyError(
                f"Train {train_id} not found in simulator."
            )

        return self.trains[train_id]