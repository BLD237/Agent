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

    # Normalize/parse agent output safely
    try:
        if isinstance(result, dict) and "output" in result:
            raw = result["output"]
            if isinstance(raw, str):
                opportunities = json.loads(raw)
            else:
                opportunities = sanitize_for_json(raw)
        elif isinstance(result, str):
            opportunities = json.loads(result)
        else:
            opportunities = sanitize_for_json(result)
    except Exception as e:
        logger.error("Failed to parse or sanitize agent output: %s", str(e))
        raise
    # Log titles and some metadata for visibility
    for i, opp in enumerate(opportunities[:10], start=1):
        title = opp.get("title") or opp.get("job_title") or "(no title)"
        logger.info("Opportunity %d: %s | %s | %s", i, title, opp.get("country"), opp.get("official_link"))
    new_items = []

    for opp in opportunities:
        if not opportunity_exists(
            opp["official_link"],
            opp["title"],
            opp["country"]
        ):
            save_opportunity(opp)
            new_items.append(opp)

    email = data.email if data else None

    if email and new_items:
        send_email(
            subject="New International Job Opportunities",
            body=json.dumps(new_items, indent=2),
            to_email=email
        )

    return {
        "new_results": new_items,
        "count": len(new_items)
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
