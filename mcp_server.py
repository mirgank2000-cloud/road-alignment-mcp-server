from mcp.server.fastmcp import FastMCP
from geocode import geocode_location
from osm_features import get_osm_features
from elevation import get_elevation_profile, calculate_slope
from route_search import build_grid, build_graph, get_grid_elevations, find_shortest_path, generate_multiple_candidates
from constraints import check_constraints
from earthwork import estimate_earthwork_basic
from scoring import score_routes
from export_results import export_to_geojson, export_to_csv

mcp = FastMCP("Road Alignment MCP Server")


@mcp.tool()
def geocode(place_name: str) -> dict:
    """
    Convert a place name into latitude/longitude coordinates.

    Args:
        place_name: Name of the place to geocode (e.g. "Pari Chowk, Greater Noida")
    """
    return geocode_location(place_name)


@mcp.tool()
def get_alignment_points(start_point: str, end_point: str) -> dict:
    """
    Convert a start point and end point into their latitude/longitude coordinates,
    for use in road alignment planning.

    Args:
        start_point: Name of the starting location (e.g. "Noida Sector 62")
        end_point: Name of the ending location (e.g. "Pari Chowk, Greater Noida")
    """
    start_result = geocode_location(start_point)
    end_result = geocode_location(end_point)

    return {
        "start_point": start_result,
        "end_point": end_result,
    }


@mcp.tool()
def get_route_area_features(start_point: str, end_point: str, margin: float = 0.02) -> dict:
    """
    Geocode a start and end point, build a bounding box around both
    (with a margin so nearby roads/rivers are included), and fetch
    OSM roads and rivers within that area.

    Args:
        start_point: Name of the starting location (e.g. "Noida Sector 62")
        end_point: Name of the ending location (e.g. "Pari Chowk, Greater Noida")
        margin: Extra padding (in degrees) added around the two points
                to widen the search area. Default 0.02 (~2 km).
    """
    start_result = geocode_location(start_point)
    end_result = geocode_location(end_point)

    if "error" in start_result:
        return {"error": f"Start point failed: {start_result['error']}"}
    if "error" in end_result:
        return {"error": f"End point failed: {end_result['error']}"}

    start_lat, start_lon = start_result["lat"], start_result["lon"]
    end_lat, end_lon = end_result["lat"], end_result["lon"]

    min_lat = min(start_lat, end_lat) - margin
    max_lat = max(start_lat, end_lat) + margin
    min_lon = min(start_lon, end_lon) - margin
    max_lon = max(start_lon, end_lon) + margin

    osm_data = get_osm_features(min_lat, min_lon, max_lat, max_lon)

    return {
        "start_point": start_result,
        "end_point": end_result,
        "search_area": osm_data["bounding_box"],
        "roads_found": osm_data["roads_found"],
        "rivers_found": osm_data["rivers_found"],
    }


@mcp.tool()
def get_route_elevation_profile(start_point: str, end_point: str, num_points: int = 10) -> dict:
    """
    Geocode a start and end point, then get the elevation profile and
    slope statistics (including per-segment slope) along the straight
    line between them.

    Args:
        start_point: Name of the starting location (e.g. "Noida Sector 62")
        end_point: Name of the ending location (e.g. "Pari Chowk, Greater Noida")
        num_points: How many sample points to take along the line (default 10)
    """
    start_result = geocode_location(start_point)
    end_result = geocode_location(end_point)

    if "error" in start_result:
        return {"error": f"Start point failed: {start_result['error']}"}
    if "error" in end_result:
        return {"error": f"End point failed: {end_result['error']}"}

    profile = get_elevation_profile(
        start_result["lat"], start_result["lon"],
        end_result["lat"], end_result["lon"],
        num_points
    )
    slope_stats = calculate_slope(profile)

    return {
        "start_point": start_result,
        "end_point": end_result,
        "elevation_profile": profile,
        "slope_stats": slope_stats,
    }


@mcp.tool()
def generate_candidates(start_point: str, end_point: str, grid_size: int = 10) -> dict:
    """
    Geocode a start and end point, then generate multiple distinct
    candidate routes between them using different slope-penalty
    weightings, so the user can compare route options. Each candidate
    includes fair, comparable metrics: pure_distance_meters and
    max_slope_percent.

    Args:
        start_point: Name of the starting location (e.g. "Noida Sector 62")
        end_point: Name of the ending location (e.g. "Pari Chowk, Greater Noida")
        grid_size: Number of rows/columns in the search grid (default 10)
    """
    start_result = geocode_location(start_point)
    end_result = geocode_location(end_point)

    if "error" in start_result:
        return {"error": f"Start point failed: {start_result['error']}"}
    if "error" in end_result:
        return {"error": f"End point failed: {end_result['error']}"}

    candidates = generate_multiple_candidates(
        start_result["lat"], start_result["lon"],
        end_result["lat"], end_result["lon"],
        grid_size=grid_size
    )

    return {
        "start_point": start_result,
        "end_point": end_result,
        "num_candidates": len(candidates),
        "candidates": candidates,
    }


