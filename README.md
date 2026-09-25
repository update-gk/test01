# 価格差ウォッチ

楽天市場（販売価格）と森森買取（新品・通常買取価格）の差額を30分ごとに計算し、
しきい値を超えたらDiscordに通知、`docs/index.html` に一覧を表示します。

## セットアップ（初回のみ）

1. **GitHubで新しいリポジトリを作成**し、このフォルダの中身をすべてアップロード
   （`.github` フォルダも忘れずに）
2. **楽天ウェブサービス**でアプリを登録し、次の2つを控える
   - アプリケーションID
   - アクセスキー
   - 「許可されたWebサイト」には `ユーザー名.github.io` を登録
3. リポジトリの Settings → Secrets and variables → Actions に4つ登録
   | 名前 | 値 |
   |---|---|
   | `DISCORD_WEBHOOK_URL` | DiscordのWebhook URL |
   | `RAKUTEN_APP_ID` | 楽天のアプリケーションID |
   | `RAKUTEN_ACCESS_KEY` | 楽天のアクセスキー |
   | `RAKUTEN_ORIGIN` | `https://ユーザー名.github.io` |
4. Settings → Pages → Branch を `main` / `/docs` に設定
5. Actions タブ → check-prices → Run workflow で手動実行して動作確認

## 設定

`config.json` を編集します。

- `profit_threshold_yen` 通知する差額のしきい値
- `use_points` true にすると楽天ポイント分を差し引いて計算
- `target_models` 対象機種のキーワード
- `ng_words` 楽天の検索結果から除外する語（ケース、中古など）

## ローカルでの試運転

```
pip install -r requirements.txt
set RAKUTEN_APP_ID=...        (Windowsのコマンドプロンプト)
set RAKUTEN_ACCESS_KEY=...
set RAKUTEN_ORIGIN=https://ユーザー名.github.io
python fetch_prices.py --dry-run
```

Discordのテスト通知だけ送る場合は `python fetch_prices.py --test-discord`
（`DISCORD_WEBHOOK_URL` を設定しておく）。
