#!/usr/bin/env python3
"""
Custom script to invoke the agent directly for testing and debugging.
Does NOT require FastAPI server to be running.

Usage:
  python3 run_agent.py search "fintech funding opportunities"
  python3 run_agent.py preview "funding rounds"
  python3 run_agent.py metrics
  python3 run_agent.py scheduled
"""

import sys
import json
import os
import logging
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import agent utilities
from agent import invoke_agent, preview_search, get_metrics
from summarization import summarize_results
from email_service import send_email
from job_config import AGENT_PROMPT, SEARCH_QUERY, SEARCH_MAX_RESULTS
from utils import sanitize_for_json


def cmd_search(query):
    """Run a search + agent invocation with custom query."""
    logger.info(f"🔍 Searching for opportunities: {query}")
    
    try:
        # Step 1: Preview search results
        logger.info("Step 1: Fetching search results...")
        search_results = preview_search(query, max_results=SEARCH_MAX_RESULTS)
        logger.info(f"  ✓ Found {len(search_results)} results")
        
        # Step 2: Summarize results
        logger.info("Step 2: Summarizing results...")
        summary = summarize_results(search_results)
        logger.info(f"  ✓ Summarized to {len(summary)} items")
        
        # Print preview
        print("\n📋 Search Results Preview:")
        print("-" * 70)
        for i, item in enumerate(summary[:3], 1):
            if isinstance(item, dict):
                print(f"{i}. {item.get('title', 'N/A')}")
                print(f"   Link: {item.get('link', 'N/A')}")
                print(f"   {item.get('snippet', 'N/A')[:100]}...")
            else:
                print(f"{i}. {str(item)[:100]}...")
        print("-" * 70)
        
        # Step 3: Invoke agent
        logger.info("Step 3: Invoking agent for analysis...")
        payload = {
            "messages": [
                {"role": "system", "content": AGENT_PROMPT},
                {"role": "user", "content": f"Analyze these opportunities:\n{json.dumps(summary[:5])}"}
            ]
        }
        
        result = invoke_agent(payload)

        logger.info("✓ Agent analysis complete")
        print("\n🤖 Agent Analysis:")
        print("-" * 70)
        try:
            print(json.dumps(sanitize_for_json(result), indent=2, ensure_ascii=False))
        except Exception:
            print(str(result))
        print("-" * 70)
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Error during search: {e}", exc_info=True)
        sys.exit(1)


def cmd_preview(query=None):
    """Preview search results without agent analysis."""
    query = query or SEARCH_QUERY
    logger.info(f"📋 Previewing search results for: {query}")
    
    try:
        results = preview_search(query, max_results=SEARCH_MAX_RESULTS)
        
        print(f"\n📄 Search Results ({len(results)} found):")
        print("-" * 70)
        
        for i, item in enumerate(results, 1):
            if isinstance(item, dict):
                print(f"\n{i}. {item.get('title', 'N/A')}")
                print(f"   Link: {item.get('link', 'N/A')}")
                print(f"   {item.get('snippet', 'N/A')}")
            else:
                print(f"\n{i}. {item}")
        
        print("-" * 70)
        print(f"Total: {len(results)} results")
        
    except Exception as e:
        logger.error(f"❌ Error during preview: {e}", exc_info=True)
        sys.exit(1)


def cmd_scheduled():
    """Simulate a scheduled job run."""
    logger.info("⏰ Running scheduled job simulation...")
    
    try:
        print("\n📅 Scheduled Job Run")
        print("=" * 70)
        print(f"Time: {datetime.now().isoformat()}")
        print(f"Query: {SEARCH_QUERY}")
        print("=" * 70)
        
        # Run full workflow
        result = cmd_search(SEARCH_QUERY)
        
        print("\n✓ Scheduled job completed successfully")
        
    except Exception as e:
        logger.error(f"❌ Scheduled job failed: {e}", exc_info=True)
        sys.exit(1)


