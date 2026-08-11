"""Register över alla marknads-connectors. Lägg till nya länder här."""
from __future__ import annotations

from .base import MarketConnector
from .sweden import SwedenConnector
from .norway import NorwayConnector
from .finland import FinlandConnector
from .canada import CanadaConnector

# Ordningen styr hur marknader listas i appen.
ALL_CONNECTORS: list[MarketConnector] = [
    SwedenConnector(),
    NorwayConnector(),
    FinlandConnector(),
    CanadaConnector(),
]


def get_connector(code: str) -> MarketConnector | None:
    for c in ALL_CONNECTORS:
        if c.market.code == code:
            return c
    return None
