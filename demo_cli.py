"""Quick command-line demo.

Usage:
    python demo_cli.py "get me wireless earbuds under 2000 rupees"
"""
import sys

from dotenv import load_dotenv

load_dotenv()

from cartpilot.agent import run_agent  # noqa: E402
from cartpilot import payments  # noqa: E402


def main():
    if len(sys.argv) < 2:
        print('Usage: python demo_cli.py "your buyer request here"')
        sys.exit(1)

    buyer_intent = " ".join(sys.argv[1:])
    print(f"Buyer: {buyer_intent}\n")
    print(f"Payment mode: {'LIVE (Razorpay test-mode)' if payments.is_live_mode() else 'MOCK'}\n")

    result = run_agent(buyer_intent)

    print("--- Agent trace ---")
    for step in result["trace"]:
        print(f"  → {step['tool']}({step['args']})")
        print(f"     result: {step['result']}")

    print("\n--- Final answer ---")
    print(result["answer"])
    print(f"\n(session_id={result['session_id']} — see audit_log.jsonl for the full audit trail)")


if __name__ == "__main__":
    main()
