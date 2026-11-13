#!/usr/bin/env python3
"""
価格差ウォッチ: 森森買取（買取価格）× 楽天市場（販売価格）の差額を計算し、
しきい値を超えたらDiscordへ通知、docs/data.json にダッシュボード用データを書き出す。

使い方:
  python fetch_prices.py               通常実行（GitHub Actionsから呼ばれる）
  python fetch_prices.py --dry-run     通知せず、結果を表示するだけ
  python fetch_prices.py --test-discord  Discordにテスト通知だけ送る
"""
import argparse
import datetime as dt
import json
import os
import re
import sys
import time
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent
DOCS = ROOT / "docs"
CFG = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
JST = dt.timezone(dt.timedelta(hours=9))

MORI = "https://www.morimori-kaitori.jp"
UA = "price-gap-watch/0.1 (personal use)"
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": UA, "Accept-Language": "ja"})


def now_jst() -> dt.datetime:
    return dt.datetime.now(JST)


def norm(s: str) -> str:
    return re.sub(r"\s+", "", s or "").lower()


def to_int(text: str):
    m = re.search(r"([\d,]+)\s*円", text or "")
    if not m:
        m = re.search(r"([\d,]{4,})", text or "")
    return int(m.group(1).replace(",", "")) if m else None


# ---------------------------------------------------------------- 森森買取
def get(url: str, **kw) -> requests.Response:
    r = SESSION.get(url, timeout=30, **kw)
    r.raise_for_status()
    time.sleep(1.0)  # 相手サーバーに優しく
    return r


def model_wanted(name: str) -> bool:
    n = norm(name)
    return any(norm(k) in n for k in CFG["target_models"])


def category_wanted(name: str) -> bool:
    """discover_model_ids/fetch_buybackでこのカテゴリページを開くかどうかの緩い判定。
    実サイトでは複数機種が「iPhone（アイフォン）」のような1ページにまとまっているため、
    ここではiPhone関連かどうかだけ見る。個別機種の絞り込みはparse_price_list内の
    model_wanted（商品名ベース・厳密一致）に任せる。"""
    n = norm(name)
    return "iphone" in n or "アイフォン" in name or model_wanted(name)


def discover_model_ids() -> list:
    """カテゴリーページから対象機種のIDを集める。設定で固定もできる。"""
    if CFG.get("morimori_model_ids"):
        return list(CFG["morimori_model_ids"])
    html = get(f"{MORI}/category/0301").text
    soup = BeautifulSoup(html, "html.parser")
    found = {}
    for a in soup.find_all("a", href=True):
        href = (a.get("href") or "").strip()
        m = re.search(r"/category/(\d{2,})(?:/)?$", href)
        if not m:
            continue
        category_id = m.group(1)
        label = a.get_text(strip=True) or (a.find("img") or {}).get("alt", "")
        if not category_id or category_id == "03":
            continue
        found.setdefault(category_id, label)
    ids = [i for i, label in found.items() if not label or category_wanted(label)]
    print(f"[森森] 機種ページ {len(found)}件中 {len(ids)}件を対象にします")
    return ids


def expand_cells(row):
    """colspanを展開してセル文字列のリストにする（ヘッダーと本文の列位置を揃えるため）。"""
    out = []
    for c in row.find_all(["th", "td"]):
        span = int(c.get("colspan", 1) or 1)
        out.extend([c] * span)
    return out


def parse_price_list(html: str, page_url: str) -> dict:
    """価格表ページ → {JAN: {...}}（新品のみ・通常買取価格）"""
    soup = BeautifulSoup(html, "html.parser")
    title = (soup.find("h1").get_text(" ", strip=True) if soup.find("h1") else "")
    items = {}
    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        if not rows:
            continue
        header = [c.get_text(strip=True) for c in expand_cells(rows[0])]
        if not any("JAN" in h for h in header):
            continue
        idx = {}
        for i, h in enumerate(header):
            if "JAN" in h:
                idx["jan"] = i
            elif h == "商品名":
                idx["name"] = i
            elif h == "商品タイプ":
                idx["type"] = i
            elif h in ("通常買取価格", "買取価格") and "price" not in idx:
                idx["price"] = i
        if not {"jan", "name", "price"} <= idx.keys():
            continue
        for tr in rows[1:]:
            cells = expand_cells(tr)
            if len(cells) <= max(idx.values()):
                continue
            text = [c.get_text(" ", strip=True) for c in cells]
            name = text[idx["name"]]
            kind = text[idx["type"]] if "type" in idx else name
            if "新品" not in kind and "新品" not in name:
                continue  # 新品のみ扱う（中古は次のステップ）
            if not model_wanted(name):
                continue  # config.jsonのtarget_modelsに合致する商品名のみ扱う
            jan = re.sub(r"\D", "", text[idx["jan"]])
            price_text = text[idx["price"]]
            m = re.search(r"([\d,]+)円\(通常\)", price_text)
            price = int(m.group(1).replace(",", "")) if m else to_int(price_text)
            if not jan or not price or jan in items:
                continue
            link = cells[idx["name"]].find("a")
            items[jan] = {
                "jan": jan,
                "name": re.sub(r"^新品\s*", "", name),
                "buyback": price,
                "buyback_url": urljoin(page_url, link["href"]) if link and link.get("href") else page_url,
            }
    return {"title": title, "items": items}


