from elevation import haversine_distance


def check_constraints(route_path: list, river_points: list, crossing_threshold_meters: float = 100.0) -> dict:
    """
    Check a candidate route against river points to detect potential
    water crossings.

    Args:
        route_path: List of {"lat": ..., "lon": ...} points along the route
                    (as returned by generate_candidates)
        river_points: List of {"lat": ..., "lon": ..., "name": ...} river
                      locations (as returned by get_osm_features)
        crossing_threshold_meters: How close a route point must be to a
                    river point to count as a crossing (default 100m)
    """
    crossings = []

    for route_point in route_path:
        for river_point in river_points:
            dist = haversine_distance(
                route_point["lat"], route_point["lon"],
                river_point["lat"], river_point["lon"]
            )
            if dist <= crossing_threshold_meters:
                crossings.append({
                    "route_point": route_point,
                    "river_name": river_point["name"],
                    "distance_meters": round(dist, 2),
                })

    return {
        "num_water_crossings": len(crossings),
        "crossings": crossings,
    }


if __name__ == "__main__":
    test_route = [
        {"lat": 28.6041988, "lon": 77.3113464},
        {"lat": 28.61, "lon": 77.32},
    ]
    test_rivers = [
        {"lat": 28.6041988, "lon": 77.3113464, "name": "Hindon Yamuna Canal"},
    ]
    result = check_constraints(test_route, test_rivers)
    print(result)