from dataclasses import dataclass


@dataclass(frozen=True)
class Item:
    """Identifies one iPhone variant (e.g. model='iPhone 17 Pro', capacity='256GB')."""
    model: str
    capacity: str
    color: str = ""

    @property
    def key(self) -> str:
        return f"{self.model}|{self.capacity}|{self.color}"


@dataclass(frozen=True)
class PricePoint:
    source: str  # "apple" or a shop name such as "morimori"
    item: Item
    price: int  # JPY, tax included for Apple
    in_stock: bool = True
