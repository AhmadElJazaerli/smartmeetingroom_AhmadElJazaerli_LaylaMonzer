"""Simple profiling harness for the bookings service."""
import cProfile
import pstats
from pathlib import Path

import requests

BASE_URL = "http://localhost:8003"


def exercise_bookings():
    response = requests.get(f"{BASE_URL}/health", timeout=5)
    response.raise_for_status()


def main() -> None:
    profile_path = Path(__file__).with_name("bookings_profile.prof")
    with cProfile.Profile() as profiler:
        exercise_bookings()
    profiler.dump_stats(profile_path)
    stats = pstats.Stats(profile_path)
    stats.sort_stats(pstats.SortKey.TIME).print_stats(10)


if __name__ == "__main__":
    main()
