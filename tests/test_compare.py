from iphone_arbitrage import db
from iphone_arbitrage.compare import best_opportunity, should_notify
from iphone_arbitrage.models import Item, PricePoint
from iphone_arbitrage.notify import format_body

ITEM = Item("iPhone 17 Pro", "256GB", "silver")


def test_best_shop_and_profit():
    apple = PricePoint("apple", ITEM, 179800)
    opp = best_opportunity(apple, [PricePoint("a", ITEM, 170000), PricePoint("b", ITEM, 190000)])
    assert opp.shop == "b" and opp.profit == 10200
    assert best_opportunity(apple, []) is None


def test_should_notify_rules():
    apple = PricePoint("apple", ITEM, 100000, in_stock=True)
    opp = best_opportunity(apple, [PricePoint("a", ITEM, 112000)])
    assert should_notify(opp, 10000, None)
    assert not should_notify(opp, 15000, None)                 # below threshold
    assert not should_notify(opp, 10000, 11000)                # already alerted, small change
    assert should_notify(opp, 10000, 10000)                    # rose by >= step
    oos = best_opportunity(PricePoint("apple", ITEM, 100000, in_stock=False),
                           [PricePoint("a", ITEM, 112000)])
    assert not should_notify(oos, 10000, None)
    assert should_notify(oos, 10000, None, require_stock=False)


def test_db_roundtrip(tmp_path):
    conn = db.connect(str(tmp_path / "t.db"))
    db.save_prices(conn, [PricePoint("apple", ITEM, 100)])
    db.save_prices(conn, [PricePoint("apple", ITEM, 200)])
    assert db.latest_price(conn, "apple", ITEM).price == 200
    db.record_alert(conn, ITEM, 5000)
    assert db.last_alert_profit(conn, ITEM) == 5000
    db.clear_alert(conn, ITEM)
    assert db.last_alert_profit(conn, ITEM) is None


def test_format_body():
    opp = best_opportunity(PricePoint("apple", ITEM, 100000), [PricePoint("morimori", ITEM, 112000)])
    body = format_body([opp])
    assert "¥12,000" in body and "morimori" in body
