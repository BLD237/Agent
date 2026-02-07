DAILY_JOB_CONFIG = {
    "emails": [
        "muforbelmond61@gmail.com",
        "muforbelmond20@gmail.com",
        "muforbelmond62@gmail.com"
    ]
}

# Hard-coded agent prompt used for scheduled and manual searches
AGENT_PROMPT = """
You are an expert international job opportunity researcher.

STRICT RULES:
- Use the search tool ONLY TWICE
- Only return REAL and CURRENT opportunities
- MUST accept international applicants
- MUST include visa sponsorship, LMIA, or relocation support
- Ignore expired or unofficial sources

FOCUS:
- Germany (Ausbildung)
- Canada (Visa sponsorship / LMIA)

RETURN STRICT JSON ARRAY with fields:
title,
country,
city_or_region,
field,
language_level,
visa_info,
official_link
"""

# Default query used by the search tool (used for preview and scheduled searches)
SEARCH_QUERY = (
    "Germany Ausbildung programs site:.de OR site:.gov "
    "AND international applicants; Canada jobs with visa sponsorship OR LMIA"
)

# Default number of results the search tool should return when previewing
SEARCH_MAX_RESULTS = 5
# Summarization strategy to reduce token consumption before sending to Gemini
# Options: "none" (no summarization), "extract" (extract key fields), "summarize" (use local model)
SUMMARIZATION_MODE = "extract"

# Max characters to keep per search result (for "extract" mode)
RESULT_SUMMARY_LENGTH = 300