def cmd_metrics():
    """Display current agent metrics."""
    print("\n📊 Agent Metrics")
    print("-" * 70)
    
    metrics = get_metrics()
    for key, value in metrics.items():
        if isinstance(value, (int, float)):
            print(f"{key:20s}: {value}")
        else:
            print(f"{key:20s}: {str(value)[:50]}")
    
    print("-" * 70)
    print(f"Total invocations: {metrics.get('total_invocations', 0)}")
    print(f"Model calls: {metrics.get('model_calls', 0)}")
    print(f"Cache hits: {metrics.get('cache_hits', 0)}")
    print(f"Cache misses: {metrics.get('cache_misses', 0)}")
    print(f"Rate limited waits: {metrics.get('rate_limited_waits', 0)}")
    print(f"Retries: {metrics.get('retries', 0)}")


def cmd_search_and_email(query, recipient_email):
    """Run full workflow: search → summarize → agent → email results."""
    logger.info(f"🔍 Running full workflow and emailing to {recipient_email}")
    
    # Get email config from environment
    smtp_config = {
        "server": os.getenv("SMTP_HOST", "smtp.gmail.com"),
        "port": int(os.getenv("SMTP_PORT", "587")),
        "sender": os.getenv("SMTP_EMAIL"),
        "password": os.getenv("SMTP_PASSWORD"),
    }
    
    # Validate SMTP config
    if not smtp_config["sender"] or not smtp_config["password"]:
        print("❌ Error: SMTP credentials not configured!")
        print("\nSet these environment variables in .env:")
        print("  SMTP_EMAIL=your-email@gmail.com")
        print("  SMTP_PASSWORD=your-app-password")
        print("  SMTP_HOST=smtp.gmail.com (optional, default shown)")
        print("  SMTP_PORT=587 (optional, default shown)")
        print("\nFor Gmail:")
        print("  1. Enable 2-factor authentication")
        print("  2. Generate app password: https://myaccount.google.com/apppasswords")
        print("  3. Use that password in SMTP_PASSWORD")
        sys.exit(1)
    
    try:
        # Step 1: Search
        logger.info("Step 1: Searching for opportunities...")
        search_results = preview_search(query, max_results=SEARCH_MAX_RESULTS)
        logger.info(f"  ✓ Found {len(search_results)} results")
        
        # Step 2: Summarize
        logger.info("Step 2: Summarizing results...")
        summary = summarize_results(search_results)
        logger.info(f"  ✓ Summarized to {len(summary)} items")
        
        # Step 3: Agent analysis
        logger.info("Step 3: Invoking agent...")
        payload = {
            "messages": [
                {"role": "system", "content": AGENT_PROMPT},
                {"role": "user", "content": f"Analyze these opportunities:\n{json.dumps(summary[:5])}"}
            ]
        }
        agent_result = invoke_agent(payload)
        logger.info("  ✓ Agent analysis complete")
        
        # Step 4: Format for email
        logger.info("Step 4: Formatting email...")
        email_body = {
            "timestamp": datetime.now().isoformat(),
            "query": query,
            "results_count": len(summary),
            "opportunities": sanitize_for_json(summary[:5]),
            "analysis": sanitize_for_json(agent_result)
        }
        
        email_subject = f"🎯 Funding Opportunities - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        
        # Step 5: Send email
        logger.info("Step 5: Sending email...")
        success = send_email(
            recipient=recipient_email,
            subject=email_subject,
            body=json.dumps(email_body),
            smtp_config=smtp_config
        )
        
        if success:
            logger.info(f"✓ Email sent successfully to {recipient_email}")
            print("\n✅ Full workflow completed!")
            print(f"   Query: {query}")
            print(f"   Results: {len(summary)} opportunities found")
            print(f"   Email sent to: {recipient_email}")
        else:
            logger.error("Failed to send email")
            print("⚠️  Workflow completed but email failed to send")
        
        return agent_result
        
    except Exception as e:
        logger.error(f"❌ Error during workflow: {e}", exc_info=True)
        sys.exit(1)


