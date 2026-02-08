import smtplib
import os
import json
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger("agent.email")


def format_opportunities_readable(items):
    """Format job opportunities into a readable point-form text format."""
    if not items:
        return "No new opportunities found."
    
    text = f"Found {len(items)} new job opportunity{'ies' if len(items) > 1 else 'y'}:\n\n"
    
    for idx, it in enumerate(items, start=1):
        title = it.get("title", "No title")
        country = it.get("country", "Not specified")
        city = it.get("city_or_region") or it.get("city", "Not specified")
        field = it.get("field", "Not specified")
        language = it.get("language_level", "Not specified")
        visa = it.get("visa_info", "Not specified")
        link = it.get("official_link", "")
        salary = it.get("salary", "Not specified")
        
        text += f"Job {idx}: {title}\n"
        text += f"  • Country: {country}\n"
        text += f"  • City/Region: {city}\n"
        text += f"  • Field: {field}\n"
        text += f"  • Language Level: {language}\n"
        text += f"  • Visa Information: {visa}\n"
        text += f"  • Salary: {salary}\n"
        if link:
            text += f"  • Official Link: {link}\n"
        text += "\n"
    
    return text


def _render_html_from_json(items):
    """Render job opportunities as HTML in a readable format."""
    header = """
    <html>
    <head>
      <meta charset="utf-8">
      <style>
        body { font-family: Arial, sans-serif; color: #111; line-height: 1.6; }
        .job { border: 1px solid #e1e1e1; border-radius: 8px; padding: 16px; margin: 12px 0; background: #f9f9f9; }
        .job-title { font-size: 18px; font-weight: 600; color: #0b57d0; margin-bottom: 10px; }
        .job-detail { margin: 6px 0; color: #444; font-size: 14px; }
        .job-detail strong { color: #222; }
        a.button { display: inline-block; margin-top: 10px; padding: 8px 14px; background: #0b57d0; color: #fff; text-decoration: none; border-radius: 4px; font-size: 14px; }
        a.button:hover { background: #084298; }
      </style>
    </head>
    <body>
      <h2>New International Job Opportunities</h2>
    """

    items_html = ""
    for idx, it in enumerate(items, start=1):
        title = it.get("title", "No title")
        country = it.get("country", "Not specified")
        city = it.get("city_or_region") or it.get("city", "Not specified")
        field = it.get("field", "Not specified")
        language = it.get("language_level", "Not specified")
        visa = it.get("visa_info", "Not specified")
        link = it.get("official_link", "")
        salary = it.get("salary", "Not specified")

        items_html += f"""
        <div class="job">
          <div class="job-title">Job {idx}: {title}</div>
          <div class="job-detail"><strong>Country:</strong> {country}</div>
          <div class="job-detail"><strong>City/Region:</strong> {city}</div>
          <div class="job-detail"><strong>Field:</strong> {field}</div>
          <div class="job-detail"><strong>Language Level:</strong> {language}</div>
          <div class="job-detail"><strong>Visa Information:</strong> {visa}</div>
          <div class="job-detail"><strong>Salary:</strong> {salary}</div>
          {f'<a class="button" href="{link}">View Official Listing</a>' if link else ''}
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

  # Check if body is already readable text or JSON
  readable_body = body
  html_part = None
  try:
    # Try to parse as JSON first (for backward compatibility)
    parsed = json.loads(body)
    if isinstance(parsed, list):
      # Convert JSON list to readable point-form text
      readable_body = format_opportunities_readable(parsed)
      html = _render_html_from_json(parsed)
      html_part = MIMEText(html, "html", "utf-8")
    else:
      # Not a list: format as readable text
      readable_body = format_opportunities_readable([parsed]) if isinstance(parsed, dict) else str(parsed)
      html = f"<pre>{readable_body}</pre>"
      html_part = MIMEText(html, "html", "utf-8")
  except Exception:
    # If body isn't JSON, it's already readable text - use it directly
    readable_body = body
    # Convert plain text to HTML with proper formatting
    safe = body.replace("\n", "<br />")
    # Preserve bullet points and formatting
    safe = safe.replace("  •", "&nbsp;&nbsp;•")
    html = f"""
    <html>
    <head>
      <meta charset="utf-8">
      <style>
        body {{ font-family: Arial, sans-serif; color: #111; line-height: 1.6; padding: 20px; }}
        .job-section {{ margin: 15px 0; }}
      </style>
    </head>
    <body>
      <div style="white-space: pre-wrap;">{safe}</div>
    </body>
    </html>
    """
    html_part = MIMEText(html, "html", "utf-8")

  # Plain text part with readable format
  plain_part = MIMEText(readable_body, "plain", "utf-8")

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
