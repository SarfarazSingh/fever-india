"""Concierge shortlist for a confirmed trip. Curated five-star stays and restaurants."""

from app.schemas import DestinationGuide, GuidePlace

# Airport (and a few city codes) -> city and places.
_GUIDES: dict[str, tuple[str, list[tuple], list[tuple]]] = {
    "LHR": ("London", [
        ("The Peninsula London", "Belgravia", "Five-star, full spa, serious gym, walk to Hyde Park.", "https://www.peninsula.com/en/london"),
        ("Claridge's", "Mayfair", "Classic five-star, spa, and a quiet location for early flights to Heathrow.", "https://www.claridges.co.uk/"),
        ("The Ned", "City", "Pool and gym on site, central if the day is meetings.", "https://www.thened.com/london"),
    ], [
        ("The Clove Club", "Shoreditch", "Tasting menu, book ahead.", "https://thecloveclub.com/"),
        ("Core by Clare Smyth", "Notting Hill", "Three Michelin stars, calm room.", "https://www.corebyclaresmyth.com/"),
        ("Gymkhana", "Mayfair", "Indian, strong wine list, near the hotels.", "https://www.gymkhanalondon.com/"),
    ]),
    "CDG": ("Paris", [
        ("Cheval Blanc Paris", "1st", "Five-star, Dior spa, Seine views, compact gym.", "https://www.chevalblanc.com/en/maison/paris/"),
        ("The Peninsula Paris", "16th", "Rooftop, spa, large gym, quiet residential street.", "https://www.peninsula.com/en/paris"),
        ("Ritz Paris", "1st", "Chanel spa, pool, central for dining.", "https://www.ritzparis.com/"),
    ], [
        ("Le Cinq", "8th", "Hotel George V dining room.", "https://www.fourseasons.com/paris/dining/restaurants/le_cinq/"),
        ("Septime", "11th", "Seasonal, reserve early.", "https://www.septime-charonne.fr/"),
        ("Allard", "6th", "Classic bistro when you do not want a tasting menu.", "https://www.restaurant-allard.fr/"),
    ]),
    "DXB": ("Dubai", [
        ("One&Only One Za'abeel", "Za'abeel", "Spa, large gym, sky-level pool, central.", "https://www.oneandonlyresorts.com/one-zaabeel"),
        ("Bulgari Resort Dubai", "Jumeira Bay", "Private beach, spa, serious gym.", "https://www.bulgarihotels.com/en_US/dubai"),
        ("Four Seasons DIFC", "DIFC", "Best if the trip is meetings. Gym and spa in the tower.", "https://www.fourseasons.com/dubaidifc/"),
    ], [
        ("Trèsind Studio", "DIFC", "Indian tasting menu.", "https://tresind.com/"),
        ("Orfali Bros", "Wasl", "Small room, book the counter.", "https://www.orfalibros.com/"),
        ("Zuma DIFC", "DIFC", "Easy lunch between meetings.", "https://www.zumarestaurant.com/"),
    ]),
    "DOH": ("Doha", [
        ("Mandarin Oriental Doha", "Msheireb", "Spa, gym, walkable downtown.", "https://www.mandarinoriental.com/en/doha"),
        ("Four Seasons Doha", "The Pearl", "Beach, spa, full gym.", "https://www.fourseasons.com/doha/"),
        ("Banyan Tree Doha", "Mushaireb", "Spa-led hotel if recovery matters more than location.", "https://www.banyantree.com/qatar/doha"),
    ], [
        ("IDAM", "Museum of Islamic Art", "Alain Ducasse, book a window.", "https://www.mia.org.qa/en/idam"),
        ("Jamavar", "Marsà Malaz", "Indian, quieter than the hotel restaurants.", "https://www.jamavarrestaurants.com/"),
        ("Nobu Doha", "Four Seasons", "Reliable late arrival dinner.", "https://www.noburestaurants.com/doha"),
    ]),
    "SIN": ("Singapore", [
        ("Raffles Singapore", "Civic District", "Spa, pool, central, quiet courtyard.", "https://www.raffles.com/singapore/"),
        ("The Capitol Kempinski", "City Hall", "Strong gym, central MRT.", "https://www.kempinski.com/en/singapore"),
        ("Capella Singapore", "Sentosa", "Best spa on the island. Use it when the schedule is empty.", "https://www.capellahotels.com/en/capella-singapore"),
    ], [
        ("Odette", "National Gallery", "Three stars, lunch is easier to book.", "https://www.odetterestaurant.com/"),
        ("Burnt Ends", "Dempsey", "Small, meat-focused.", "https://burntends.com.sg/"),
        ("Candlenut", "Dempsey", "Peranakan, less formal.", "https://www.comodempsey.sg/candlenut"),
    ]),
    "NRT": ("Tokyo", [
        ("Aman Tokyo", "Otemachi", "Vast rooms, serious spa and gym, central.", "https://www.aman.com/hotels/aman-tokyo"),
        ("Four Seasons Otemachi", "Otemachi", "Pool, gym, best for a short trip.", "https://www.fourseasons.com/tokyo/"),
        ("Hoshinoya Tokyo", "Otemachi", "Ryokan in the city. Gym is limited; pick this for calm, not training.", "https://hoshinoya.com/tokyo/en/"),
    ], [
        ("Den", "Jingumae", "Creative, book weeks ahead.", "https://www.jimbochoden.com/"),
        ("Tempura Kondo", "Ginza", "Counter tempura.", "https://tempura-kondo.jp/"),
        ("Sushi Saito", "Minato", "Only if a table is already held.", "https://guide.michelin.com/us/en/tokyo-region/tokyo/restaurant/sushi-saito"),
    ]),
    "JFK": ("New York", [
        ("The Peninsula New York", "Midtown", "Rooftop spa, full gym, straightforward car to JFK.", "https://www.peninsula.com/en/new-york"),
        ("Aman New York", "Midtown", "Largest rooms, spa, quiet.", "https://www.aman.com/hotels/aman-new-york"),
        ("The Greenwich Hotel", "Tribeca", "Shibui spa, less convenient for early JFK departures.", "https://www.thegreenwichhotel.com/"),
    ], [
        ("Le Bernardin", "Midtown", "Seafood, business lunch.", "https://www.le-bernardin.com/"),
        ("Atomix", "NoMad", "Tasting menu.", "https://www.atomixnyc.com/"),
        ("Via Carota", "West Village", "No reservation. Go early.", "https://www.viacarota.com/"),
    ]),
    "HKG": ("Hong Kong", [
        ("The Upper House", "Admiralty", "Quiet, gym, spa, above Pacific Place.", "https://www.upperhouse.com/"),
        ("Rosewood Hong Kong", "Tsim Sha Tsui", "Harbour, large spa and gym.", "https://www.rosewoodhotels.com/en/hong-kong"),
        ("Mandarin Oriental Hong Kong", "Central", "Classic, central, proper gym.", "https://www.mandarinoriental.com/en/hong-kong"),
    ], [
        ("Amber", "The Landmark", "Two stars, Central.", "https://www.amberhongkong.com/"),
        ("The Chairman", "Central", "Cantonese, book ahead.", "https://www.thechairmangroup.com/"),
        ("Yardbird", "Sheung Wan", "Walk-in yakitori.", "https://yardbirdrestaurant.com/"),
    ]),
    "FRA": ("Frankfurt", [
        ("Roomers Frankfurt", "Station district", "Design hotel, gym, spa, short train to the airport.", "https://www.roomers-frankfurt.com/"),
        ("Jumeirah Frankfurt", "City", "Spa and gym, walkable.", "https://www.jumeirah.com/en/stay/germany/jumeirah-frankfurt"),
    ], [
        ("Lafleur", "Opera", "Fine dining.", "https://www.restaurant-lafleur.de/"),
        ("Heimat", "City", "Modern German.", "https://www.heimat-frankfurt.com/"),
    ]),
}


