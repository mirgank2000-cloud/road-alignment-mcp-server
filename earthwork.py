def estimate_earthwork_basic(profile: list) -> dict:
    """
    Give a rough (proxy) cut/fill estimate for a route, based on an
    elevation profile. Compares each point's elevation to the average
    elevation of the route (used as a simple target road level).

    Args:
        profile: List of elevation points (each with "elevation_meters"),
                 as returned by get_elevation_profile or a route path
                 with elevations attached.
    """
    elevations = [p["elevation_meters"] for p in profile]
    target_level = sum(elevations) / len(elevations)

    segments = []
    total_cut = 0.0
    total_fill = 0.0

    for point in profile:
        diff = point["elevation_meters"] - target_level

        if diff > 0:
            cut = diff
            fill = 0.0
            total_cut += cut
        else:
            cut = 0.0
            fill = abs(diff)
            total_fill += fill

        segments.append({
            "lat": point["lat"],
            "lon": point["lon"],
            "elevation_meters": point["elevation_meters"],
            "cut_meters": round(cut, 2),
            "fill_meters": round(fill, 2),
        })

    return {
        "target_road_level_meters": round(target_level, 2),
        "total_cut_meters": round(total_cut, 2),
        "total_fill_meters": round(total_fill, 2),
        "segments": segments,
        "note": "This is a rough, DEM-based proxy estimate, not survey-grade.",
    }


if __name__ == "__main__":
    test_profile = [
        {"lat": 28.57, "lon": 77.32, "elevation_meters": 210},
        {"lat": 28.56, "lon": 77.34, "elevation_meters": 195},
        {"lat": 28.55, "lon": 77.36, "elevation_meters": 200},
        {"lat": 28.54, "lon": 77.38, "elevation_meters": 190},
        {"lat": 28.53, "lon": 77.40, "elevation_meters": 205},
    ]
    result = estimate_earthwork_basic(test_profile)
    print(result)