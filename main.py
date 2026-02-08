from fastapi import FastAPI, Body
from pydantic import BaseModel
from dotenv import load_dotenv
import json

import logging
from agent import invoke_agent, get_metrics, preview_search
from job_config import AGENT_PROMPT, SEARCH_QUERY, SEARCH_MAX_RESULTS
from pydantic import BaseModel

logger = logging.getLogger("agent")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s %(levelname)s [main] %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.setLevel(logging.INFO)
from scheduler import start_scheduler
from email_service import send_email
from db import opportunity_exists, save_opportunity
from utils import sanitize_for_json

load_dotenv()

app = FastAPI(title="International Job Opportunity AI Bot")


class JobRequest(BaseModel):
    query: str
    email: str | None = None


# preview endpoint no longer requires a request body; uses SEARCH_QUERY and SEARCH_MAX_RESULTS


@app.on_event("startup")
def startup_event():
    start_scheduler()


@app.post("/search-opportunities")
def search_opportunities(data: JobRequest = Body(default=None)):
    # Use the shared hard-coded prompt for manual triggers as well
    logger.info("Received manual search request; using hard-coded agent prompt")

    # Fetch and summarize search results first to reduce token consumption
    try:
        logger.info("Fetching search results for query: %s", SEARCH_QUERY[:100])
        summarized_results = preview_search(SEARCH_QUERY, max_results=SEARCH_MAX_RESULTS)
        logger.info("Search results fetched and summarized")
    except Exception as e:
        logger.error("Failed to fetch search results: %s", str(e))
        raise

    # Pass summarized search results to the agent
    payload = {
        "input": AGENT_PROMPT,
        "search_results": summarized_results,
    }

    try:
        result = invoke_agent(payload)
    except Exception as e:
        logger.error("invoke_agent failed: %s", str(e))
        raise

    # Get the readable text output directly from the agent
    try:
        if isinstance(result, dict) and "output" in result:
            email_body = result["output"]
        elif isinstance(result, str):
            email_body = result
        else:
            email_body = str(result)
        
        logger.info("Agent returned readable text format")
    except Exception as e:
        logger.error("Failed to get agent output: %s", str(e))
        raise

    email = data.email if data else None

    # Send the readable text directly to email if provided
    if email and email_body and email_body.strip() and "No new opportunities" not in email_body:
        send_email(
            subject="New International Job Opportunities",
            body=email_body,
            to_email=email
        )

    # Count opportunities from the text (simple count of "Job X:" patterns)
    opportunity_count = email_body.count("Job ") if email_body else 0

    return {
        "output": email_body,
        "count": opportunity_count,
        "format": "readable_text"
    }



@app.get("/metrics")
def metrics():
    """Return in-memory metrics about agent usage."""
    return get_metrics()


@app.get("/preview-search")
def preview_search_endpoint():
    """Return raw search results from the search tool using the configured query (no body required)."""
    q = SEARCH_QUERY
    max_r = SEARCH_MAX_RESULTS
    logger.info("Preview search endpoint called; max_results=%s", max_r)
    try:
        from agent import preview_search as _preview

        res = _preview(q, max_results=max_r)
        return {"results": res}
    except Exception as e:
        logger.error("preview_search_endpoint failed: %s", str(e))
        raise
