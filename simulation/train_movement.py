from dataclasses import dataclass
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from simulation.network import RailwayNetwork
from input.input_state import TrainDatabase


@dataclass
class TrainMovement:
    train_id: str
    train_name: str
    route_id: str
    entry_station: str
    exit_station: str
    section_sequence: list[str]
    total_running_time_min: float


class TrainMovementModel:
    def __init__(self, network: RailwayNetwork, train_database: TrainDatabase):
        self.network = network
        self.train_database = train_database

    def build_movement(self, train_id: str) -> TrainMovement:
        # Get train information
        train = self.train_database.get_train(train_id)

        if train is None:
            raise ValueError(f"Unknown train ID: {train_id}")

        route = self.network.get_route(train["route_id"])

        if route is None:
            raise ValueError(
                f"Unknown route ID: {train['route_id']} "
                f"for train {train_id}"
            )

        entry = train["entry_station"]
        exit_station = train["exit_station"]

        stations = route.station_sequence
        sections = route.section_sequence

        # Both entry and exit must exist on the selected route
        if entry not in stations:
            raise ValueError(
                f"Entry station {entry} is not present on route {route.route_id}"
            )

        if exit_station not in stations:
            raise ValueError(
                f"Exit station {exit_station} is not present on route {route.route_id}"
            )

        entry_index = stations.index(entry)
        exit_index = stations.index(exit_station)

        # Train moves in the same direction as the route template
        if entry_index < exit_index:
            movement_sections = sections[entry_index:exit_index]
        
        # Train moves opposite to the route template
        elif entry_index > exit_index:
            movement_sections = list(
                reversed(sections[exit_index:entry_index])
            )
        
        else:
            raise ValueError(
                f"Entry and exit station are the same for train {train_id}"
            )

        # Calculate running time section by section
        section_times = []

        for section_id in movement_sections:
            section = self.network.get_section(section_id)

            if section is None:
                raise ValueError(
                    f"Unknown section ID: {section_id}"
                )

            travel_time = section.travel_time(
                float(train["max_speed_kmph"])
            )

            section_times.append(travel_time)

        total_running_time = sum(section_times)

        return TrainMovement(
            train_id=train_id,
            train_name=train["train_name"],
            route_id=train["route_id"],
            entry_station=entry,
            exit_station=exit_station,
            section_sequence=movement_sections,
            total_running_time_min=total_running_time,
        )


if __name__ == "__main__":
    # Load railway network
    network = RailwayNetwork()

    # Load train database
    train_database = TrainDatabase()

    # Create movement model
    movement_model = TrainMovementModel(
        network,
        train_database
    )

    # Test T008
    movement = movement_model.build_movement("T008")

    print("=== Train Movement Test ===")
    print(f"Train: {movement.train_id}")
    print(f"Name: {movement.train_name}")
    print(f"Route template: {movement.route_id}")
    print(f"Movement: {movement.entry_station} → {movement.exit_station}")
    print(
        "Sections:",
        " → ".join(movement.section_sequence)
    )
    print(
        f"Total running time: "
        f"{movement.total_running_time_min:.2f} minutes"
    )

    # Test reverse movement using T004
    reverse_movement = movement_model.build_movement("T004")

    print("\n=== Reverse Movement Test ===")
    print(f"Train: {reverse_movement.train_id}")
    print(f"Name: {reverse_movement.train_name}")
    print(
        f"Movement: "
        f"{reverse_movement.entry_station} → "
        f"{reverse_movement.exit_station}"
    )
    print(
        "Sections:",
        " → ".join(reverse_movement.section_sequence)
    )
    print(
        f"Total running time: "
        f"{reverse_movement.total_running_time_min:.2f} minutes"
    )