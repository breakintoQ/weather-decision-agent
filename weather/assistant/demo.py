import argparse
import json
from dataclasses import asdict

from assistant.api.app import handle_query


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the weather decision assistant for a single query."
    )
    parser.add_argument("query", help="Natural-language weather query")
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the full assistant state as JSON.",
    )
    args = parser.parse_args()

    state = handle_query(args.query)
    if args.json:
        print(json.dumps(asdict(state), ensure_ascii=False, indent=2))
        return

    print(f"Query: {args.query}")
    print(f"Decision: {state.final_answer.decision}")
    print(f"Summary: {state.final_answer.summary}")
    if state.final_answer.tips:
        print("Tips:")
        for tip in state.final_answer.tips:
            print(f"- {tip}")
            
if __name__ == "__main__":
    main()
