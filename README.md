# iPhone 価格差チェッカー

Apple Store の iPhone 価格と、森森買取の買取価格の差額を監視し、閾値を超えたらメール通知する自分用ツール。

## 状態
- 実装済み: DB(SQLite)、差額計算、通知ルール、メール通知、テスト
- 未実装: `sources/apple.py` と `sources/morimori.py` の取得処理(実ページの構造確認が必要)

## 使い方
```
cp config.example.toml config.toml
python -m pytest
python -m iphone_arbitrage.main config.toml --dry-run
```
メール送信には環境変数 `SMTP_HOST` `SMTP_PORT` `SMTP_USER` `SMTP_PASSWORD` `MAIL_TO` を設定する。
