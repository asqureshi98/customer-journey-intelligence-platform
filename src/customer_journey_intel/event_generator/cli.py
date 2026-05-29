import argparse
import logging
from pathlib import Path

from customer_journey_intel.common.logging import configure_logging
from customer_journey_intel.common.settings import Settings
from customer_journey_intel.event_generator.simulator import JourneySimulator

logger = logging.getLogger(__name__)


def main() -> None:
    settings = Settings()
    configure_logging(settings.log_level)
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
    logger.info(
        "generated customer journey events",
        extra={"cji_event_count": len(lines), "cji_output_path": str(args.output)},
    )


if __name__ == "__main__":
    main()
