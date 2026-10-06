import networkx as nx
from elevation import haversine_distance, get_elevation_batch


def build_grid(start_lat: float, start_lon: float, end_lat: float, end_lon: float, rows: int = 10, cols: int = 10) -> list:
    """
    Build a grid of lat/lon points covering the area between a start and end point.

    Args:
        start_lat, start_lon: Coordinates of the start point
        end_lat, end_lon: Coordinates of the end point
        rows: Number of grid rows
        cols: Number of grid columns
    """
    margin = 0.01  # extra padding around the straight line

    min_lat = min(start_lat, end_lat) - margin
    max_lat = max(start_lat, end_lat) + margin
    min_lon = min(start_lon, end_lon) - margin
    max_lon = max(start_lon, end_lon) + margin

    lat_step = (max_lat - min_lat) / (rows - 1)
    lon_step = (max_lon - min_lon) / (cols - 1)

    grid = []
    for r in range(rows):
        row = []
        for c in range(cols):
            lat = min_lat + r * lat_step
            lon = min_lon + c * lon_step
            row.append((lat, lon))
        grid.append(row)

    return grid


def build_graph(grid: list, elevations: dict = None, slope_penalty_factor: float = 10.0) -> nx.Graph:
    """
    Convert a grid of lat/lon points into a weighted graph.
    Each point connects to its neighbors (up, down, left, right, and
    both diagonals). Edge weight = real-world distance, plus an extra
    penalty if elevation data is provided and the segment is steep.
    This weight is only used to GUIDE the search (Dijkstra) — it is not
    a fair number to compare between different slope_penalty_factor runs,
    since it mixes distance and slope into one unit. Fair comparison
    metrics are computed separately in generate_multiple_candidates.

    Args:
        grid: 2D list of (lat, lon) points, as returned by build_grid
        elevations: Optional dict of {(row, col): elevation_meters}, as
                    returned by get_grid_elevations. If given, steep
                    segments get a higher cost.
        slope_penalty_factor: How much extra cost to add per meter of
                    elevation change. Higher = avoids slopes more.
    """
    G = nx.Graph()
    rows = len(grid)
    cols = len(grid[0])

    for r in range(rows):
        for c in range(cols):
            node = (r, c)
            lat, lon = grid[r][c]
            G.add_node(node, lat=lat, lon=lon)

    def edge_cost(node1, node2):
        r1, c1 = node1
        r2, c2 = node2
        lat1, lon1 = grid[r1][c1]
        lat2, lon2 = grid[r2][c2]
        dist = haversine_distance(lat1, lon1, lat2, lon2)

        if elevations is not None:
            elev1 = elevations[node1]
            elev2 = elevations[node2]
            elevation_diff = abs(elev2 - elev1)
            cost = dist + (elevation_diff * slope_penalty_factor)
        else:
            cost = dist

        return cost

    for r in range(rows):
        for c in range(cols):
            if c + 1 < cols:
                G.add_edge((r, c), (r, c + 1), weight=edge_cost((r, c), (r, c + 1)))
            if r + 1 < rows:
                G.add_edge((r, c), (r + 1, c), weight=edge_cost((r, c), (r + 1, c)))
            if r + 1 < rows and c + 1 < cols:
                G.add_edge((r, c), (r + 1, c + 1), weight=edge_cost((r, c), (r + 1, c + 1)))
            if r + 1 < rows and c - 1 >= 0:
                G.add_edge((r, c), (r + 1, c - 1), weight=edge_cost((r, c), (r + 1, c - 1)))

    return G


def get_grid_elevations(grid: list) -> dict:
    """
    Fetch elevation for every point in the grid, in a single batch request.

    Args:
        grid: 2D list of (lat, lon) points, as returned by build_grid
    """
    rows = len(grid)
    cols = len(grid[0])

    points = []
    node_order = []
    for r in range(rows):
        for c in range(cols):
            lat, lon = grid[r][c]
            points.append((lat, lon))
            node_order.append((r, c))

    elevations = get_elevation_batch(points)

    elevation_lookup = {}
    for node, elev_data in zip(node_order, elevations):
        elevation_lookup[node] = elev_data["elevation_meters"]

    return elevation_lookup