def guide_for(airport: str, *, wants_gym: bool = True, wants_spa: bool = True) -> DestinationGuide:
    code = airport.upper()
    city, hotels, restaurants = _GUIDES.get(code, _fallback(code))
    hotel_places = [
        GuidePlace(name=n, kind="hotel", area=a, why=_why(w, wants_gym, wants_spa), url=u) for n, a, w, u in hotels
    ]
    restaurant_places = [GuidePlace(name=n, kind="restaurant", area=a, why=w, url=u) for n, a, w, u in restaurants]
    return DestinationGuide(airport=code, city=city, hotels=hotel_places, restaurants=restaurant_places)


def _why(text: str, gym: bool, spa: bool) -> str:
    notes = []
    if gym and "gym" not in text.lower():
        notes.append("Confirm the gym before arrival.")
    if spa and "spa" not in text.lower() and "pool" not in text.lower():
        notes.append("Spa is limited here.")
    return text if not notes else f"{text} {' '.join(notes)}"


def _fallback(code: str) -> tuple[str, list, list]:
    q = f"https://www.google.com/travel/hotels?q=five+star+hotel+gym+spa+near+{code}+airport"
    return (
        code,
        [("Five-star near the airport", code, "Filter for a spa and a gym. This city is not in the curated list yet.", q)],
        [("Ask the hotel concierge", code, "Request two restaurants within ten minutes, one quiet.", q)],
    )
