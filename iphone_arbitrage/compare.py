from dataclasses import dataclass

from .models import Item, PricePoint


@dataclass(frozen=True)
class Opportunity:
    item: Item
    apple_price: int
    shop: str
    buyback_price: int
    in_stock: bool

    @property
    def profit(self) -> int:
        return self.buyback_price - self.apple_price

    @property
    def margin(self) -> float:
        return self.profit / self.apple_price if self.apple_price else 0.0


def best_opportunity(apple: PricePoint, buybacks: list[PricePoint]) -> Opportunity | None:
    """Pick the shop that pays the most for this item."""
    if not buybacks:
        return None
    best = max(buybacks, key=lambda p: p.price)
    return Opportunity(apple.item, apple.price, best.source, best.price, apple.in_stock)


def should_notify(opp: Opportunity, threshold: int, last_alert_profit: int | None,
                  require_stock: bool = True, renotify_step: int = 2000) -> bool:
    """Notify when profit >= threshold; re-notify only if profit rose by renotify_step."""
    if opp.profit < threshold:
        return False
    if require_stock and not opp.in_stock:
        return False
    return last_alert_profit is None or opp.profit >= last_alert_profit + renotify_step
