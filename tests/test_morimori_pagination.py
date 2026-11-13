import fetch_prices as fp

TABLE = """
<h1>iPhone（アイフォン）の 買取価格表</h1>
<table><tr><th>商品タイプ</th><th>商品名</th><th>JANコード</th><th>通常買取価格</th></tr>
<tr><td>新品</td><td><a href="/category/0301066/product/1">Apple
   iPhone17 Pro 256GB
   シルバー</a></td><td>4549995649284</td><td>192,000円</td></tr></table>
"""
NEXT = '<ul class="pagination"><li class="next"><a href="https://www.morimori-kaitori.jp/category/price-list/0301?page=2">次のページ</a></li></ul>'
URL = "https://www.morimori-kaitori.jp/category/price-list/0301"


def test_next_page_link_is_returned():
    page = fp.parse_price_list(TABLE + NEXT, URL)
    assert page["next"].endswith("/category/price-list/0301?page=2")
    assert fp.parse_price_list(TABLE, URL)["next"] is None


def test_name_is_cleaned():
    item = fp.parse_price_list(TABLE, URL)["items"]["4549995649284"]
    assert item["name"] == "iPhone17 Pro 256GB シルバー"
    assert item["buyback"] == 192000


def test_fetch_buyback_follows_all_pages(monkeypatch):
    pages = {
        URL: TABLE + NEXT,
        URL + "?page=2": TABLE.replace("4549995649284", "4549995649291"),
    }

    class R:
        def __init__(self, text):
            self.text = text

    monkeypatch.setattr(fp, "discover_model_ids", lambda: ["0301"])
    monkeypatch.setattr(fp, "get", lambda url, **kw: R(pages[url]))
    assert set(fp.fetch_buyback()) == {"4549995649284", "4549995649291"}
