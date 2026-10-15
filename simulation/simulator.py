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
    waiting_time_min: float = 0.0
    ready_time_min: float = 0.0


class RailwaySimulator:

    def __init__(self, network: RailwayNetwork):
        self.network = network

        self.movement_model = None

        self.current_time_min = 0.0

        self.trains = {}
        self.dispatch_at_stations = False

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
        interlocking = getattr(self, 'interlocking', None)
        if interlocking is not None and interlocking.blocked_reason(train_id):
            return False

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

        if self.current_time_min < train.ready_time_min - 1e-9:
            return False

        # Create movement model
        movement = self.movement_model.build_movement(train_id)

        if train.section_index >= len(movement.section_sequence):

            train.status = "ARRIVED"

            return False

        section_id = movement.section_sequence[train.section_index]

        if self._conflict_detector is not None:
            conflict = self._conflict_detector.check_section_conflict(train_id, section_id)
            if conflict['conflict']:
                self.set_train_waiting(train_id, reason=conflict['reason'], section_id=section_id)
                return False
        elif section_id in self.section_occupancy:
            self.set_train_waiting(train_id, reason='Section occupied', section_id=section_id)
            return False

        from_station, to_station = self._get_current_section_endpoints(
            section_id
        )

        # The route's actual station is authoritative, including branch routes.
        if train.current_station == from_station:
            train.next_station = to_station
        elif train.current_station == to_station:
            train.next_station = from_station
        else:
            raise ValueError(f'Train {train_id} is not at an endpoint of {section_id}')

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

                    if train.status in {'WAITING', 'NOT_ENTERED', 'APPROACHING'}:
                        eligible_time = max(self.current_time_min, train.entry_time_min, train.ready_time_min)
                        waited = max(0.0, next_event_time - eligible_time)
                        train.waiting_time_min += waited
                        train.delay_min += waited
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
        if self.section_occupancy.get(section_id) == train_id:
            del self.section_occupancy[section_id]
            if self._conflict_detector is not None:
                self._conflict_detector.record_section_exit(section_id)
        train.current_station = train.next_station
        train.current_section = None
        train.next_station = None
        train.remaining_time_min = 0.0
        train.section_index += 1
        self.log_event('SECTION_COMPLETED', train_id=train_id, section_id=section_id,
                       station_id=train.current_station)
        movement = self.movement_model.build_movement(train_id)
        if train.section_index >= len(movement.section_sequence):
            train.status = 'ARRIVED'
            self.log_event('TRAIN_ARRIVED', train_id=train_id, station_id=train.current_station)
            return True
        record = self.movement_model.train_database.get_train(train_id)
        dwell = float(record.get('dwell_min', 0)) if self.dispatch_at_stations and str(record.get('stops_intermediate')).lower() == 'true' else 0.0
        train.ready_time_min = self.current_time_min + dwell
        self.set_train_waiting(train_id, reason='Reached next station',
                               section_id=movement.section_sequence[train.section_index])
        if not self.dispatch_at_stations:
            return self.start_train(train_id)
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
                cursor = train_record['entry_station']
                sim_train.section_index = len(movement.section_sequence)
                for index, sid in enumerate(movement.section_sequence):
                    if cursor == sim_train.current_station:
                        sim_train.section_index = index
                        break
                    section = self.network.get_section(sid)
                    cursor = section.to_station if cursor == section.from_station else section.from_station
                if sim_train.section_index == len(movement.section_sequence) and sim_train.status != 'ARRIVED':
                    raise ValueError(f'Invalid station for {sim_train.train_id}')

            if sim_train.status == 'RUNNING':
                section = self.network.get_section(sim_train.current_section)
                sim_train.remaining_time_min = section.travel_time(float(train_record['max_speed_kmph']))

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
