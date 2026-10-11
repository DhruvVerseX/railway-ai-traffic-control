import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from simulation.simulator import RailwaySimulator


class ConflictDetector:

    def __init__(self, simulator: RailwaySimulator):

        self.simulator = simulator

        # Allow the simulator to notify this detector
        # whenever a section is released.
        self.simulator._conflict_detector = self

        # Stores the last time each section was released
        # section_id -> time_min
        self.last_exit_time = {}

    # ---------------------------------------------------------
    # SECTION OCCUPANCY
    # ---------------------------------------------------------

    def is_section_occupied(self, section_id):

        return section_id in self.simulator.section_occupancy

    def get_section_occupant(self, section_id):

        return self.simulator.get_section_occupant(section_id)

    # ---------------------------------------------------------
    # TRAIN DIRECTION
    # ---------------------------------------------------------

    def get_train_direction(self, train_id):

        train = self.simulator.get_train_state(train_id)

        return train.direction

    # ---------------------------------------------------------
    # RECORD SECTION EXIT
    # ---------------------------------------------------------

    def record_section_exit(self, section_id):

        self.last_exit_time[section_id] = (
            self.simulator.current_time_min
        )

    # ---------------------------------------------------------
    # CHECK SECTION CONFLICT
    # ---------------------------------------------------------

    def check_section_conflict(
        self,
        train_id,
        section_id,
    ):

        train_direction = self.get_train_direction(
            train_id
        )

        # -----------------------------------------------------
        # CASE 1: SECTION OCCUPIED
        # -----------------------------------------------------

        if self.is_section_occupied(section_id):

            occupying_train_id = self.get_section_occupant(
                section_id
            )

            # Same train is not a conflict
            if occupying_train_id == train_id:

                return {
                    "conflict": False,
                    "reason": "Section occupied by same train",
                    "required_wait_min": 0.0,
                    "conflicting_train_id": None,
                }

            occupying_direction = self.get_train_direction(
                occupying_train_id
            )

            if occupying_direction != train_direction:

                reason = "Opposite-direction conflict"

            else:

                reason = "Same-direction section conflict"

            result = {
                "conflict": True,
                "reason": reason,
                "required_wait_min": 0.0,
                "conflicting_train_id": occupying_train_id,
            }

            # Record conflict in simulator history
            # Log the conflict only if the same conflict has not
            # already been recorded at the current simulation time.
            already_logged = any(
                event.get("event") == "CONFLICT_DETECTED"
                and event.get("time_min") == self.simulator.current_time_min
                and event.get("train_id") == train_id
                and event.get("section_id") == section_id
                and event.get("conflicting_train_id") == occupying_train_id
                and event.get("reason") == reason
                for event in self.simulator.history
            )

            if not already_logged:
                self.simulator.log_event(
                    "CONFLICT_DETECTED",
                    train_id=train_id,
                    section_id=section_id,
                    conflicting_train_id=occupying_train_id,
                    reason=reason,
                )

            return result

        # -----------------------------------------------------
        # CASE 2: HEADWAY CONFLICT
        # -----------------------------------------------------

        if section_id in self.last_exit_time:

            last_exit = self.last_exit_time[section_id]

            elapsed = (
                self.simulator.current_time_min
                - last_exit
            )

            section = self.simulator.network.get_section(
                section_id
            )

            required_headway = section.minimum_headway_min

            if elapsed + 1e-9 < required_headway:

                required_wait = (
                    required_headway - elapsed
                )

                result = {
                    "conflict": True,
                    "reason": "Minimum headway not satisfied",
                    "required_wait_min": round(
                        required_wait,
                        2,
                    ),
                    "conflicting_train_id": None,
                }

                self.simulator.log_event(
                    "CONFLICT_DETECTED",
                    train_id=train_id,
                    section_id=section_id,
                    conflicting_train_id=None,
                    reason="Minimum headway not satisfied",
                    required_wait_min=round(
                        required_wait,
                        2,
                    ),
                )

                return result

        # -----------------------------------------------------
        # CASE 3: NO CONFLICT
        # -----------------------------------------------------

        return {
            "conflict": False,
            "reason": "Section available",
            "required_wait_min": 0.0,
            "conflicting_train_id": None,
        }
