import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# Find the project root directory
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"


VALID_STATUSES = {
    "WAITING",
    "APPROACHING",
    "RUNNING",
    "ARRIVED",
}

VALID_DIRECTIONS = {
    "UP",
    "DOWN",
}


@dataclass
class TrainState:
    train_id: str
    location: str
    direction: str
    status: str
    delay_min: float = 0.0
    entry_time_min: float = 0.0
    current_section: Optional[str] = None
    next_station: Optional[str] = None

    def validate(self):
        """Check whether the train's current state is valid."""

        if self.direction not in VALID_DIRECTIONS:
            raise ValueError(
                f"Invalid direction: {self.direction}"
            )

        if self.status not in VALID_STATUSES:
            raise ValueError(
                f"Invalid status: {self.status}"
            )

        if self.delay_min < 0:
            raise ValueError(
                "Delay cannot be negative."
            )
        if self.entry_time_min < 0:
            raise ValueError(
                "Entry time cannot be negative."
            )


@dataclass
class TrafficState:
    trains: list[TrainState] = field(default_factory=list)

    def add_train(self, train: TrainState):
        """Add a train to the current traffic situation."""

        if any(
            existing.train_id == train.train_id
            for existing in self.trains
        ):
            raise ValueError(
                f"Train {train.train_id} is already in the traffic state."
            )

        train.validate()
        self.trains.append(train)

    def remove_train(self, train_id: str):
        """Remove a train from the current traffic situation."""

        self.trains = [
            train
            for train in self.trains
            if train.train_id != train_id
        ]

    def get_train(self, train_id: str) -> Optional[TrainState]:
        """Find a train by its ID."""

        for train in self.trains:
            if train.train_id == train_id:
                return train

        return None

    def validate(self):
        """Validate every train in the traffic state."""

        train_ids = [train.train_id for train in self.trains]

        if len(train_ids) != len(set(train_ids)):
            raise ValueError(
                "Traffic state contains duplicate train IDs."
            )

        for train in self.trains:
            train.validate()


class TrainDatabase:
    """Loads and provides access to static train information."""

    def __init__(self):
        self.trains = {}
        self.load_trains()

    def load_trains(self):
        """Load train information from trains.csv."""

        filepath = DATA_DIR / "trains.csv"

        with open(filepath, "r", encoding="utf-8") as file:
            reader = csv.DictReader(file)

            for row in reader:
                self.trains[row["train_id"]] = row

    def get_train(self, train_id: str):
        """Return static information for a train."""

        if train_id not in self.trains:
            raise ValueError(
                f"Train {train_id} does not exist in trains.csv."
            )

        return self.trains[train_id]

    def count(self):
        """Return the number of trains in the database."""

        return len(self.trains)


def create_train_state(
    train_id,
    location,
    direction,
    status,
    delay_min=0.0,
    entry_time_min=0.0,
    current_section=None,
    next_station=None,
    database=None,
):
    """Create and validate a train's current state."""

    # Make sure the train exists in our database
    if database is not None:
        database.get_train(train_id)

    state = TrainState(
        train_id=train_id,
        location=location,
        direction=direction,
        status=status,
        delay_min=delay_min,
        entry_time_min=entry_time_min,
        current_section=current_section,
        next_station=next_station,
    )

    state.validate()

    return state


if __name__ == "__main__":

    print("=== Train Database Test ===")

    # Load the static train database
    database = TrainDatabase()

    print(f"Trains loaded: {database.count()}")

    # Look up T008
    train_info = database.get_train("T008")

    print(f"Train ID: {train_info['train_id']}")
    print(f"Train: {train_info['train_name']}")
    print(f"Type: {train_info['train_type']}")
    print(f"Priority: {train_info['priority']}")
    print(f"Route: {train_info['route_id']}")

    print("\n=== Dynamic State Test ===")

    # Create the current state of T008
    train_state = create_train_state(
        train_id="T008",
        location="PWL",
        direction="DOWN",
        status="APPROACHING",
        delay_min=4,
        current_section="S03",
        next_station="MTJ",
        database=database,
    )

    traffic = TrafficState()
    traffic.add_train(train_state)

    traffic.validate()

    print(f"Active trains: {len(traffic.trains)}")
    print(
        f"{train_state.train_id}: "
        f"{train_state.location} → {train_state.next_station} | "
        f"{train_state.status} | "
        f"delay={train_state.delay_min} min"
    )

    print("\nTraffic state: VALID")