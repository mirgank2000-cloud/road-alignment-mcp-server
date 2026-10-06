import requests

def geocode_location(place_name: str) -> dict:
    """
    Convert a place name into latitude/longitude coordinates.

    Args:
        place_name: Name of the place to geocode (e.g. "Pari Chowk, Greater Noida")
    """
    url = "https://nominatim.openstreetmap.org/search"
    params = {"q": place_name, "format": "json", "limit": 1}
    headers = {
        "User-Agent": "RoadAlignmentMCPTest/1.0"
    }

    resp = requests.get(url, params=params, headers=headers, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    if not data:
        return {"error": f"No result found for '{place_name}'"}

    return {
        "place_name": place_name,
        "lat": float(data[0]["lat"]),
        "lon": float(data[0]["lon"]),
        "display_name": data[0]["display_name"],
    }

if __name__ == "__main__":
    print(geocode_location("Pari Chowk, Greater Noida"))
    print(geocode_location("Sector 96, Noida"))
    