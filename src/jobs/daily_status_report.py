"""Daily status report cron job — runs at 8AM, sends summary email to QA team."""
import os
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

from openai import AzureOpenAI

# ── Azure OpenAI ──────────────────────────────────────────────────────────────
azure_client = AzureOpenAI(
    api_key=os.getenv("AZURE_API_KEY"),
    azure_endpoint=os.getenv("AZURE_API_BASE"),
    api_version="2024-05-01-preview",
)

# ── Email config (set in .env) ────────────────────────────────────────────────
SMTP_HOST     = os.getenv("SMTP_HOST", "smtp.office365.com")
SMTP_PORT     = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER     = os.getenv("SMTP_USER", "md.mohiuddinkhan@xeniaretail.com")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
EMAIL_FROM    = os.getenv("REPORT_EMAIL_FROM", SMTP_USER)
EMAIL_TO      = os.getenv("REPORT_EMAIL_TO", "md.mohiuddinkhan@xeniaretail.com")   # comma-separated recipients

# ── Dashboard API ─────────────────────────────────────────────────────────────
BASE_DASHBOARD_API = "https://app-itdashboard-test.azurewebsites.net/api"


# ─────────────────────────────────────────────────────────────────────────────
# Data fetchers
# ─────────────────────────────────────────────────────────────────────────────

def _today_params() -> dict:
    today = datetime.now()
    date_key = int(today.strftime("%Y%m%d"))
    start_dt = today.strftime("%Y-%m-%d") + " 00:00:00"
    end_dt   = today.strftime("%Y-%m-%d") + " 23:59:59"
    return {
        "TimeRange": 1,
        "StartDateKey": date_key,
        "EndDateKey": date_key,
        "StartDateTime": start_dt,
        "EndDateTime": end_dt,
    }


def fetch_dashboard_summary() -> dict:
    date_key = _today_params()["StartDateKey"]
    try:
        resp = requests.get(
            f"{BASE_DASHBOARD_API}/ITCentralServer/dashboard-summary/{date_key}",
            timeout=15,
        )
        return resp.json()
    except Exception as e:
        return {"error": str(e)}


def fetch_cs_exceptions() -> list:
    try:
        resp = requests.get(
            f"{BASE_DASHBOARD_API}/ITCentralServer/exceptions",
            params=_today_params(),
            timeout=15,
        )
        return resp.json() or []
    except Exception as e:
        return [{"error": str(e)}]


def fetch_store_exceptions() -> list:
    try:
        resp = requests.get(
            f"{BASE_DASHBOARD_API}/ITCentralServer/storeexceptions",
            params=_today_params(),
            timeout=15,
        )
        return resp.json() or []
    except Exception as e:
        return [{"error": str(e)}]


# ─────────────────────────────────────────────────────────────────────────────
# AI summary
# ─────────────────────────────────────────────────────────────────────────────

SUMMARY_PROMPT = """
You are an IT operations assistant. Based on the data below, write a clear and concise HTML daily status report email for the QA team.

Structure the email with:
1. A brief overall health status (Green / Yellow / Red) with one-sentence reason
2. Dashboard Summary section — highlight success/failure counts
3. CS Exceptions section — list each exception concisely (or "None" if empty)
4. Store Exceptions section — list each exception concisely (or "None" if empty)
5. A short closing note

Use <h2>, <p>, <ul>, <li>, <b> HTML tags for formatting. Keep it professional and scannable.
Do not include <html>, <head>, or <body> tags — just the inner content.

Date: {date}

--- DASHBOARD SUMMARY ---
{dashboard}

--- CS EXCEPTIONS ---
{cs_exceptions}

--- STORE EXCEPTIONS ---
{store_exceptions}
"""


def generate_email_body(dashboard: dict, cs_exceptions: list, store_exceptions: list) -> str:
    today = datetime.now().strftime("%Y-%m-%d")

    prompt = SUMMARY_PROMPT.format(
        date=today,
        dashboard=str(dashboard),
        cs_exceptions=str(cs_exceptions) if cs_exceptions else "None",
        store_exceptions=str(store_exceptions) if store_exceptions else "None",
    )

    response = azure_client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )

    return response.choices[0].message.content


# ─────────────────────────────────────────────────────────────────────────────
# Email sender — Microsoft Graph API (SMTP AUTH not required)
# ─────────────────────────────────────────────────────────────────────────────

