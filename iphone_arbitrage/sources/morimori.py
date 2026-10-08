from ..models import Item, PricePoint
from . import Source


class MorimoriSource(Source):
    name = "morimori"

    def fetch(self, items: list[Item]) -> list[PricePoint]:
        # TODO: needs network access to www.morimori-kaitori.jp to inspect the real page.
        raise NotImplementedError("Morimori scraper not implemented yet")
