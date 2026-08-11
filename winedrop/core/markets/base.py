"""Interface som varje marknads-connector implementerar."""
from __future__ import annotations
import abc
import datetime as dt

from ..schema import Market, Wine


class MarketConnector(abc.ABC):
    """En connector hämtar nya vinsläpp för en marknad och normaliserar dem."""

    #: Marknadsmetadata (visas i appen)
    market: Market

    #: Marknadens huvudspråk för recensionssök, t.ex. "sv"
    review_lang: str = "en"

    @abc.abstractmethod
    def fetch_new_releases(self, days_back: int) -> list[Wine]:
        """Returnera nya vin i (motsvarande) tillfälligt/nytt sortiment.

        Ska ALDRIG kasta uppåt vid nätverksfel — returnera [] och logga.
        """
        raise NotImplementedError

    # --- hjälpare ---
    @staticmethod
    def _recent(launch_iso: str, days_back: int) -> bool:
        try:
            d = dt.date.fromisoformat(launch_iso[:10])
        except ValueError:
            return False
        return d >= dt.date.today() - dt.timedelta(days=days_back)
