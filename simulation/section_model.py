from dataclasses import dataclass


@dataclass
class Section:
    section_id: str
    from_station: str
    to_station: str
    distance_km: float
    normal_speed_kmph: float
    minimum_headway_min: float
    capacity_tracks: int

    def travel_time(self, train_speed_kmph: float) -> float:
        """
        Calculate the minimum running time through this section.

        The effective speed is limited by both:
        1. the train's maximum speed
        2. the section's normal operating speed
        """

        effective_speed = min(
            train_speed_kmph,
            self.normal_speed_kmph
        )

        if effective_speed <= 0:
            raise ValueError("Speed must be greater than zero.")

        travel_time = (
            self.distance_km / effective_speed
        ) * 60

        return travel_time


if __name__ == "__main__":

    # Example: S04, Mathura → Bharatpur
    section = Section(
        section_id="S04",
        from_station="MTJ",
        to_station="BTE",
        distance_km=33,
        normal_speed_kmph=100,
        minimum_headway_min=5,
        capacity_tracks=2,
    )

    # Mewar Express has a maximum speed of 130 km/h
    train_speed = 130

    travel_time = section.travel_time(train_speed)

    print("=== Section Travel Time Test ===")
    print(
        f"{section.from_station} → {section.to_station}"
    )
    print(f"Distance: {section.distance_km} km")
    print(f"Train maximum speed: {train_speed} km/h")
    print(
        f"Effective speed: "
        f"{min(train_speed, section.normal_speed_kmph)} km/h"
    )
    print(f"Travel time: {travel_time:.2f} minutes")