@mcp.tool()
def check_route_constraints(start_point: str, end_point: str, grid_size: int = 10, crossing_threshold_meters: float = 100.0) -> dict:
    """
    Generate candidate routes between a start and end point, then check
    each against rivers/waterways in the area to flag potential water
    crossings.

    Args:
        start_point: Name of the starting location (e.g. "Noida Sector 62")
        end_point: Name of the ending location (e.g. "Pari Chowk, Greater Noida")
        grid_size: Number of rows/columns in the search grid (default 10)
        crossing_threshold_meters: How close a route point must be to a
                river to count as a crossing (default 100m)
    """
    start_result = geocode_location(start_point)
    end_result = geocode_location(end_point)

    if "error" in start_result:
        return {"error": f"Start point failed: {start_result['error']}"}
    if "error" in end_result:
        return {"error": f"End point failed: {end_result['error']}"}

    start_lat, start_lon = start_result["lat"], start_result["lon"]
    end_lat, end_lon = end_result["lat"], end_result["lon"]

    candidates = generate_multiple_candidates(start_lat, start_lon, end_lat, end_lon, grid_size=grid_size)

    margin = 0.02
    min_lat = min(start_lat, end_lat) - margin
    max_lat = max(start_lat, end_lat) + margin
    min_lon = min(start_lon, end_lon) - margin
    max_lon = max(start_lon, end_lon) + margin
    osm_data = get_osm_features(min_lat, min_lon, max_lat, max_lon)
    river_points = osm_data["river_points"]

    results = []
    for cand in candidates:
        constraint_check = check_constraints(cand["path"], river_points, crossing_threshold_meters)
        results.append({
            "slope_penalty_factor_used": cand["slope_penalty_factor_used"],
            "path": cand["path"],
            "pure_distance_meters": cand["pure_distance_meters"],
            "max_slope_percent": cand["max_slope_percent"],
            "total_elevation_gain_meters": cand["total_elevation_gain_meters"],
            "num_water_crossings": constraint_check["num_water_crossings"],
            "crossings": constraint_check["crossings"],
        })

    return {
        "start_point": start_result,
        "end_point": end_result,
        "candidates_checked": results,
    }


@mcp.tool()
def estimate_route_earthwork(start_point: str, end_point: str, num_points: int = 10) -> dict:
    """
    Geocode a start and end point, get the elevation profile along the
    straight line between them, and give a rough cut/fill earthwork
    estimate (proxy only, not survey-grade).

    Args:
        start_point: Name of the starting location (e.g. "Noida Sector 62")
        end_point: Name of the ending location (e.g. "Pari Chowk, Greater Noida")
        num_points: How many sample points to take along the line (default 10)
    """
    start_result = geocode_location(start_point)
    end_result = geocode_location(end_point)

    if "error" in start_result:
        return {"error": f"Start point failed: {start_result['error']}"}
    if "error" in end_result:
        return {"error": f"End point failed: {end_result['error']}"}

    profile = get_elevation_profile(
        start_result["lat"], start_result["lon"],
        end_result["lat"], end_result["lon"],
        num_points
    )

    earthwork = estimate_earthwork_basic(profile)

    return {
        "start_point": start_result,
        "end_point": end_result,
        "earthwork_estimate": earthwork,
    }


