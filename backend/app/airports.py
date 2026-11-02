from datetime import datetime, timezone
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