def cmd_invoke_raw(payload_json):
    """Invoke agent with raw JSON payload."""
    logger.info("🚀 Invoking agent with raw payload...")
    
    try:
        payload = json.loads(payload_json)
        logger.info(f"Payload: {json.dumps(payload, indent=2)}")
        
        result = invoke_agent(payload)
        
        print("\n📤 Agent Response:")
        print("-" * 70)
        print(result)
        print("-" * 70)
        
    except json.JSONDecodeError as e:
        logger.error(f"❌ Invalid JSON payload: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Error invoking agent: {e}", exc_info=True)
        sys.exit(1)


def cmd_test_api_key():
    """Test if Gemini API key is configured."""
    print("\n🔑 API Key Configuration Check")
    print("-" * 70)
    
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
    
    if api_key:
        masked_key = api_key[:10] + "..." + api_key[-5:]
        print(f"✓ API Key found: {masked_key}")
    else:
        print("❌ API Key NOT found!")
        print("   Set GOOGLE_API_KEY or GEMINI_API_KEY environment variable")
        return False
    
    print(f"✓ Model: {model}")
    print("-" * 70)
    return True


def cmd_test_email():
    """Test if email (SMTP) is configured."""
    print("\n📧 Email Configuration Check")
    print("-" * 70)
    
    sender = os.getenv("SMTP_EMAIL")
    password = os.getenv("SMTP_PASSWORD")
    server = os.getenv("SMTP_HOST", "smtp.gmail.com")
    port = os.getenv("SMTP_PORT", "587")
    
    if not sender:
        print("❌ SMTP_EMAIL not set!")
        print("   Example: export SMTP_EMAIL=your-email@gmail.com")
        return False
    else:
        print(f"✓ Email: {sender}")
    
    if not password:
        print("❌ SMTP_PASSWORD not set!")
        print("   Example: export SMTP_PASSWORD=your-app-password")
        return False
    else:
        masked_pwd = password[:3] + "*" * (len(password) - 6) + password[-3:]
        print(f"✓ Password: {masked_pwd}")
    
    print(f"✓ Server: {server}")
    print(f"✓ Port: {port}")
    print("-" * 70)
    print("✅ Email configuration looks good!")
    return True