def find_shortest_path(graph: nx.Graph, grid: list, start_lat: float, start_lon: float, end_lat: float, end_lon: float) -> dict:
    """
    Find the shortest path through the grid graph from the point nearest
    the start location to the point nearest the end location.

    Args:
        graph: Weighted graph, as returned by build_graph
        grid: The grid of lat/lon points used to build the graph
        start_lat, start_lon: Coordinates of the start point
        end_lat, end_lon: Coordinates of the end point
    """
    rows = len(grid)
    cols = len(grid[0])

    def closest_node(target_lat, target_lon):
        best_node = None
        best_dist = None
        for r in range(rows):
            for c in range(cols):
                lat, lon = grid[r][c]
                dist = haversine_distance(target_lat, target_lon, lat, lon)
                if best_dist is None or dist < best_dist:
                    best_dist = dist
                    best_node = (r, c)
        return best_node

    start_node = closest_node(start_lat, start_lon)
    end_node = closest_node(end_lat, end_lon)

    path_nodes = nx.shortest_path(graph, source=start_node, target=end_node, weight="weight")
    search_cost = nx.shortest_path_length(graph, source=start_node, target=end_node, weight="weight")

    path_coords = [{"lat": grid[r][c][0], "lon": grid[r][c][1]} for (r, c) in path_nodes]

    return {
        "path": path_coords,
        "path_nodes": path_nodes,
        "search_cost": round(search_cost, 2),
        "num_points": len(path_coords),
    }


def generate_multiple_candidates(start_lat: float, start_lon: float, end_lat: float, end_lon: float, grid_size: int = 5) -> list:
    """
    Generate multiple candidate routes by trying different slope
    penalty factors, then keep only the distinct ones. For each
    candidate, also computes FAIR comparison metrics that do not
    depend on which slope_penalty_factor was used to search:
    pure_distance_meters (real path length) and max_slope_percent
    (steepest single segment along the path).

    Args:
        start_lat, start_lon: Coordinates of the start point
        end_lat, end_lon: Coordinates of the end point
        grid_size: Number of rows/columns in the search grid
    """
    grid = build_grid(start_lat, start_lon, end_lat, end_lon, rows=grid_size, cols=grid_size)
    elevations = get_grid_elevations(grid)

    penalty_factors_to_try = [0.0, 5.0, 15.0, 40.0]
    seen_paths = set()
    candidates = []

    for factor in penalty_factors_to_try:
        graph = build_graph(grid, elevations=elevations, slope_penalty_factor=factor)
        result = find_shortest_path(graph, grid, start_lat, start_lon, end_lat, end_lon)

        path_coords = result["path"]
        path_nodes = result["path_nodes"]

        path_signature = tuple((p["lat"], p["lon"]) for p in path_coords)
        if path_signature in seen_paths:
            continue
        seen_paths.add(path_signature)

        # Compute FAIR metrics on the resulting path, independent of
        # which slope_penalty_factor was used to find it.
        pure_distance_meters = 0.0
        max_slope_percent = 0.0
        total_elevation_gain_meters = 0.0

        for i in range(1, len(path_coords)):
            lat1, lon1 = path_coords[i - 1]["lat"], path_coords[i - 1]["lon"]
            lat2, lon2 = path_coords[i]["lat"], path_coords[i]["lon"]
            seg_dist = haversine_distance(lat1, lon1, lat2, lon2)
            pure_distance_meters += seg_dist

            elev1 = elevations[path_nodes[i - 1]]
            elev2 = elevations[path_nodes[i]]
            elev_diff = elev2 - elev1

            if elev_diff > 0:
                total_elevation_gain_meters += elev_diff

            if seg_dist > 0:
                slope_percent = abs(elev_diff) / seg_dist * 100
                if slope_percent > max_slope_percent:
                    max_slope_percent = slope_percent

        candidates.append({
            "slope_penalty_factor_used": factor,
            "path": path_coords,
            "search_cost": result["search_cost"],
            "pure_distance_meters": round(pure_distance_meters, 2),
            "max_slope_percent": round(max_slope_percent, 2),
            "total_elevation_gain_meters": round(total_elevation_gain_meters, 2),
            "num_points": result["num_points"],
        })

    return candidates


if __name__ == "__main__":
    start_lat, start_lon = 28.5706333, 77.3272147
    end_lat, end_lon = 28.4631285, 77.5080985

    candidates = generate_multiple_candidates(start_lat, start_lon, end_lat, end_lon, grid_size=10)
    print(f"Number of distinct candidates: {len(candidates)}")
    for i, cand in enumerate(candidates, 1):
        print(f"\nCandidate {i} (slope_penalty_factor={cand['slope_penalty_factor_used']}):")
        print(f"  Pure distance: {cand['pure_distance_meters']} m")
        print(f"  Max slope: {cand['max_slope_percent']}%")
        print(f"  Total elevation gain: {cand['total_elevation_gain_meters']} m")
        print(f"  Points: {cand['num_points']}")