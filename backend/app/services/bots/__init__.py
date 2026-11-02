from app.services.bots.base import AirlineCheckInBot, BotResult, CheckInBotError
from app.services.bots.delta import DeltaCheckInBot

BOT_REGISTRY: dict[str, type[AirlineCheckInBot]] = {
    DeltaCheckInBot.airline_iata: DeltaCheckInBot,
}


def get_bot_for(airline_iata: str) -> type[AirlineCheckInBot] | None:
    return BOT_REGISTRY.get(airline_iata.upper())


__all__ = [
    "AirlineCheckInBot",
    "BOT_REGISTRY",
    "BotResult",
    "CheckInBotError",
    "DeltaCheckInBot",
    "get_bot_for",
]
