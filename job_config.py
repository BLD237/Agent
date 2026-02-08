"""
Configuration file for job opportunity search and email notifications.

This file contains:
- Search query for finding job opportunities
- Agent prompt for processing opportunities
- Maximum number of search results
- Daily job configuration including email recipients
"""

# Search query for finding international job opportunities
SEARCH_QUERY = "Germany Ausbildung programs Canada visa sponsorship LMIA jobs international applicants 2024 2025"

# Maximum number of search results to fetch
SEARCH_MAX_RESULTS = 30

# Agent prompt - instructions for the AI agent to process search results
AGENT_PROMPT = """Please analyze the search results and extract international job opportunities.

Focus on:
- Germany: Ausbildung (vocational training) programs that accept international applicants
- Canada: Jobs with visa sponsorship, LMIA (Labour Market Impact Assessment), or relocation support

For each opportunity, extract and format the following information in a clear, readable JSON format:
- Job title
- Country
- City or region
- Field/Industry
- Salary information (if available)
- Language requirements
- Visa/sponsorship details
- Official link to the job posting

Make sure all information is complete, detailed, and human-readable. The data will be sent via email to users who need clear, understandable information."""

# Daily job configuration
DAILY_JOB_CONFIG = {
    "emails": [
        # Add email addresses here that should receive daily job opportunity notifications
        # Example: "user@example.com",
        # You can add multiple email addresses:
        # "user1@example.com",
        # "user2@example.com",
        "muforbelmond20@gmail.com"
    ]
}

