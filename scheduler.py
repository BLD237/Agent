import json
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

from agent import invoke_agent, preview_search
from email_service import send_email
from job_config import DAILY_JOB_CONFIG, AGENT_PROMPT, SEARCH_QUERY, SEARCH_MAX_RESULTS
from utils import sanitize_for_json
from db import opportunity_exists, save_opportunity

logger = logging.getLogger("agent")


def daily_job_search():
    logger.info("Running daily opportunity search")

    # Fetch and summarize search results first to reduce token consumption
    try:
        logger.info("Fetching search results for query: %s", SEARCH_QUERY[:100])
        summarized_results = preview_search(SEARCH_QUERY, max_results=SEARCH_MAX_RESULTS)
        logger.info("Search results fetched and summarized")
    except Exception as e:
        logger.error("Failed to fetch search results: %s", str(e))
        return

    # Pass summarized search results to the agent
    payload = {
        "input": AGENT_PROMPT,
        "search_results": summarized_results,
    }

    result = invoke_agent(payload)

    # Get the text output directly from the agent
    try:
        if isinstance(result, dict) and "output" in result:
            email_body = result["output"]
        elif isinstance(result, str):
            email_body = result
        else:
            email_body = str(result)
        
        # Check if we got meaningful content
        if not email_body or email_body.strip() == "" or "No new opportunities" in email_body:
            logger.info("No new opportunities found today")
            return
        
        logger.info("Agent returned readable text format, sending directly to email")
    except Exception as e:
        logger.error("Failed to get agent output: %s", str(e))
        return

    # Send the readable text directly to email
    for email in DAILY_JOB_CONFIG["emails"]:
        send_email(
            subject="New Germany Ausbildung & Canada Visa Jobs",
            body=email_body,
            to_email=email
        )


def start_scheduler():
    scheduler = BackgroundScheduler(
        timezone=pytz.timezone("Africa/Douala")
    )

    scheduler.add_job(
        daily_job_search,
        CronTrigger(hour=5, minute=0)
    )

    scheduler.start()
    logger.info("Scheduler started (5 AM GMT+1)")

