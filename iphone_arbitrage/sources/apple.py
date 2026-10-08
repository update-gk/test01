from ..models import Item, PricePoint
from . import Source


class AppleSource(Source):
    name = "apple"

    def fetch(self, items: list[Item]) -> list[PricePoint]:
        # TODO: needs network access to www.apple.com to inspect the real page/JSON.
        raise NotImplementedError("Apple scraper not implemented yet")
