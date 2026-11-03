"""Small, source-backed hotel catalogue. Unknown amenities never satisfy requirements."""

import json
from datetime import date
from pathlib import Path

from app.v1.schemas import Profile


def verified_hotels(airport: str, prefs: Profile) -> list[dict]:
    catalogue = json.loads(Path(__file__).with_name("hotels.json").read_text())
    result = []
    for hotel in catalogue:
        if (
            airport not in hotel["airports"]
            or (date.today() - date.fromisoformat(hotel["verified_at"])).days > 30
        ):
            continue
        if (
            hotel["hotel_stars"] < prefs.hotel_stars
            or (prefs.wants_gym and hotel.get("gym") is not True)
            or (prefs.wants_spa and hotel.get("spa") is not True)
        ):
            continue
        result.append(
            {k: v for k, v in hotel.items() if k != "airports"}
            | {
                "verification": "Official hotel sources checked "
                + hotel["verified_at"],
                "rating": None,
            }
        )
    return result[:3]
