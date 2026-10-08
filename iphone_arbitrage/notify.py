import os
import smtplib
from email.message import EmailMessage

from .compare import Opportunity


def format_body(opps: list[Opportunity]) -> str:
    lines = []
    for o in opps:
        stock = "在庫あり" if o.in_stock else "在庫なし/不明"
        lines.append(
            f"{o.item.model} {o.item.capacity} {o.item.color}\n"
            f"  Apple: ¥{o.apple_price:,} ({stock})\n"
            f"  買取({o.shop}): ¥{o.buyback_price:,}\n"
            f"  差額: ¥{o.profit:,} ({o.margin:.1%})"
        )
    return "\n\n".join(lines)


def send_email(opps: list[Opportunity]) -> None:
    """SMTP settings come from env vars (never commit them): SMTP_HOST, SMTP_PORT,
    SMTP_USER, SMTP_PASSWORD, MAIL_TO. Gmail users: use an app password."""
    msg = EmailMessage()
    msg["Subject"] = f"[iPhone差額] {len(opps)}件の利益チャンス"
    msg["From"] = os.environ["SMTP_USER"]
    msg["To"] = os.environ["MAIL_TO"]
    msg.set_content(format_body(opps))
    with smtplib.SMTP_SSL(os.environ["SMTP_HOST"], int(os.environ.get("SMTP_PORT", "465"))) as s:
        s.login(os.environ["SMTP_USER"], os.environ["SMTP_PASSWORD"])
        s.send_message(msg)
