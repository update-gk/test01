"""Run once: fetch prices, store them, email if a price gap exceeds the threshold.

Usage: python -m iphone_arbitrage.main [config.toml] [--dry-run]
"""
import sys
import tomllib

from . import db
from .compare import best_opportunity, should_notify
from .models import Item
from .notify import format_body, send_email
from .sources.apple import AppleSource
from .sources.morimori import MorimoriSource


def run(config_path: str, dry_run: bool = False) -> int:
    with open(config_path, "rb") as f:
        cfg = tomllib.load(f)
    items = [Item(**i) for i in cfg["items"]]
    conn = db.connect(cfg.get("db_path", "prices.db"))

    apple = AppleSource().fetch(items)
    shops = MorimoriSource().fetch(items)
    db.save_prices(conn, apple + shops)

    pending = []
    for a in apple:
        opp = best_opportunity(a, [s for s in shops if s.item == a.item])
        if opp is None:
            continue
        if should_notify(opp, cfg["threshold_yen"], db.last_alert_profit(conn, a.item),
                         cfg.get("require_stock", True)):
            pending.append(opp)
        elif opp.profit < cfg["threshold_yen"]:
            db.clear_alert(conn, a.item)  # dropped below threshold: allow a fresh alert later

    if pending:
        if dry_run:
            print(format_body(pending))
        else:
            send_email(pending)
        for o in pending:
            db.record_alert(conn, o.item, o.profit)
    return len(pending)


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    print(f"notified: {run(args[0] if args else 'config.toml', '--dry-run' in sys.argv)}")