def print_help():
    """Print usage help."""
    help_text = """
╔══════════════════════════════════════════════════════════════════════════════╗
║                         AGENT TEST RUNNER                                    ║
║                    Custom script to invoke the agent                         ║
╚══════════════════════════════════════════════════════════════════════════════╝

USAGE:
  python3 run_agent.py <command> [args]

COMMANDS:

  search "<query>"
    Run full workflow: search → summarize → agent analysis
    Example: python3 run_agent.py search "fintech funding opportunities"

  search-and-email "<query>" "<recipient-email>"
    Run full workflow and SEND EMAIL with results
    Example: python3 run_agent.py search-and-email "Series A funding" user@example.com

  preview [query]
    Preview raw search results without agent analysis
    Example: python3 run_agent.py preview "Series A funding"
    Example: python3 run_agent.py preview  (uses SEARCH_QUERY from config)

  scheduled
    Simulate a scheduled job run with config query
    Example: python3 run_agent.py scheduled

  invoke '<json>'
    Invoke agent with raw JSON payload
    Example: python3 run_agent.py invoke '{"messages":[{"role":"user","content":"Find opportunities"}]}'

  metrics
    Display current agent metrics (cache hits, rate limits, etc.)
    Example: python3 run_agent.py metrics

  check-key
    Verify Gemini API key configuration
    Example: python3 run_agent.py check-key

  check-email
    Verify email (SMTP) configuration
    Example: python3 run_agent.py check-email

  help
    Show this help message
    Example: python3 run_agent.py help

ENVIRONMENT VARIABLES:

  GOOGLE_API_KEY        (or GEMINI_API_KEY) - Required for Gemini API
  GEMINI_MODEL          - Model to use (default: gemini-2.0-flash)
  GEMINI_MAX_RPM        - Rate limit requests/minute (default: 10)
  SUMMARIZATION_MODE    - extract/summarize/none (default: extract)

EMAIL CONFIGURATION (for search-and-email):

  SMTP_SENDER           - Your email address (required, e.g., you@gmail.com)
  SMTP_PASSWORD         - Your email password or app password (required)
  SMTP_SERVER           - SMTP server (default: smtp.gmail.com)
  SMTP_PORT             - SMTP port (default: 465)

EXAMPLES:

  1. Check if API key is configured:
     python3 run_agent.py check-key

  2. Preview search results:
     python3 run_agent.py preview "AI funding 2026"

  3. Run full search + analysis:
     python3 run_agent.py search "Series A opportunities"

  4. Run search + send EMAIL with results:
     python3 run_agent.py search-and-email "fintech opportunities" user@gmail.com

  5. Simulate scheduled job:
     python3 run_agent.py scheduled

  6. Check metrics:
     python3 run_agent.py metrics

  7. Check email configuration:
     python3 run_agent.py check-email

GMAIL SETUP FOR EMAIL SENDING:

  1. Enable 2-factor authentication on your Gmail account
  2. Generate an app-specific password:
     https://myaccount.google.com/apppasswords
     Select "Mail" and "Windows Computer" (or other device)
  3. Copy the 16-character password shown
  4. Set environment variables:
     export SMTP_SENDER="your-email@gmail.com"
     export SMTP_PASSWORD="your-16-char-app-password"
  5. Test with:
     python3 run_agent.py check-email

COMPLETE WORKFLOW EXAMPLE:

  # 1. Set up API keys
  export GOOGLE_API_KEY="your-gemini-api-key"

  # 2. Set up email
  export SMTP_SENDER="your-email@gmail.com"
  export SMTP_PASSWORD="your-app-password"

  # 3. Test everything
  python3 run_agent.py check-key
  python3 run_agent.py check-email

  # 4. Run search + email
  python3 run_agent.py search-and-email "Series A funding 2026" recipient@example.com

"""
    print(help_text)


def main():
    """Main CLI entry point."""
    if len(sys.argv) < 2 or sys.argv[1] in ["-h", "--help", "help"]:
        print_help()
        sys.exit(0)
    
    command = sys.argv[1].lower()
    args = sys.argv[2:] if len(sys.argv) > 2 else []
    
    logger.info(f"Command: {command}")
    
    try:
        if command == "search":
            if not args:
                print("❌ Error: 'search' requires a query argument")
                print("   Example: python3 run_agent.py search \"fintech funding\"")
                sys.exit(1)
            query = " ".join(args)
            cmd_search(query)
        
        elif command == "search-and-email":
            if len(args) < 2:
                print("❌ Error: 'search-and-email' requires query and email arguments")
                print('   Example: python3 run_agent.py search-and-email "fintech" user@example.com')
                sys.exit(1)
            query = args[0]
            email = args[1]
            cmd_search_and_email(query, email)
        
        elif command == "preview":
            query = " ".join(args) if args else None
            cmd_preview(query)
        
        elif command == "scheduled":
            cmd_scheduled()
        
        elif command == "invoke":
            if not args:
                print("❌ Error: 'invoke' requires a JSON payload argument")
                print('   Example: python3 run_agent.py invoke \'{"messages":[...]}\' ')
                sys.exit(1)
            payload_json = args[0]
            cmd_invoke_raw(payload_json)
        
        elif command == "metrics":
            cmd_metrics()
        
        elif command == "check-key":
            success = cmd_test_api_key()
            sys.exit(0 if success else 1)
        
        elif command == "check-email":
            success = cmd_test_email()
            sys.exit(0 if success else 1)
        
        else:
            print(f"❌ Unknown command: {command}")
            print("   Run 'python3 run_agent.py help' for usage")
            sys.exit(1)
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
