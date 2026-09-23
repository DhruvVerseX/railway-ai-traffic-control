import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from simulation.simulator import RailwaySimulator


class SimulationMetrics:

    def __init__(self, simulator: RailwaySimulator):

        self.simulator = simulator

    # ---------------------------------------------------------
    # BASIC METRICS
    # ---------------------------------------------------------

    def count_completed_trains(self):

        return sum(
            1
            for train in self.simulator.trains.values()
            if train.status == "ARRIVED"
        )

    # ---------------------------------------------------------
    # THROUGHPUT
    # ---------------------------------------------------------

    def calculate_throughput(self):

        simulation_time_hours = (
            self.simulator.current_time_min / 60.0
        )

        if simulation_time_hours <= 0:
            return 0.0

        completed_trains = self.count_completed_trains()

        return completed_trains / simulation_time_hours

    # ---------------------------------------------------------
    # INITIAL DELAY
    # ---------------------------------------------------------

    def calculate_initial_delay(self):

        total_delay = 0.0

        for event in self.simulator.history:

            if event["event"] != "SCENARIO_LOADED":
                continue

            train_id = event["train_id"]

            train = self.simulator.get_train_state(
                train_id
            )

            total_delay += train.entry_time_min

        return round(total_delay, 2)

    # ---------------------------------------------------------
    # WAITING TIME
    # ---------------------------------------------------------

    def calculate_total_waiting_time(self):

        total_waiting = 0.0

        waiting_start = {}

        # Process events in chronological order
        for event in self.simulator.history:

            train_id = event["train_id"]
            event_type = event["event"]
            event_time = event["time_min"]

            if event_type == "WAITING_STARTED":

                # Only record the first currently-open
                # waiting interval.
                if train_id not in waiting_start:

                    waiting_start[train_id] = event_time

            elif event_type == "WAITING_ENDED":

                if train_id in waiting_start:

                    start_time = waiting_start.pop(
                        train_id
                    )

                    total_waiting += (
                        event_time - start_time
                    )

        # If a train is still waiting at simulation end,
        # count waiting until the end of simulation.
        simulation_end = self.simulator.current_time_min

        for train_id, start_time in waiting_start.items():

            total_waiting += (
                simulation_end - start_time
            )

        return round(total_waiting, 2)

    # ---------------------------------------------------------
    # AVERAGE WAITING TIME
    # ---------------------------------------------------------

    def calculate_average_waiting_time(self):

        train_count = len(self.simulator.trains)

        if train_count == 0:
            return 0.0

        total_waiting = self.calculate_total_waiting_time()

        return round(
            total_waiting / train_count,
            2
        )

    # ---------------------------------------------------------
    # CONFLICTS
    # ---------------------------------------------------------

    def count_conflicts(self):

        unique_conflicts = set()

        for event in self.simulator.history:

            if event["event"] != "CONFLICT_DETECTED":
                continue

            train_id = event.get("train_id")
            section_id = event.get("section_id")
            conflicting_train_id = event.get(
                "conflicting_train_id"
            )
            reason = event.get("reason")

            # For headway conflicts there may be no
            # conflicting train ID.
            conflict_key = (
                train_id,
                section_id,
                conflicting_train_id,
                reason
            )

            unique_conflicts.add(conflict_key)

        return len(unique_conflicts)

    # ---------------------------------------------------------
    # SECTION UTILIZATION
    # ---------------------------------------------------------

    def calculate_section_utilization(self):

        simulation_time = self.simulator.current_time_min

        if simulation_time <= 0:
            return {}

        section_occupied_time = {}

        active_entries = {}

        for event in self.simulator.history:

            event_type = event["event"]
            section_id = event["section_id"]
            event_time = event["time_min"]

            if section_id is None:
                continue

            # -------------------------------------------------
            # SECTION ENTERED
            # -------------------------------------------------

            if event_type == "SECTION_ENTERED":

                active_entries[section_id] = event_time

            # -------------------------------------------------
            # SECTION COMPLETED
            # -------------------------------------------------

            elif event_type == "SECTION_COMPLETED":

                if section_id in active_entries:

                    start_time = active_entries.pop(
                        section_id
                    )

                    occupied_time = (
                        event_time - start_time
                    )

                    section_occupied_time[
                        section_id
                    ] = (
                        section_occupied_time.get(
                            section_id,
                            0.0
                        )
                        + occupied_time
                    )

        # Sections that are still occupied at the end
        for section_id, start_time in active_entries.items():

            occupied_time = (
                simulation_time - start_time
            )

            section_occupied_time[
                section_id
            ] = (
                section_occupied_time.get(
                    section_id,
                    0.0
                )
                + occupied_time
            )

        # Convert to percentage
        utilization = {}

        for section_id, occupied_time in (
            section_occupied_time.items()
        ):

            utilization[section_id] = round(
                (
                    occupied_time
                    / simulation_time
                ) * 100,
                2
            )

        return utilization

    # ---------------------------------------------------------
    # ALL METRICS
    # ---------------------------------------------------------

    def calculate_all(self):

        return {
            "throughput_trains_per_hour": round(
                self.calculate_throughput(),
                2
            ),

            "completed_trains": (
                self.count_completed_trains()
            ),

            "initial_delay_min": (
                self.calculate_initial_delay()
            ),

            "total_waiting_time_min": (
                self.calculate_total_waiting_time()
            ),

            "average_waiting_time_min": (
                self.calculate_average_waiting_time()
            ),

            "conflicts": (
                self.count_conflicts()
            ),

            "section_utilization_percent": (
                self.calculate_section_utilization()
            ),
        }


