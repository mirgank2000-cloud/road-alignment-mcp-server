def score_routes(candidates: list, distance_weight: float = 1.0, slope_weight: float = 1000.0, water_crossing_weight: float = 500.0) -> list:
    """
    Score and rank candidate routes using FAIR metrics that are
    comparable across all candidates (pure_distance_meters and
    max_slope_percent), plus the number of water crossings.

    Args:
        candidates: List of candidate route dicts, each with
                    "pure_distance_meters", "max_slope_percent", and
                    "num_water_crossings" keys.
        distance_weight: Multiplier applied to pure_distance_meters.
        slope_weight: Multiplier applied to max_slope_percent (slope is
                    a small number like 0-10, so this weight is large
                    to make it comparably meaningful against distance).
        water_crossing_weight: Penalty added per water crossing.
    """
    scored = []

    for cand in candidates:
        distance = cand.get("pure_distance_meters", 0)
        max_slope = cand.get("max_slope_percent", 0)
        num_crossings = cand.get("num_water_crossings", 0)

        score = (
            (distance * distance_weight)
            + (max_slope * slope_weight)
            + (num_crossings * water_crossing_weight)
        )

        scored_candidate = dict(cand)
        scored_candidate["score"] = round(score, 2)
        scored.append(scored_candidate)

    scored.sort(key=lambda c: c["score"])

    for rank, cand in enumerate(scored, start=1):
        cand["rank"] = rank

    return scored


if __name__ == "__main__":
    test_candidates = [
        {"slope_penalty_factor_used": 0.0, "pure_distance_meters": 24212.4, "max_slope_percent": 3.5, "num_water_crossings": 0},
        {"slope_penalty_factor_used": 15.0, "pure_distance_meters": 25000.0, "max_slope_percent": 0.8, "num_water_crossings": 0},
        {"slope_penalty_factor_used": 40.0, "pure_distance_meters": 26500.0, "max_slope_percent": 0.2, "num_water_crossings": 0},
    ]
    result = score_routes(test_candidates)
    for r in result:
        print(r)