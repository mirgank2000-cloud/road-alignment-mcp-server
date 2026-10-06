import requests


def get_osm_features(min_lat: float, min_lon: float, max_lat: float, max_lon: float) -> dict:
    """
    Fetch OSM features (roads and rivers) within a bounding box area.

    Args:
        min_lat: Minimum latitude of the bounding box
        min_lon: Minimum longitude of the bounding box
        max_lat: Maximum latitude of the bounding box
        max_lon: Maximum longitude of the bounding box
    """
    query = f"""
    [out:json][timeout:25];
    (
      way["highway"]({min_lat},{min_lon},{max_lat},{max_lon});
      way["waterway"]({min_lat},{min_lon},{max_lat},{max_lon});
    );
    out center tags;
    """

    urls = [
        "https://overpass-api.de/api/interpreter",
        "https://overpass.kumi.systems/api/interpreter",
        "https://overpass.private.coffee/api/interpreter",
    ]

    headers = {
        "User-Agent": "RoadAlignmentMCPTest/1.0",
        "Accept": "application/json",
    }

    data = None
    last_error = None

    for url in urls:
        try:
            resp = requests.post(url, data={"data": query}, headers=headers, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            break
        except Exception as e:
            last_error = e
            continue

    if data is None:
        raise Exception(f"All Overpass servers failed. Last error: {last_error}")

    roads = []
    rivers = []
    river_points = []

    for element in data.get("elements", []):
        tags = element.get("tags", {})
        name = tags.get("name", "Unnamed")

        if "highway" in tags:
            roads.append(name)
        elif "waterway" in tags:
            rivers.append(name)
            center = element.get("center")
            if center:
                river_points.append({"lat": center["lat"], "lon": center["lon"], "name": name})

    return {
        "bounding_box": {
            "min_lat": min_lat, "min_lon": min_lon,
            "max_lat": max_lat, "max_lon": max_lon,
        },
        "roads_found": roads,
        "rivers_found": rivers,
        "river_points": river_points,
    }


if __name__ == "__main__":
            print(get_osm_features(28.58, 77.30, 28.62, 77.32))