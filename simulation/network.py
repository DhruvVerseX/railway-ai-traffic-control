import csv
from pathlib import Path
from dataclasses import dataclass


# Find the project root directory
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"


@dataclass
class Station:
    station_id: str
    station_name: str
    station_code: str
    station_type: str


@dataclass
class Section:
    section_id: str
    from_station: str
    to_station: str
    track_configuration: str
    distance_km: float
    normal_speed_kmph: float
    minimum_headway_min: float
    capacity_tracks: int

    def travel_time(self, train_speed_kmph: float) -> float:
        """Calculate running time through this section."""

        effective_speed = min(
            train_speed_kmph,
            self.normal_speed_kmph
        )

        if effective_speed <= 0:
            raise ValueError("Speed must be greater than zero.")

        return (
            self.distance_km / effective_speed
        ) * 60


@dataclass
class Route:
    route_id: str
    route_name: str
    origin: str
    destination: str
    station_sequence: list[str]
    section_sequence: list[str]
    route_type: str


class RailwayNetwork:
    """Loads and manages the railway network."""

    def __init__(self):
        self.stations = {}
        self.sections = {}
        self.routes = {}

        self.load_stations()
        self.load_sections()
        self.load_routes()

    def load_stations(self):
        """Load stations from stations.csv."""

        filepath = DATA_DIR / "stations.csv"

        with open(filepath, "r", encoding="utf-8") as file:
            reader = csv.DictReader(file)

            for row in reader:
                station = Station(
                    station_id=row["station_id"],
                    station_name=row["station_name"],
                    station_code=row["station_code"],
                    station_type=row["station_type"],
                )

                self.stations[station.station_code] = station

    def load_sections(self):
        """Load sections from sections.csv."""

        filepath = DATA_DIR / "sections.csv"

        with open(filepath, "r", encoding="utf-8") as file:
            reader = csv.DictReader(file)

            for row in reader:
                section = Section(
                    section_id=row["section_id"],
                    from_station=row["from_station"],
                    to_station=row["to_station"],
                    track_configuration=row["track_configuration"],
                    distance_km=float(row["distance_km"]),
                    normal_speed_kmph=float(
                        row["normal_speed_kmph"]
                    ),
                    minimum_headway_min=float(
                        row["minimum_headway_min"]
                    ),
                    capacity_tracks=int(
                        row["capacity_tracks"]
                    ),
                )

                self.sections[section.section_id] = section

    def load_routes(self):
        """Load routes from routes.csv."""

        filepath = DATA_DIR / "routes.csv"

        with open(filepath, "r", encoding="utf-8") as file:
            reader = csv.DictReader(file)

            for row in reader:
                route = Route(
                    route_id=row["route_id"],
                    route_name=row["route_name"],
                    origin=row["origin"],
                    destination=row["destination"],
                    station_sequence=row[
                        "station_sequence"
                    ].split(">"),
                    section_sequence=row[
                        "section_sequence"
                    ].split(">"),
                    route_type=row["route_type"],
                )

                self.routes[route.route_id] = route

    def get_station(self, station_code: str) -> Station:
        """Return a station by its code."""

        if station_code not in self.stations:
            raise ValueError(
                f"Unknown station: {station_code}"
            )

        return self.stations[station_code]

    def get_section(self, section_id: str) -> Section:
        """Return a section by its ID."""

        if section_id not in self.sections:
            raise ValueError(
                f"Unknown section: {section_id}"
            )

        return self.sections[section_id]

    def get_route(self, route_id: str) -> Route:
        """Return a route by its ID."""

        if route_id not in self.routes:
            raise ValueError(
                f"Unknown route: {route_id}"
            )

        return self.routes[route_id]

    def route_travel_time(
        self,
        route_id: str,
        train_speed_kmph: float
    ) -> float:
        """Calculate total running time for a train on a route."""

        route = self.get_route(route_id)

        total_time = 0.0

        for section_id in route.section_sequence:
            section = self.get_section(section_id)

            total_time += section.travel_time(
                train_speed_kmph
            )

        return total_time


if __name__ == "__main__":

    print("=== Railway Network Test ===")

    network = RailwayNetwork()

    print(f"Stations loaded: {len(network.stations)}")
    print(f"Sections loaded: {len(network.sections)}")
    print(f"Routes loaded: {len(network.routes)}")

    # Test route R04: Mathura → Kota
    route = network.get_route("R04")

    print("\n=== Route Test ===")
    print(f"Route: {route.route_name}")
    print(f"Origin: {route.origin}")
    print(f"Destination: {route.destination}")

    print("\nStations:")
    print(" → ".join(route.station_sequence))

    print("\nSections:")
    print(" → ".join(route.section_sequence))

    # Test travel time using a 130 km/h train
    travel_time = network.route_travel_time(
        route_id="R04",
        train_speed_kmph=130
    )

    print(
        f"\nRunning time at 130 km/h maximum speed: "
        f"{travel_time:.2f} minutes"
    )

    print("\nNetwork: VALID")