import csv
from pathlib import Path


# Find the project root directory
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"


def load_csv(filename):
    """Load a CSV file and return its rows."""
    filepath = DATA_DIR / filename

    with open(filepath, "r", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def check_unique_ids(rows, id_column, filename):
    """Check that IDs are unique."""
    ids = [row[id_column] for row in rows]

    if len(ids) != len(set(ids)):
        print(f"❌ Duplicate {id_column} found in {filename}")
        return False

    print(f"✅ {filename}: IDs are unique")
    return True


def check_references():
    """Check that stations, sections, routes and trains reference valid data."""

    stations = load_csv("stations.csv")
    sections = load_csv("sections.csv")
    routes = load_csv("routes.csv")
    trains = load_csv("trains.csv")

    station_codes = {row["station_code"] for row in stations}
    section_ids = {row["section_id"] for row in sections}
    route_ids = {row["route_id"] for row in routes}

    valid = True

    # Check section station references
    for section in sections:
        if section["from_station"] not in station_codes:
            print(
                f"❌ Section {section['section_id']} references "
                f"unknown station {section['from_station']}"
            )
            valid = False

        if section["to_station"] not in station_codes:
            print(
                f"❌ Section {section['section_id']} references "
                f"unknown station {section['to_station']}"
            )
            valid = False

    # Check route references
    for route in routes:
        if route["origin"] not in station_codes:
            print(
                f"❌ Route {route['route_id']} has unknown origin "
                f"{route['origin']}"
            )
            valid = False

        if route["destination"] not in station_codes:
            print(
                f"❌ Route {route['route_id']} has unknown destination "
                f"{route['destination']}"
            )
            valid = False

        section_list = route["section_sequence"].split(">")

        for section_id in section_list:
            if section_id not in section_ids:
                print(
                    f"❌ Route {route['route_id']} references "
                    f"unknown section {section_id}"
                )
                valid = False

    # Check train route references
    for train in trains:
        if train["route_id"] not in route_ids:
            print(
                f"❌ Train {train['train_id']} references "
                f"unknown route {train['route_id']}"
            )
            valid = False

    return valid


def main():
    print("\n=== Railway Project Data Validation ===\n")

    stations = load_csv("stations.csv")
    sections = load_csv("sections.csv")
    junctions = load_csv("junctions.csv")
    routes = load_csv("routes.csv")
    trains = load_csv("trains.csv")

    print(f"Stations:   {len(stations)}")
    print(f"Sections:   {len(sections)}")
    print(f"Junctions:  {len(junctions)}")
    print(f"Routes:     {len(routes)}")
    print(f"Trains:     {len(trains)}")
    print()

    valid = True

    valid &= check_unique_ids(
        stations, "station_id", "stations.csv"
    )

    valid &= check_unique_ids(
        sections, "section_id", "sections.csv"
    )

    valid &= check_unique_ids(
        junctions, "junction_id", "junctions.csv"
    )

    valid &= check_unique_ids(
        routes, "route_id", "routes.csv"
    )

    valid &= check_unique_ids(
        trains, "train_id", "trains.csv"
    )

    print("\n--- Checking references ---")

    if not check_references():
        valid = False

    print()

    if valid:
        print("🎉 DATA VALIDATION PASSED")
        print("All current CSV files are internally consistent.")
    else:
        print("❌ DATA VALIDATION FAILED")
        print("Fix the errors above before continuing.")


if __name__ == "__main__":
    main()