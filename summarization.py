"""Summarization utilities to reduce token consumption from search results."""
import json
import logging
from job_config import SUMMARIZATION_MODE, RESULT_SUMMARY_LENGTH

logger = logging.getLogger("agent")


def extract_key_fields(result):
    """Extract and truncate key fields from a search result."""
    if isinstance(result, dict):
        return {
            "title": result.get("title", "")[:100],
            "link": result.get("link", ""),
            "snippet": result.get("snippet", "")[:RESULT_SUMMARY_LENGTH],
        }
    return {"content": str(result)[:RESULT_SUMMARY_LENGTH]}


def summarize_results(raw_results):
    """Apply the configured summarization strategy to search results.

    Args:
        raw_results: Raw search results (string, list, or dict)

    Returns:
        Processed results ready for the LLM (str or dict)
    """
    logger.info("Summarizing results with mode=%s", SUMMARIZATION_MODE)

    if isinstance(raw_results, str):
        # If raw_results is a plain string, try to parse as JSON
        try:
            data = json.loads(raw_results)
        except Exception:
            # Not JSON, just truncate
            logger.info("Raw results not JSON, truncating to %d chars", RESULT_SUMMARY_LENGTH)
            return raw_results[: RESULT_SUMMARY_LENGTH]
    else:
        data = raw_results

    if SUMMARIZATION_MODE == "none":
        return data

    elif SUMMARIZATION_MODE == "extract":
        # Extract key fields only
        if isinstance(data, list):
            processed = [extract_key_fields(item) for item in data]
        else:
            processed = extract_key_fields(data)
        logger.info("Extracted key fields from results")
        return json.dumps(processed) if isinstance(processed, list) else processed

    elif SUMMARIZATION_MODE == "summarize":
        # Use a small local model to summarize (requires transformers + model download)
        try:
            from transformers import pipeline

            summarizer = pipeline(
                "summarization", model="facebook/bart-large-cnn", device=-1  # device=-1 = CPU
            )

            if isinstance(data, list):
                summaries = []
                for item in data:
                    text = json.dumps(item) if isinstance(item, dict) else str(item)
                    # Bart requires min 50 tokens
                    if len(text.split()) > 50:
                        try:
                            summary = summarizer(text[:1024], max_length=100, min_length=30)[
                                0
                            ]["summary_text"]
                            summaries.append({"original": text[:200], "summary": summary})
                        except Exception as e:
                            logger.warning("Summarization failed for item: %s", str(e))
                            summaries.append(extract_key_fields(item))
                    else:
                        summaries.append(extract_key_fields(item))
                logger.info("Summarized %d results using BART", len(summaries))
                return json.dumps(summaries)
            else:
                text = json.dumps(data) if isinstance(data, dict) else str(data)
                summary = summarizer(text[:1024], max_length=100, min_length=30)[0]["summary_text"]
                logger.info("Summarized results using BART")
                return summary
        except ImportError:
            logger.warning(
                "transformers not installed, falling back to extract mode. "
                "Install with: pip install transformers"
            )
            return summarize_results(raw_results) if SUMMARIZATION_MODE != "extract" else data

    else:
        logger.warning("Unknown summarization mode %s, returning data as-is", SUMMARIZATION_MODE)
        return data
