import argparse
from pathlib import Path

from customer_journey_intel.event_generator.simulator import JourneySimulator


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic ecommerce journey events.")
    parser.add_argument(
        "--journeys", type=int, default=10, help="Number of customer journeys to emit."
    )
    parser.add_argument("--output", type=Path, default=Path("data/sample_events.jsonl"))
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    simulator = JourneySimulator(seed=args.seed)
    lines = simulator.generate_json_lines(journey_count=args.journeys)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {len(lines)} events to {args.output}")


if __name__ == "__main__":
    main()