def fetch_buyback() -> dict:
    all_items = {}
    for mid in discover_model_ids():
        url = f"{MORI}/category/price-list/{mid}"
        try:
            page = parse_price_list(get(url).text, url)
        except requests.RequestException as e:
            print(f"[森森] {mid} 取得失敗: {e}", file=sys.stderr)
            continue
        if page["title"] and not category_wanted(page["title"]):
            continue
        all_items.update(page["items"])
        print(f"[森森] {page['title'] or mid}: {len(page['items'])}件")
    return all_items


# ---------------------------------------------------------------- 楽天
class RakutenAuthError(RuntimeError):
    pass


def rakuten_search(jan: str) -> list:
    app_id = os.environ["RAKUTEN_APP_ID"]
    access_key = os.environ["RAKUTEN_ACCESS_KEY"]
    origin = os.environ["RAKUTEN_ORIGIN"].rstrip("/")  # 例: https://ユーザー名.github.io
    params = {
        "applicationId": app_id,
        "accessKey": access_key,
        "keyword": jan,
        "hits": 30,
        "sort": "+itemPrice",
        "availability": 1,
        "formatVersion": 2,
        "format": "json",
    }
    headers = {"Origin": origin, "Referer": origin + "/"}
    for attempt in range(3):
        r = SESSION.get(CFG["rakuten_endpoint"], params=params, headers=headers, timeout=30)
        if r.status_code == 429:
            time.sleep(3 * (attempt + 1))
            continue
        if r.status_code in (400, 401, 403):
            raise RakutenAuthError(f"HTTP {r.status_code}: {r.text[:200]}")
        r.raise_for_status()
        data = r.json()
        raw = data.get("Items") or data.get("items") or []
        # 2026年の楽天API刷新後、レスポンスのキー大文字/小文字（Items/Item vs items/item）が
        # 情報源によって食い違っていたため、両方に対応しておく。
        return [
            ((x.get("Item") or x.get("item") or x) if isinstance(x, dict) else {})
            for x in raw
        ]
    return []


def best_offer(buyback: int, hits: list):
    """NGワード・価格帯で絞り、実質コスト最小の1件を返す。"""
    best = None
    for h in hits:
        title = h.get("itemName", "")
        price = int(h.get("itemPrice") or 0)
        if not price or any(w in title for w in CFG["ng_words"]):
            continue
        if price < buyback * CFG["min_price_ratio"]:
            continue  # 安すぎるものはアクセサリや別商品の可能性
        cost = price
        separate = int(h.get("postageFlag", 0)) == 1  # 1 = 送料別
        if separate:
            cost += CFG["shipping_if_separate_yen"]
        points = int(price * float(h.get("pointRate", 1) or 1) / 100)
        if CFG["use_points"]:
            cost -= points
        cost += CFG["extra_cost_per_unit_yen"]
        if best is None or cost < best["cost"]:
            best = {
                "rakuten_price": price,
                "cost": cost,
                "points": points,
                "shipping_separate": separate,
                "shop": h.get("shopName", ""),
                "url": h.get("itemUrl", ""),
                "title": title,
            }
    return best


# ---------------------------------------------------------------- 通知
def send_discord(webhook: str, content: str, embeds: list):
    r = requests.post(webhook, json={"content": content, "embeds": embeds}, timeout=30)
    if r.status_code >= 300:
        print(f"[Discord] 送信失敗 {r.status_code}: {r.text[:200]}", file=sys.stderr)


def yen(n: int) -> str:
    return f"{n:,}円"


