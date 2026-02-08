import os

from langchain_community.tools.tavily_search import TavilySearchResults
from langchain.agents import create_agent
from dotenv import load_dotenv
from summarization import summarize_results

load_dotenv()

# Determine which LLM to use
# Default to Ollama (local model), set USE_GEMINI=true to use Gemini instead
USE_GEMINI = os.getenv("USE_GEMINI", "false").lower() == "true"
USE_LOCAL_MODEL = not USE_GEMINI  # Use Ollama by default
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "mistral")  # Best balance: fast, high quality, supports tools
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

if USE_LOCAL_MODEL:
    # Use local Ollama model (no API key needed)
    from langchain_ollama import ChatOllama
    
    print(f"🚀 Using local Ollama model: {OLLAMA_MODEL} at {OLLAMA_BASE_URL}")
    
    llm = ChatOllama(
        model=OLLAMA_MODEL,
        base_url=OLLAMA_BASE_URL,
        temperature=0,
    )
else:
    # Use Google Gemini API
    from langchain_google_genai import ChatGoogleGenerativeAI
    
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "Google Gemini API key missing. Set GOOGLE_API_KEY or GEMINI_API_KEY environment variable, "
            "or use local model: export USE_GEMINI=false (Ollama is default)"
        )
    
    print(f"🌐 Using Gemini API: {os.getenv('GEMINI_MODEL', 'gemini-2.0-flash')}")
    
    llm = ChatGoogleGenerativeAI(
        model=os.getenv("GEMINI_MODEL", "gemini-2.0-flash"),
        temperature=0,
        api_key=api_key,
    )

search_tool = TavilySearchResults(max_results=6)

tools = [search_tool]

system_prompt = """You are an expert international job opportunity researcher.

STRICT RULES:
- Use the search tool. 
- Only return REAL and CURRENT opportunities
- MUST accept international applicants
- MUST include visa sponsorship, LMIA, or relocation support
- Ignore expired or unofficial sources

FOCUS:
- Germany (Ausbildung)
- Canada (Visa sponsorship / LMIA)

OUTPUT FORMAT:
You MUST return your response as READABLE TEXT in the following format. This text will be sent directly via email, so make it clear and professional.

Format each job opportunity exactly like this:

Job 1:
  title: [Clear, descriptive job title]
  description: [Detailed job description including responsibilities, requirements, and key information about the role]
  Country: [Full country name]
  City/Region: [Specific city or region name]
  Field: [Industry or field of work, e.g., "Software Engineering", "Healthcare", "Engineering"]
  Language Level: [Specific language requirements, e.g., "German B2 level required", "English proficiency required"]
  Visa Information: [Detailed visa/sponsorship information, e.g., "Work visa sponsorship available", "LMIA approved position"]
  Salary: [Specific salary range or compensation details, e.g., "€50,000 - €70,000 per year"]
  Official Link: [Valid URL to the official job posting]

Job 2:
  title: [Next job title]
  description: [Detailed job description]
  Country: [Country]
  City/Region: [City/Region]
  Field: [Field]
  Language Level: [Language requirements]
  Visa Information: [Visa details]
  Salary: [Salary information]
  Official Link: [Link]

Continue this format for all opportunities found.

IMPORTANT:
- Start with "Found X new job opportunity/opportunities:" if you have results
- Use "Job 1:", "Job 2:", etc. for numbering
- Always include "title:" and "description:" fields for each job
- Description should be comprehensive and informative (2-4 sentences)
- Make all information complete, detailed, and human-readable
- If no opportunities found, return "No new opportunities found."
- Do NOT use JSON format - return plain readable text only
- Do NOT use bullet points (•) - use the format shown above with field names followed by colons
"""

agent_executor = create_agent(
    model=llm,
    tools=tools,
    system_prompt=system_prompt
)

# --- Rate limiting + caching wrapper (only for Gemini API) ---
import time
import threading
import json
import logging
from collections import deque

# Rate limiting only applies to Gemini API, not Ollama
# stricter default rate limit (user requested 2-3 max)
RATE_LIMIT = int(os.getenv("GEMINI_MAX_RPM", "2")) if USE_GEMINI else 999  # requests per minute (unlimited for Ollama)
MAX_WAIT_SECONDS = int(os.getenv("GEMINI_MAX_WAIT", "30"))
CACHE_TTL = int(os.getenv("GEMINI_CACHE_TTL", "600"))  # seconds

_call_timestamps = deque()
_timestamps_lock = threading.Lock()
_cache = {}
_cache_lock = threading.Lock()

# logging and metrics
logger = logging.getLogger("agent")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s %(levelname)s [agent] %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.setLevel(logging.INFO)

_metrics = {
    "total_invocations": 0,
    "model_calls": 0,
    "cache_hits": 0,
    "cache_misses": 0,
    "rate_limited_waits": 0,
    "retries": 0,
    "errors": 0,
}
_metrics_lock = threading.Lock()


def get_metrics():
    with _metrics_lock:
        return dict(_metrics)