TENANT_ID     = os.getenv("AZURE_TENANT_ID", "")
CLIENT_ID     = os.getenv("AZURE_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET", "")


def _get_graph_token() -> str:
    """Obtain an OAuth2 access token from Azure AD for Microsoft Graph."""
    # print(TENANT_ID, CLIENT_ID, CLIENT_SECRET)
    url = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"
    resp = requests.post(url, data={
        "grant_type":    "client_credentials",
        "client_id":     CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "scope":         "https://graph.microsoft.com/.default",
    })
    resp.raise_for_status()
    # print(resp.json()["access_token"])
    return resp.json()["access_token"]


def send_email(subject: str, html_body: str):
    if not EMAIL_FROM or not EMAIL_TO:
        print("[DailyReport] REPORT_EMAIL_FROM or REPORT_EMAIL_TO not configured — skipping email.")
        return

    recipients = [r.strip() for r in EMAIL_TO.split(",") if r.strip()]

    token = _get_graph_token()

    payload = {
        "message": {
            "subject": subject,
            "body": {
                "contentType": "HTML",
                "content": html_body,
            },
            "toRecipients": [
                {"emailAddress": {"address": r}} for r in recipients
            ],
        },
        "saveToSentItems": True,
    }

    resp = requests.post(
        f"https://graph.microsoft.com/v1.0/users/{EMAIL_FROM}/sendMail",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type":  "application/json",
        },
        json=payload,
        timeout=15,
    )
    resp.raise_for_status()
    print(f"[DailyReport] Email sent to: {', '.join(recipients)}")


# ─────────────────────────────────────────────────────────────────────────────
# Main job entry point
# ─────────────────────────────────────────────────────────────────────────────

def run_daily_report():
    today = datetime.now().strftime("%Y-%m-%d")
    print(f"[DailyReport] Running daily status report for {today}")

    try:
        dashboard      = fetch_dashboard_summary()
        cs_exc         = fetch_cs_exceptions()
        store_exc      = fetch_store_exceptions()

        html_body = generate_email_body(dashboard, cs_exc, store_exc)

        subject = f"IT Daily Status Report — {today}"
        send_email(subject, html_body)

    except Exception as e:
        print(f"[DailyReport] Failed: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# Test function — call this manually to verify the full pipeline
# ─────────────────────────────────────────────────────────────────────────────

def test_daily_report(override_email_to: str = None):
    """
    Runs the full report pipeline and prints each step result.
    Optionally override the recipient email to avoid sending to the QA list.

    Usage:
        from src.jobs.daily_status_report import test_daily_report
        test_daily_report("your-email@domain.com")
    """
    today = datetime.now().strftime("%Y-%m-%d")
    print(f"\n{'='*60}")
    print(f"[TEST] Daily Status Report — {today}")
    print(f"{'='*60}\n")

    print("[TEST] 1. Fetching dashboard summary...")
    dashboard = fetch_dashboard_summary()
    print(f"       Result: {str(dashboard)[:300]}\n")

    print("[TEST] 2. Fetching CS exceptions...")
    cs_exc = fetch_cs_exceptions()
    print(f"       Count: {len(cs_exc)} record(s)")
    if cs_exc:
        print(f"       Sample: {str(cs_exc[0])[:200]}\n")

    print("[TEST] 3. Fetching store exceptions...")
    store_exc = fetch_store_exceptions()
    print(f"       Count: {len(store_exc)} record(s)")
    if store_exc:
        print(f"       Sample: {str(store_exc[0])[:200]}\n")

    print("[TEST] 4. Generating email body via Azure OpenAI...")
    html_body = generate_email_body(dashboard, cs_exc, store_exc)
    print(f"       Generated HTML ({len(html_body)} chars):")
    print(f"       {html_body[:500]}...\n")

    global EMAIL_TO
    recipient = override_email_to or EMAIL_TO
    print(f"[TEST] 5. Sending email to: {recipient}")
    original_to = EMAIL_TO
    if override_email_to:
        EMAIL_TO = override_email_to

    try:
        send_email(f"[TEST] IT Daily Status Report — {today}", html_body)
        print("       Email sent successfully.\n")
    except Exception as e:
        print(f"       Email failed: {e}\n")
    finally:
        EMAIL_TO = original_to

    print(f"{'='*60}")
    print("[TEST] Done.")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    test_daily_report()
