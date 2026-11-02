from datetime import datetime, timezone
from math import asin, cos, radians, sin, sqrt
from zoneinfo import ZoneInfo

# IATA -> (city, IANA timezone)
AIRPORTS: dict[str, tuple[str, str]] = {
    "ATL": ("Atlanta", "America/New_York"),
    "BOS": ("Boston", "America/New_York"),
    "DFW": ("Dallas", "America/Chicago"),
    "DEN": ("Denver", "America/Denver"),
    "EWR": ("Newark", "America/New_York"),
    "IAD": ("Washington Dulles", "America/New_York"),
    "IAH": ("Houston", "America/Chicago"),
    "JFK": ("New York JFK", "America/New_York"),
    "LAX": ("Los Angeles", "America/Los_Angeles"),
    "MIA": ("Miami", "America/New_York"),
    "ORD": ("Chicago O'Hare", "America/Chicago"),
    "SEA": ("Seattle", "America/Los_Angeles"),
    "SFO": ("San Francisco", "America/Los_Angeles"),
    "YYZ": ("Toronto", "America/Toronto"),
    "YVR": ("Vancouver", "America/Vancouver"),
    "MEX": ("Mexico City", "America/Mexico_City"),
    "GRU": ("Sao Paulo", "America/Sao_Paulo"),
    "EZE": ("Buenos Aires", "America/Argentina/Buenos_Aires"),
    "LHR": ("London Heathrow", "Europe/London"),
    "LGW": ("London Gatwick", "Europe/London"),
    "CDG": ("Paris", "Europe/Paris"),
    "AMS": ("Amsterdam", "Europe/Amsterdam"),
    "FRA": ("Frankfurt", "Europe/Berlin"),
    "MUC": ("Munich", "Europe/Berlin"),
    "ZRH": ("Zurich", "Europe/Zurich"),
    "GVA": ("Geneva", "Europe/Zurich"),
    "VIE": ("Vienna", "Europe/Vienna"),
    "MAD": ("Madrid", "Europe/Madrid"),
    "BCN": ("Barcelona", "Europe/Madrid"),
    "FCO": ("Rome", "Europe/Rome"),
    "MXP": ("Milan", "Europe/Rome"),
    "LIS": ("Lisbon", "Europe/Lisbon"),
    "DUB": ("Dublin", "Europe/Dublin"),
    "CPH": ("Copenhagen", "Europe/Copenhagen"),
    "IST": ("Istanbul", "Europe/Istanbul"),
    "DOH": ("Doha", "Asia/Qatar"),
    "DXB": ("Dubai", "Asia/Dubai"),
    "AUH": ("Abu Dhabi", "Asia/Dubai"),
    "RUH": ("Riyadh", "Asia/Riyadh"),
    "DEL": ("Delhi", "Asia/Kolkata"),
    "BOM": ("Mumbai", "Asia/Kolkata"),
    "BLR": ("Bengaluru", "Asia/Kolkata"),
    "SIN": ("Singapore", "Asia/Singapore"),
    "HKG": ("Hong Kong", "Asia/Hong_Kong"),
    "BKK": ("Bangkok", "Asia/Bangkok"),
    "KUL": ("Kuala Lumpur", "Asia/Kuala_Lumpur"),
    "NRT": ("Tokyo Narita", "Asia/Tokyo"),
    "HND": ("Tokyo Haneda", "Asia/Tokyo"),
    "ICN": ("Seoul", "Asia/Seoul"),
    "PEK": ("Beijing", "Asia/Shanghai"),
    "PVG": ("Shanghai", "Asia/Shanghai"),
    "TPE": ("Taipei", "Asia/Taipei"),
    "SYD": ("Sydney", "Australia/Sydney"),
    "MEL": ("Melbourne", "Australia/Melbourne"),
    "AKL": ("Auckland", "Pacific/Auckland"),
    "JNB": ("Johannesburg", "Africa/Johannesburg"),
    "CPT": ("Cape Town", "Africa/Johannesburg"),
    "CAI": ("Cairo", "Africa/Cairo"),
    "NBO": ("Nairobi", "Africa/Nairobi"),
    "ADD": ("Addis Ababa", "Africa/Addis_Ababa"),
}


