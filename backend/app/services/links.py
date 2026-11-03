"""Airline websites for managing a reservation. The app never takes a card."""

from urllib.parse import urlencode

MANAGE_SITES: dict[str, str] = {
    "AA": "https://www.aa.com/reservation/view/find-your-reservation",
    "AF": "https://wwws.airfrance.us/trip",
    "BA": "https://www.britishairways.com/travel/managebooking/public/en_us",
    "DL": "https://www.delta.com/mytrips/findPnr",
    "EK": "https://www.emirates.com/us/english/manage-booking/",
    "IB": "https://www.iberia.com/us/manage-my-booking/",
    "KL": "https://www.klm.us/trip",
    "LH": "https://www.lufthansa.com/us/en/my-bookings",
    "QR": "https://www.qatarairways.com/en-us/manage-booking.html",
    "SQ": "https://www.singaporeair.com/en_UK/us/plan-travel/manage-booking/",
    "UA": "https://www.united.com/en/us/manageres/mytrips",
    "TK": "https://www.turkishairlines.com/en-us/flights/manage-booking/",
    "CX": "https://www.cathaypacific.com/cx/en_US/manage-booking/retrieve-booking.html",
}


def airline_manage_url(carrier: str, pnr: str) -> str:
    base = MANAGE_SITES.get(carrier.upper())
    query = urlencode({"pnr": pnr, "confirmation": pnr})
    if base:
        joiner = "&" if "?" in base else "?"
        return f"{base}{joiner}{query}"
    home = _home(carrier)
    if home:
        return home
    return f"https://www.iata.org/en/publications/directories/code-search/?airline.search={carrier.upper()}"


def _home(code: str) -> str | None:
    return _HOMEPAGES.get(code.upper())


# Official homepages, used only when a manage-booking page is unknown.
_HOMEPAGES = {
    "ZZ": "https://duffel.com",
    "B6": "https://www.jetblue.com/",
    "EI": "https://www.aerlingus.com/",
    "SK": "https://www.flysas.com/",
    "LO": "https://www.lot.com/us/en",
    "OK": "https://www.czechairlines.com/",
    "UX": "https://www.aireuropa.com/",
    "VY": "https://www.vueling.com/",
    "FR": "https://www.ryanair.com/",
    "U2": "https://www.easyjet.com/",
    "W6": "https://wizzair.com/",
    "LA": "https://www.latamairlines.com/",
    "AM": "https://aeromexico.com/",
    "CM": "https://www.copaair.com/",
    "AV": "https://www.avianca.com/",
    "SA": "https://www.flysaa.com/",
    "MS": "https://www.egyptair.com/",
    "RJ": "https://www.rj.com/",
    "GF": "https://www.gulfair.com/",
    "SV": "https://www.saudia.com/",
    "WY": "https://www.omanair.com/",
    "MH": "https://www.malaysiaairlines.com/",
    "TG": "https://www.thaiairways.com/",
    "CI": "https://www.china-airlines.com/",
    "BR": "https://www.evaair.com/",
    "CA": "https://www.airchina.com/",
    "MU": "https://www.ceair.com/",
    "CZ": "https://www.csair.com/",
    "HU": "https://www.hainanairlines.com/",
    "OZ": "https://flyasiana.com/",
    "VN": "https://www.vietnamairlines.com/",
    "GA": "https://www.garuda-indonesia.com/",
    "PR": "https://www.philippineairlines.com/",
    "UL": "https://www.srilankan.com/",
    "PK": "https://www.piac.com.pk/",
    "HY": "https://www.uzairways.com/",
    "SU": "https://www.aeroflot.com/",
    "A3": "https://en.aegeanair.com/",
    "OU": "https://www.croatiaairlines.com/",
    "BT": "https://www.airbaltic.com/",
    "DY": "https://www.norwegian.com/",
    "WF": "https://www.wideroe.no/",
    "PC": "https://www.flypgs.com/",
    "RO": "https://www.tarom.ro/",
    "FB": "https://www.air.bg/",
    "KM": "https://www.kmmaltairlines.com/",
    "TS": "https://www.airtransat.com/",
    "WS": "https://www.westjet.com/",
    "HA": "https://www.hawaiianairlines.com/",
    "WN": "https://www.southwest.com/",
    "NK": "https://www.spirit.com/",
    "F9": "https://www.flyfrontier.com/",
    "G3": "https://www.voegol.com.br/",
    "AD": "https://www.voeazul.com.br/",
    "H2": "https://www.skyairline.com/",
    "AR": "https://www.aerolineas.com.ar/",
    "JJ": "https://www.latamairlines.com/",
}