def invoke_agent(payload):
    """Invoke the compiled agent with rate limiting, simple caching and retries.

    - `payload` may be a string or dict.
    - Uses in-memory cache for `CACHE_TTL` seconds to avoid repeat queries.
    - Enforces `RATE_LIMIT` calls per 60s window and will wait up to `MAX_WAIT_SECONDS`.
    """
    # Normalize input text from payload (accept string or dict shapes)
    if isinstance(payload, str):
        input_text = payload
    elif isinstance(payload, dict):
        # common keys
        input_text = payload.get("input") or payload.get("query") or payload.get("message")
        if not input_text and "messages" in payload:
            # join message contents
            msgs = payload.get("messages")
            if isinstance(msgs, list) and msgs:
                # take last user/system content
                input_text = "\n".join([m.get("content", "") for m in msgs if m.get("content")])
    else:
        input_text = str(payload)

    if not input_text:
        input_text = ""

    # Optionally enhance prompt with search results summary (if available)
    if "search_results" in payload:
        sr = payload.get("search_results")
        summarized_sr = summarize_results(sr)
        logger.info("Including summarized search results in prompt")
        input_text = f"{input_text}\n\n## Search Context:\n{summarized_sr}"

    # build normalized agent payload as messages (system + user)
    normalized_payload = {
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": input_text},
        ]
    }

    # Normalize cache key
    key = json.dumps(normalized_payload, sort_keys=True)

    now = time.time()

    with _metrics_lock:
        _metrics["total_invocations"] += 1

    logger.info("Invoking agent for key=%s", (key if len(str(key)) < 200 else str(key)[:200] + "..."))

    # Check cache
    with _cache_lock:
        entry = _cache.get(key)
        if entry and now - entry[0] < CACHE_TTL:
            with _metrics_lock:
                _metrics["cache_hits"] += 1
            logger.info("Cache hit for key")
            return entry[1]
        else:
            with _metrics_lock:
                _metrics["cache_misses"] += 1
            logger.info("Cache miss for key")

    # Enforce rate limit (only for Gemini API)
    wait = 0
    if USE_GEMINI:  # Only apply rate limiting for Gemini
        with _timestamps_lock:
            # prune old timestamps
            while _call_timestamps and now - _call_timestamps[0] > 60:
                _call_timestamps.popleft()
            if len(_call_timestamps) >= RATE_LIMIT:
                oldest = _call_timestamps[0]
                wait = 60 - (now - oldest)
                if wait > MAX_WAIT_SECONDS:
                    with _metrics_lock:
                        _metrics["errors"] += 1
                    raise RuntimeError(
                        f"Rate limit exceeded ({RATE_LIMIT}/min). Try again later or increase GEMINI_MAX_RPM."
                    )

    if wait > 0:
        with _metrics_lock:
            _metrics["rate_limited_waits"] += 1
        logger.warning("Rate limit reached, sleeping %.2fs", wait)
        time.sleep(wait)

    # record timestamp
    with _timestamps_lock:
        _call_timestamps.append(time.time())

    # Call agent with retries on quota errors
    backoff = 1
    max_attempts = 4
    last_exc = None
    for attempt in range(1, max_attempts + 1):
        try:
            logger.info("Calling agent (attempt %d)", attempt)
            with _metrics_lock:
                _metrics["model_calls"] += 1
            # prefer invoking the compiled agent with normalized messages
            result = agent_executor.invoke(normalized_payload)
            logger.info("Agent call succeeded")
            with _cache_lock:
                _cache[key] = (time.time(), result)
            return result
        except Exception as e:
            last_exc = e
            msg = str(e)
            with _metrics_lock:
                _metrics["errors"] += 1
            logger.error("Agent call failed on attempt %d: %s", attempt, msg)
            # If it's a quota/429-like error, wait and retry with exponential backoff
            if "RESOURCE_EXHAUSTED" in msg or "429" in msg or "quota" in msg.lower():
                with _metrics_lock:
                    _metrics["retries"] += 1
                logger.warning("Quota error detected, backing off for %.1fs", backoff)
                time.sleep(backoff)
                backoff = min(backoff * 2, 30)
                continue
            raise

    # If we exit loop, raise last exception
    logger.error("All attempts failed, raising last exception")
    raise last_exc


def preview_search(query: str, max_results: int | None = None):
    """Run the search tool directly and return raw results.

    This does not call the LLM and can be used to inspect or trim results
    before sending them to the model.
    """
    logger.info("Preview search started")
    try:
        if max_results is not None:
            tool = TavilySearchResults(max_results=max_results)
        else:
            tool = search_tool

        # most LangChain tools implement `run`
        res = tool.run(query)
        logger.info("Preview search returned results type=%s", type(res))

        # Apply summarization to reduce token consumption
        summarized = summarize_results(res)
        logger.info(
            "Summarization applied; original_size=%s, summarized_size=%s",
            len(str(res)),
            len(str(summarized)),
        )
        return summarized
    except Exception as e:
        logger.error("Preview search failed: %s", str(e))
        raise