# IATA -> (latitude, longitude)
COORDINATES: dict[str, tuple[float, float]] = {
    "ATL": (33.64, -84.43), "BOS": (42.36, -71.01), "DFW": (32.90, -97.04), "DEN": (39.86, -104.67),
    "EWR": (40.69, -74.17), "IAD": (38.95, -77.46), "IAH": (29.99, -95.34), "JFK": (40.64, -73.78),
    "LAX": (33.94, -118.41), "MIA": (25.79, -80.29), "ORD": (41.97, -87.91), "SEA": (47.45, -122.31),
    "SFO": (37.62, -122.38), "YYZ": (43.68, -79.63), "YVR": (49.19, -123.18), "MEX": (19.44, -99.07),
    "GRU": (-23.43, -46.47), "EZE": (-34.82, -58.54), "LHR": (51.47, -0.45), "LGW": (51.15, -0.18),
    "CDG": (49.01, 2.55), "AMS": (52.31, 4.76), "FRA": (50.04, 8.56), "MUC": (48.35, 11.79),
    "ZRH": (47.46, 8.55), "GVA": (46.24, 6.11), "VIE": (48.11, 16.57), "MAD": (40.49, -3.57),
    "BCN": (41.30, 2.08), "FCO": (41.80, 12.25), "MXP": (45.63, 8.72), "LIS": (38.77, -9.13),
    "DUB": (53.42, -6.27), "CPH": (55.62, 12.66), "IST": (41.26, 28.74), "DOH": (25.27, 51.61),
    "DXB": (25.25, 55.36), "AUH": (24.43, 54.65), "RUH": (24.96, 46.70), "DEL": (28.56, 77.10),
    "BOM": (19.09, 72.87), "BLR": (13.20, 77.71), "SIN": (1.36, 103.99), "HKG": (22.31, 113.91),
    "BKK": (13.69, 100.75), "KUL": (2.75, 101.71), "NRT": (35.77, 140.39), "HND": (35.55, 139.78),
    "ICN": (37.46, 126.44), "PEK": (40.08, 116.58), "PVG": (31.14, 121.81), "TPE": (25.08, 121.23),
    "SYD": (-33.95, 151.18), "MEL": (-37.67, 144.84), "AKL": (-37.01, 174.79), "JNB": (-26.14, 28.24),
    "CPT": (-33.97, 18.60), "CAI": (30.12, 31.41), "NBO": (-1.32, 36.93), "ADD": (8.98, 38.80),
}


def distance_km(a: str, b: str) -> float | None:
    """Great-circle distance between two airports, or None if either is unknown."""
    pa, pb = COORDINATES.get(a.upper()), COORDINATES.get(b.upper())
    if not pa or not pb:
        return None
    lat1, lon1, lat2, lon2 = map(radians, (*pa, *pb))
    h = sin((lat2 - lat1) / 2) ** 2 + cos(lat1) * cos(lat2) * sin((lon2 - lon1) / 2) ** 2
    return 2 * 6371.0 * asin(sqrt(h))


def airport_tz(iata: str) -> ZoneInfo | None:
    entry = AIRPORTS.get(iata.upper())
    return ZoneInfo(entry[1]) if entry else None


def local_to_utc(iata: str, local: datetime) -> datetime:
    """Convert an airport-local wall-clock time to UTC.

    Unknown airports are treated as UTC, which is the best available guess.
    """
    if local.tzinfo is not None:
        return local.astimezone(timezone.utc)
    tz = airport_tz(iata) or timezone.utc
    return local.replace(tzinfo=tz).astimezone(timezone.utc)


def utc_to_local(iata: str, utc: datetime) -> datetime:
    tz = airport_tz(iata) or timezone.utc
    return utc.astimezone(tz).replace(tzinfo=None)
