from ..models import Item, PricePoint


class Source:
    """A price source. Implementations return one PricePoint per watched item found."""
    name: str

    def fetch(self, items: list[Item]) -> list[PricePoint]:
        raise NotImplementedError
