import smtplib
from email.message import EmailMessage
from typing import Optional

from .config import SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS


def is_mailer_configured() -> bool:
    return all([SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS])


def send_subscription_confirmation(
    email: str,
    amount: Optional[float] = None,
    currency: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    session_id: Optional[str] = None,
) -> None:
    if not is_mailer_configured():
        print("⚠️ SMTP non configuré — aucun email envoyé.")
        return

    msg = EmailMessage()
    msg["Subject"] = "Confirmation de votre abonnement Flight Comparator"
    msg["From"] = SMTP_USER
    msg["To"] = email

    body_lines = [
        "Bonjour,",
        "",
        "Merci pour votre confiance ! Votre abonnement Flight Comparator vient d'être activé.",
        "",
    ]

    if amount and currency:
        body_lines.append(f"• Montant réglé : {amount:.2f} {currency.upper()}")
    if start_date:
        body_lines.append(f"• Date d'activation : {start_date}")
    if end_date:
        body_lines.append(f"• Prochaine échéance : {end_date} (renouvellement annuel)")

    body_lines.extend(
        [
            "",
            "Échéancier :",
            "  - Accès illimité aux recherches pendant 1 an",
            "  - Support prioritaire dédié",
            "  - Export CSV sans limite",
            "",
            "Vous pouvez revenir sur l’application pour reprendre vos recherches en toute liberté.",
        ]
    )
    if session_id:
        body_lines.append(f"ID de transaction Stripe: {session_id}")
    body_lines.append("")
    body_lines.append("Bon voyage !")

    msg.set_content("\n".join(body_lines))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)
        print(f"📬 Email de confirmation envoyé à {email}")
    except Exception as exc:
        print(f"⚠️ Erreur lors de l'envoi de l'email à {email}: {exc}")

