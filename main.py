import argparse
import logging
import sys

from rich.logging import RichHandler

from utils.config import Settings


def main() -> None:
    parser = argparse.ArgumentParser(description="Instagram account management tools")
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Set logging level",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    unfollow_parser = subparsers.add_parser(
        "unfollow-inactive",
        help="Unfollow users who haven't posted in a given period",
    )
    unfollow_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate without actually unfollowing anyone",
    )
    unfollow_parser.add_argument(
        "--months",
        type=int,
        default=12,
        help="Unfollow users inactive for this many months (default: 12)",
    )
    unfollow_parser.add_argument(
        "--workers",
        type=int,
        default=5,
        help="Number of parallel workers (default: 5)",
    )
    unfollow_parser.add_argument(
        "--only-non-followers",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Only unfollow users who don't follow you back (default: True)",
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(message)s",
        handlers=[RichHandler(rich_tracebacks=True)],
    )

    settings = Settings()

    try:
        if args.command == "unfollow-inactive":
            from scripts.unfollow_inactive import run

            run(
                settings,
                dry_run=args.dry_run,
                months=args.months,
                workers=args.workers,
                only_non_followers=args.only_non_followers,
            )
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        logging.exception("Unhandled error: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