@mcp.tool()
def compare_routes(start_point: str, end_point: str, grid_size: int = 10, crossing_threshold_meters: float = 100.0) -> dict:
    """
    Generate multiple candidate routes, check each for water crossings,
    then score and rank them using fair metrics (pure_distance_meters,
    max_slope_percent, num_water_crossings) so the best option is easy
    to identify.

    Args:
        start_point: Name of the starting location (e.g. "Noida Sector 62")
        end_point: Name of the ending location (e.g. "Pari Chowk, Greater Noida")
        grid_size: Number of rows/columns in the search grid (default 10)
        crossing_threshold_meters: How close a route point must be to a
                river to count as a crossing (default 100m)
    """
    start_result = geocode_location(start_point)
    end_result = geocode_location(end_point)

    if "error" in start_result:
        return {"error": f"Start point failed: {start_result['error']}"}
    if "error" in end_result:
        return {"error": f"End point failed: {end_result['error']}"}

    start_lat, start_lon = start_result["lat"], start_result["lon"]
    end_lat, end_lon = end_result["lat"], end_result["lon"]

    candidates = generate_multiple_candidates(start_lat, start_lon, end_lat, end_lon, grid_size=grid_size)

    margin = 0.02
    min_lat = min(start_lat, end_lat) - margin
    max_lat = max(start_lat, end_lat) + margin
    min_lon = min(start_lon, end_lon) - margin
    max_lon = max(start_lon, end_lon) + margin
    osm_data = get_osm_features(min_lat, min_lon, max_lat, max_lon)
    river_points = osm_data["river_points"]

    checked_candidates = []
    for cand in candidates:
        constraint_check = check_constraints(cand["path"], river_points, crossing_threshold_meters)
        checked_candidates.append({
            "slope_penalty_factor_used": cand["slope_penalty_factor_used"],
            "path": cand["path"],
            "pure_distance_meters": cand["pure_distance_meters"],
            "max_slope_percent": cand["max_slope_percent"],
            "total_elevation_gain_meters": cand["total_elevation_gain_meters"],
            "num_water_crossings": constraint_check["num_water_crossings"],
        })

    ranked = score_routes(checked_candidates)

    return {
        "start_point": start_result,
        "end_point": end_result,
        "ranked_candidates": ranked,
    }


@mcp.tool()
def export_route_results(start_point: str, end_point: str, grid_size: int = 10, crossing_threshold_meters: float = 100.0) -> dict:
    """
    Generate candidate routes, rank them fairly, and export the best
    (rank 1) route as both GeoJSON and CSV, ready for GIS software or
    sharing.

    Args:
        start_point: Name of the starting location (e.g. "Noida Sector 62")
        end_point: Name of the ending location (e.g. "Pari Chowk, Greater Noida")
        grid_size: Number of rows/columns in the search grid (default 10)
        crossing_threshold_meters: How close a route point must be to a
                river to count as a crossing (default 100m)
    """
    start_result = geocode_location(start_point)
    end_result = geocode_location(end_point)

    if "error" in start_result:
        return {"error": f"Start point failed: {start_result['error']}"}
    if "error" in end_result:
        return {"error": f"End point failed: {end_result['error']}"}

    start_lat, start_lon = start_result["lat"], start_result["lon"]
    end_lat, end_lon = end_result["lat"], end_result["lon"]

    candidates = generate_multiple_candidates(start_lat, start_lon, end_lat, end_lon, grid_size=grid_size)

    margin = 0.02
    min_lat = min(start_lat, end_lat) - margin
    max_lat = max(start_lat, end_lat) + margin
    min_lon = min(start_lon, end_lon) - margin
    max_lon = max(start_lon, end_lon) + margin
    osm_data = get_osm_features(min_lat, min_lon, max_lat, max_lon)
    river_points = osm_data["river_points"]

    checked_candidates = []
    for cand in candidates:
        constraint_check = check_constraints(cand["path"], river_points, crossing_threshold_meters)
        checked_candidates.append({
            "slope_penalty_factor_used": cand["slope_penalty_factor_used"],
            "path": cand["path"],
            "pure_distance_meters": cand["pure_distance_meters"],
            "max_slope_percent": cand["max_slope_percent"],
            "total_elevation_gain_meters": cand["total_elevation_gain_meters"],
            "num_water_crossings": constraint_check["num_water_crossings"],
        })

    ranked = score_routes(checked_candidates)
    best_route = ranked[0]

    geojson = export_to_geojson(
        best_route["path"],
        properties={
            "pure_distance_meters": best_route["pure_distance_meters"],
            "max_slope_percent": best_route["max_slope_percent"],
            "num_water_crossings": best_route["num_water_crossings"],
            "score": best_route["score"],
        }
    )
    csv_data = export_to_csv(best_route["path"])

    return {
        "start_point": start_result,
        "end_point": end_result,
        "best_route_summary": {
            "pure_distance_meters": best_route["pure_distance_meters"],
            "max_slope_percent": best_route["max_slope_percent"],
            "num_water_crossings": best_route["num_water_crossings"],
            "score": best_route["score"],
        },
        "geojson": geojson,
        "csv": csv_data,
    }


if __name__ == "__main__":
    mcp.run()