# -------------------------------------------------------------
# TEST
# -------------------------------------------------------------

if __name__ == "__main__":

    from simulation.network import RailwayNetwork
    from input.input_state import TrainDatabase
    from input.scenario_loader import load_scenario
    from simulation.conflict_detector import ConflictDetector
    from controller.baseline_controller import BaselineController

    print("=== Metrics Engine Test ===")

    # ---------------------------------------------------------
    # LOAD SYSTEM
    # ---------------------------------------------------------

    network = RailwayNetwork()

    database = TrainDatabase()

    scenario, traffic = load_scenario(
        "example_scenario.json",
        database
    )

    simulator = RailwaySimulator(network)

    simulator.load_traffic(
        traffic,
        database
    )

    conflict_detector = ConflictDetector(
        simulator
    )

    controller = BaselineController(
        network=network,
        simulator=simulator,
        conflict_detector=conflict_detector,
        train_database=database,
    )

    # ---------------------------------------------------------
    # SIMULATION
    # ---------------------------------------------------------

    print("\nAdvancing to t = 2 minutes...")

    simulator.advance_time(2)

    print("\nRunning baseline controller...")

    decisions = controller.control_waiting_trains(
        execute=True
    )

    for decision in decisions:

        print(decision)

    print("\nAdvancing simulation by 100 minutes...")

    simulator.advance_time(100)

    # ---------------------------------------------------------
    # CALCULATE METRICS
    # ---------------------------------------------------------

    metrics = SimulationMetrics(
        simulator
    )

    results = metrics.calculate_all()

    # ---------------------------------------------------------
    # DISPLAY
    # ---------------------------------------------------------

    print("\n=== RESULTS ===")

    print(
        "Throughput:",
        results["throughput_trains_per_hour"],
        "trains/hour"
    )

    print(
        "Completed trains:",
        results["completed_trains"]
    )

    print(
        "Initial delay:",
        results["initial_delay_min"],
        "min"
    )

    print(
        "Total waiting:",
        results["total_waiting_time_min"],
        "min"
    )

    print(
        "Average waiting:",
        results["average_waiting_time_min"],
        "min"
    )

    print(
        "Conflicts:",
        results["conflicts"]
    )

    print("\nSection utilization:")

    for section_id, utilization in (
        results["section_utilization_percent"].items()
    ):

        print(
            section_id,
            ":",
            utilization,
            "%"
        )