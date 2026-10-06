import json
import csv
import io


def export_to_geojson(route_path: list, properties: dict = None) -> dict:
    """
    Convert a route path (list of lat/lon points) into a GeoJSON
    LineString feature, suitable for importing into QGIS or similar
    GIS software.

    Args:
        route_path: List of {"lat": ..., "lon": ...} points along the route
        properties: Optional extra metadata to attach (e.g. total_cost)
    """
    coordinates = [[point["lon"], point["lat"]] for point in route_path]

    geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": coordinates,
                },
                "properties": properties or {},
            }
        ],
    }

    return geojson


def export_to_csv(route_path: list) -> str:
    """
    Convert a route path (list of lat/lon points) into a CSV string,
    with one row per point.

    Args:
        route_path: List of {"lat": ..., "lon": ...} points along the route
    """
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["point_number", "lat", "lon"])

    for i, point in enumerate(route_path, start=1):
        writer.writerow([i, point["lat"], point["lon"]])

    return output.getvalue()


if __name__ == "__main__":
    test_path = [
        {"lat": 28.57, "lon": 77.32},
        {"lat": 28.56, "lon": 77.34},
        {"lat": 28.55, "lon": 77.36},
    ]

    geojson_result = export_to_geojson(test_path, properties={"total_cost": 12345.6})
    print("---- GeoJSON ----")
    print(json.dumps(geojson_result, indent=2))

    csv_result = export_to_csv(test_path)
    print("\n---- CSV ----")
    print(csv_result)