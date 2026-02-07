import json
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

from agent import invoke_agent, preview_search
from email_service import send_email
from job_config import DAILY_JOB_CONFIG, AGENT_PROMPT, SEARCH_QUERY, SEARCH_MAX_RESULTS
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

    try:
        opportunities = json.loads(result["output"])
        logger.info("Parsed %d opportunities from agent output", len(opportunities))
    except Exception as e:
        logger.error("Failed to parse agent output: %s", str(e))
        return

    new_items = []

    for opp in opportunities:
        if not opportunity_exists(
            opp["official_link"],
            opp["title"],
            opp["country"]
        ):
            save_opportunity(opp)
            new_items.append(opp)

    if not new_items:
        logger.info("No new opportunities found today")
        return

    logger.info("Sending email with %d new opportunities", len(new_items))
    email_body = json.dumps(new_items, indent=2)

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