def notify(rows: list, stamp: str):
    webhook = os.environ.get("DISCORD_WEBHOOK_URL")
    if not webhook:
        print("[Discord] DISCORD_WEBHOOK_URL 未設定のため通知スキップ")
        return
    for i in range(0, len(rows), 10):  # 1メッセージに埋め込みは10個まで
        chunk = rows[i:i + 10]
        embeds = []
        for r in chunk:
            embeds.append({
                "title": r["name"][:250],
                "url": r["url"] or r["buyback_url"],
                "color": 0x0F7A5C,
                "description": (
                    f"**差額 +{yen(r['profit'])}**\n"
                    f"買取（森森・通常）: {yen(r['buyback'])}\n"
                    f"楽天: {yen(r['rakuten_price'])}"
                    f"{'（送料別）' if r['shipping_separate'] else ''} / {r['shop']}\n"
                    f"ポイント目安: {yen(r['points'])}"
                ),
                "footer": {"text": f"確認時刻 {stamp}（買取価格は変動・数量制限あり）"},
            })
        head = f"🔔 差額あり {len(rows)}件" if i == 0 else "（続き）"
        send_discord(webhook, head, embeds)


# ---------------------------------------------------------------- メイン
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--test-discord", action="store_true")
    args = ap.parse_args()

    if args.test_discord:
        send_discord(os.environ["DISCORD_WEBHOOK_URL"], "✅ 価格差ウォッチ: テスト通知です", [])
        print("テスト通知を送りました")
        return

    stamp = now_jst().strftime("%Y-%m-%d %H:%M")
    buyback = fetch_buyback()
    if not buyback:
        print("買取価格を1件も取得できませんでした（サイト構造の変更の可能性）", file=sys.stderr)
        sys.exit(1)

    jans = list(buyback)[: CFG["max_jans_per_run"]]
    results, errors = [], 0
    for n, jan in enumerate(jans, 1):
        b = buyback[jan]
        try:
            hits = rakuten_search(jan)
        except RakutenAuthError as e:
            print(f"楽天APIの認証エラー。ID・キー・Origin設定を確認してください: {e}", file=sys.stderr)
            sys.exit(1)
        except requests.RequestException as e:
            errors += 1
            print(f"[楽天] {jan} 失敗: {e}", file=sys.stderr)
            continue
        offer = best_offer(b["buyback"], hits)
        if offer:
            profit = b["buyback"] - CFG["buyback_shipping_yen"] - offer["cost"]
            results.append({
                **b,
                **{k: offer[k] for k in ("rakuten_price", "points", "shipping_separate", "shop", "url")},
                "profit": profit,
            })
        if n % 25 == 0:
            print(f"[楽天] {n}/{len(jans)} 件処理")
        time.sleep(CFG["request_interval_sec"])

    results.sort(key=lambda r: r["profit"], reverse=True)

    # 通知の重複抑止
    state_path = DOCS / "state.json"
    state = json.loads(state_path.read_text("utf-8")) if state_path.exists() else {}
    to_notify, new_state = [], {}
    for r in results:
        if r["profit"] < CFG["profit_threshold_yen"]:
            continue
        prev = state.get(r["jan"])
        fire = prev is None
        if prev:
            hours = (now_jst() - dt.datetime.fromisoformat(prev["at"])).total_seconds() / 3600
            fire = (r["profit"] - prev["profit"] >= CFG["renotify_step_yen"]
                    or hours >= CFG["renotify_after_hours"])
        if fire:
            to_notify.append(r)
            new_state[r["jan"]] = {"profit": r["profit"], "at": now_jst().isoformat()}
        else:
            new_state[r["jan"]] = prev  # しきい値割れで一度消え、再浮上したらまた通知される

    print(f"[結果] 比較 {len(results)}件 / しきい値超え {sum(r['profit'] >= CFG['profit_threshold_yen'] for r in results)}件 / 新規通知 {len(to_notify)}件 / 取得エラー {errors}件")

    if args.dry_run:
        for r in results[:15]:
            print(f"{r['profit']:>8,}円  {r['name']}  買取{r['buyback']:,} / 楽天{r['rakuten_price']:,} ({r['shop']})")
        return

    if to_notify:
        notify(to_notify, stamp)

    DOCS.mkdir(exist_ok=True)
    (DOCS / "data.json").write_text(json.dumps({
        "updated_at": now_jst().isoformat(),
        "threshold": CFG["profit_threshold_yen"],
        "use_points": CFG["use_points"],
        "compared": len(results),
        "errors": errors,
        "items": results[:300],
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    state_path.write_text(json.dumps(new_state, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
