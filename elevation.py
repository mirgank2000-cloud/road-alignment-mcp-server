import requests
import math


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the distance in meters between two lat/lon points.
    """
    R = 6371000  # Earth's radius in meters

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


def get_elevation_batch(points: list) -> list:
    """
    Get elevation for multiple lat/lon points in a single request.
    Tries multiple free elevation providers in case one is slow/down.

    Args:
        points: List of (lat, lon) tuples
    """
    headers = {
        "User-Agent": "RoadAlignmentMCPTest/1.0",
        "Accept": "application/json",
    }

    locations_str = "|".join(f"{lat},{lon}" for lat, lon in points)
    last_error = None

    # Provider 1: Open-Elevation
    try:
        url = "https://api.open-elevation.com/api/v1/lookup"
        params = {"locations": locations_str}
        resp = requests.get(url, params=params, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        return [
            {"lat": r["latitude"], "lon": r["longitude"], "elevation_meters": r["elevation"]}
            for r in data["results"]
        ]
    except Exception as e:
        last_error = e

    # Provider 2: Open Topo Data (fallback)
    try:
        url = "https://api.opentopodata.org/v1/srtm90m"
        params = {"locations": locations_str}
        resp = requests.get(url, params=params, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        return [
            {"lat": r["location"]["lat"], "lon": r["location"]["lng"], "elevation_meters": r["elevation"]}
            for r in data["results"]
        ]
    except Exception as e:
        last_error = e

    raise Exception(f"All elevation providers failed. Last error: {last_error}")


def get_elevation(lat: float, lon: float) -> dict:
    """
    Get the elevation (height above sea level) for a single point.

    Args:
        lat: Latitude of the point
        lon: Longitude of the point
    """
    return get_elevation_batch([(lat, lon)])[0]


def get_elevation_profile(start_lat: float, start_lon: float, end_lat: float, end_lon: float, num_points: int = 10) -> list:
    """
    Get elevation samples along a straight line between a start and end point.

    Args:
        start_lat: Latitude of the start point
        start_lon: Longitude of the start point
        end_lat: Latitude of the end point
        end_lon: Longitude of the end point
        num_points: How many sample points to take along the line (default 10)
    """
    points = []
    for i in range(num_points):
        fraction = i / (num_points - 1)
        lat = start_lat + (end_lat - start_lat) * fraction
        lon = start_lon + (end_lon - start_lon) * fraction
        points.append((lat, lon))

    return get_elevation_batch(points)


def calculate_slope(profile: list) -> dict:
    """
    Calculate slope statistics from an elevation profile, including
    per-segment slope between each consecutive pair of points.

    Args:
        profile: List of elevation points (as returned by get_elevation_profile)
    """
    elevations = [p["elevation_meters"] for p in profile]

    max_elevation = max(elevations)
    min_elevation = min(elevations)
    total_gain = 0
    total_loss = 0
    segments = []

    for i in range(1, len(profile)):
        prev_point = profile[i - 1]
        curr_point = profile[i]

        elevation_diff = curr_point["elevation_meters"] - prev_point["elevation_meters"]
        distance_meters = haversine_distance(
            prev_point["lat"], prev_point["lon"],
            curr_point["lat"], curr_point["lon"]
        )

        if distance_meters > 0:
            slope_percent = (elevation_diff / distance_meters) * 100
        else:
            slope_percent = 0

        segments.append({
            "from": {"lat": prev_point["lat"], "lon": prev_point["lon"]},
            "to": {"lat": curr_point["lat"], "lon": curr_point["lon"]},
            "distance_meters": round(distance_meters, 2),
            "elevation_diff_meters": round(elevation_diff, 2),
            "slope_percent": round(slope_percent, 2),
        })

        if elevation_diff > 0:
            total_gain += elevation_diff
        else:
            total_loss += abs(elevation_diff)

    return {
        "max_elevation_meters": max_elevation,
        "min_elevation_meters": min_elevation,
        "total_elevation_gain_meters": round(total_gain, 2),
        "total_elevation_loss_meters": round(total_loss, 2),
        "segments": segments,
    }


if __name__ == "__main__":
    result = get_elevation_profile(28.5706333, 77.3272147, 28.4631285, 77.5080985)
    for point in result:
        print(point)

    print("\n---- Slope Stats ----")
    print(calculate_slope(result))