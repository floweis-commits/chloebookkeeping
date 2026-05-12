"""
Email service — sends transactional emails via Resend.

All emails go through a single send() function so the provider
can be swapped without touching call sites.
"""

import httpx
from backend.config import settings


async def send(
    to: str,
    subject: str,
    html: str,
    from_name: str = "Chloe Bookkeeping",
    from_email: str = "reports@channeledbychloe.com",
) -> bool:
    """
    Send an email via Resend. Returns True on success, False on failure.
    Silently swallows errors so a failed email never crashes the scheduler.
    """
    if not settings.resend_api_key:
        print(f"[email] RESEND_API_KEY not set — skipping email to {to}")
        return False

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {settings.resend_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "from": f"{from_name} <{from_email}>",
                    "to": [to],
                    "subject": subject,
                    "html": html,
                },
                timeout=10,
            )
            resp.raise_for_status()
            return True
    except Exception as e:
        print(f"[email] Failed to send to {to}: {e}")
        return False


def _review_reminder_html(period_label: str, flagged_count: int, app_url: str) -> str:
    return f"""
<!DOCTYPE html>
<html>
<head>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; color: #333; max-width: 560px; margin: 0 auto; padding: 24px; }}
  .header {{ background: #f9e8e4; border-radius: 12px; padding: 24px; margin-bottom: 24px; }}
  h1 {{ color: #b05c4a; font-size: 20px; margin: 0 0 8px; }}
  .stat {{ font-size: 40px; font-weight: 700; color: #b05c4a; }}
  .btn {{ display: inline-block; background: #c9897a; color: white; padding: 12px 28px; border-radius: 8px; text-decoration: none; font-weight: 600; margin-top: 20px; }}
  .footer {{ margin-top: 32px; font-size: 12px; color: #999; }}
</style>
</head>
<body>
  <div class="header">
    <h1>Action needed — {period_label} report</h1>
    <div class="stat">{flagged_count}</div>
    <div>transaction{' ' if flagged_count == 1 else 's '}need{'' if flagged_count == 1 else ''} your review</div>
  </div>
  <p>The bookkeeping agents have finished pulling and categorizing data for <strong>{period_label}</strong>.
  Before the management report can be generated, you need to review and approve the flagged items above.</p>
  <p>Common reasons items get flagged:
  <ul>
    <li>A payment processor transaction has no matching QuickBooks entry</li>
    <li>Amounts don't match between QuickBooks and a payment source</li>
    <li>A transaction couldn't be categorized with high confidence</li>
  </ul>
  </p>
  <a href="{app_url}/review" class="btn">Review flagged items →</a>
  <div class="footer">
    Chloe Bookkeeping · This email was sent automatically at month-end.
  </div>
</body>
</html>
"""


def _report_ready_html(period_label: str, client_name: str, app_url: str) -> str:
    return f"""
<!DOCTYPE html>
<html>
<head>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; color: #333; max-width: 560px; margin: 0 auto; padding: 24px; }}
  .header {{ background: #e8f4e8; border-radius: 12px; padding: 24px; margin-bottom: 24px; }}
  h1 {{ color: #2d6a4f; font-size: 20px; margin: 0 0 8px; }}
  .btn {{ display: inline-block; background: #40916c; color: white; padding: 12px 28px; border-radius: 8px; text-decoration: none; font-weight: 600; margin-top: 20px; }}
  .footer {{ margin-top: 32px; font-size: 12px; color: #999; }}
</style>
</head>
<body>
  <div class="header">
    <h1>✓ {period_label} report is ready</h1>
  </div>
  <p>All flagged items have been reviewed and the <strong>{period_label} Management Report</strong>
  for <strong>{client_name}</strong> has been generated.</p>
  <a href="{app_url}/reports" class="btn">View report →</a>
  <div class="footer">
    Chloe Bookkeeping · This email was sent automatically.
  </div>
</body>
</html>
"""


async def send_review_reminder(
    to: str,
    period_label: str,
    flagged_count: int,
    app_url: str,
) -> bool:
    return await send(
        to=to,
        subject=f"Action needed: {flagged_count} item{'s' if flagged_count != 1 else ''} to review for {period_label}",
        html=_review_reminder_html(period_label, flagged_count, app_url),
    )


async def send_report_ready(
    to: str,
    period_label: str,
    client_name: str,
    app_url: str,
) -> bool:
    return await send(
        to=to,
        subject=f"{period_label} management report is ready — {client_name}",
        html=_report_ready_html(period_label, client_name, app_url),
    )
