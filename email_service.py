import smtplib
import os
import json
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger("agent.email")


def _render_html_from_json(items):
    # basic styled table for job opportunities
    header = """
    <html>
    <head>
      <meta charset="utf-8">
      <style>
        body { font-family: Arial, sans-serif; color: #111; }
        .card { border: 1px solid #e1e1e1; border-radius: 8px; padding: 12px; margin: 8px 0; }
        .title { font-size: 16px; font-weight: 600; color: #0b57d0; }
        .meta { color: #444; font-size: 13px; margin-top: 6px; }
        a.button { display: inline-block; margin-top:8px; padding:6px 10px; background:#0b57d0; color:#fff; text-decoration:none; border-radius:4px; }
      </style>
    </head>
    <body>
      <h2>New International Job Opportunities</h2>
    """

    items_html = ""
    for it in items:
        title = it.get("title", "No title")
        country = it.get("country", "")
        city = it.get("city_or_region", it.get("city", ""))
        field = it.get("field", "")
        language = it.get("language_level", "")
        visa = it.get("visa_info", "")
        link = it.get("official_link", "")
        salary = it.get("salary", "")

        items_html += f"""
        <div class="card">
          <div class="title">{title}</div>
          <div class="meta">{field} • {city} • {country}</div>
          <div class="meta">Language: {language} • Visa: {visa} • Salary: {salary}</div>
          {f'<a class="button" href="{link}">View official listing</a>' if link else ''}
        </div>
        """

    footer = """
    </body>
    </html>
    """

    return header + items_html + footer


def send_email(subject: str, body: str, to_email: str = None, recipient: str = None, smtp_config: dict | None = None) -> bool:
  """Send an email and return True on success, False on failure.

  Accepts either `to_email` or `recipient` for destination and an optional
  `smtp_config` dict with keys: server, port, sender, password.
  """
  dest = to_email or recipient
  if not dest:
    logger.error("No recipient provided to send_email")
    return False

  # Create message container (multipart/alternative)
  msg = MIMEMultipart("alternative")
  msg["Subject"] = subject

  # Determine SMTP configuration (prefer provided smtp_config)
  if smtp_config:
    smtp_server = smtp_config.get("server") or smtp_config.get("host") or os.getenv("SMTP_HOST")
    smtp_port = int(smtp_config.get("port", os.getenv("SMTP_PORT", 587)))
    smtp_sender = smtp_config.get("sender") or os.getenv("SMTP_EMAIL")
    smtp_password = smtp_config.get("password") or os.getenv("SMTP_PASSWORD")
  else:
    smtp_server = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_sender = os.getenv("SMTP_EMAIL")
    smtp_password = os.getenv("SMTP_PASSWORD")

  if not smtp_sender or not smtp_password or not smtp_server:
    logger.error("SMTP configuration incomplete: sender=%s server=%s", smtp_sender, smtp_server)
    return False

  msg["From"] = smtp_sender
  msg["To"] = dest

  # Plain text fallback
  plain_part = MIMEText(body, "plain", "utf-8")

  # Try to parse JSON body (expected from the app) and render HTML
  html_part = None
  try:
    parsed = json.loads(body)
    if isinstance(parsed, list):
      html = _render_html_from_json(parsed)
      html_part = MIMEText(html, "html", "utf-8")
    else:
      # Not a list: include pretty-printed JSON in HTML
      pretty = json.dumps(parsed, indent=2)
      html = f"<pre>{pretty}</pre>"
      html_part = MIMEText(html, "html", "utf-8")
  except Exception:
    # If body isn't JSON, wrap it in simple HTML
    safe = body.replace("\n", "<br />")
    html = f"<div>{safe}</div>"
    html_part = MIMEText(html, "html", "utf-8")

  msg.attach(plain_part)
  msg.attach(html_part)

  try:
    with smtplib.SMTP(smtp_server, smtp_port) as server:
      server.starttls()
      server.login(smtp_sender, smtp_password)
      server.send_message(msg)
    return True
  except Exception as e:
    logger.exception("Failed to send email: %s", str(e))
    return False
