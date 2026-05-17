import logging
import random
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from copy import deepcopy
from datetime import datetime, timedelta, timezone

from rich.console import Console
from rich.progress import BarColumn, Progress, TaskProgressColumn, TextColumn, TimeRemainingColumn
from rich.prompt import Confirm
from rich.table import Table

from utils.config import Settings
from utils.instagram_client import InstagramClient

logger = logging.getLogger(__name__)
console = Console()

MIN_DELAY = 0.5
MAX_DELAY = 2.0


def _check_user(uid_str, user_info, settings, session_data, cutoff_date):
    local_client = InstagramClient(settings, load_session=False)
    local_client.client.set_settings(deepcopy(session_data))

    user_id = int(uid_str)
    username = user_info.username
    full_name = user_info.full_name or ""

    time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))

    try:
        medias = local_client.rate_limited_call(local_client.get_user_medias, user_id, 1)
    except Exception:
        return ("error", username, full_name, None)

    if not medias:
        return ("skip_no_posts", username, full_name, None)

    post_date = medias[0].taken_at.replace(tzinfo=timezone.utc)
    if post_date > cutoff_date:
        return ("skip_active", username, full_name, post_date)

    return ("unfollow", username, full_name, post_date)


def _unfollow_user(uid_str, username, full_name, settings, session_data):
    local_client = InstagramClient(settings, load_session=False)
    local_client.client.set_settings(deepcopy(session_data))

    user_id = int(uid_str)
    time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))

    try:
        local_client.rate_limited_call(local_client.unfollow, user_id)
        return ("unfollowed", username, full_name)
    except Exception:
        return ("error", username, full_name)


def run(
    settings: Settings,
    dry_run: bool = False,
    months: int = 12,
    workers: int = 5,
    only_non_followers: bool = True,
) -> None:
    main_client = InstagramClient(settings)
    main_client.login()

    cutoff_date = datetime.now(timezone.utc) - timedelta(days=months * 30)
    console.print(f"Looking for users inactive since [bold yellow]{cutoff_date.date()}[/]")

    following = main_client.rate_limited_call(main_client.get_following)
    items = list(following.items())

    if only_non_followers:
        followers = main_client.rate_limited_call(main_client.get_followers)
        follower_ids = set(followers.keys())
        before = len(items)
        items = [(uid, info) for uid, info in items if uid not in follower_ids]
        skipped_mutuals = before - len(items)
        console.print(f"You follow [bold]{before}[/] users, [bold]{skipped_mutuals}[/] follow you back — checking the remaining [bold]{len(items)}[/]\n")
    else:
        console.print(f"You follow [bold]{len(items)}[/] users\n")

    session_data = main_client.client.get_settings()

    skipped_active = skipped_no_posts = errors = 0
    to_unfollow = []

    progress = Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeRemainingColumn(),
        console=console,
    )

    with progress:
        task = progress.add_task("Checking following...", total=len(items))

        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(
                    _check_user, uid, info, settings, session_data, cutoff_date
                ): uid
                for uid, info in items
            }

            for future in as_completed(futures):
                uid = futures[future]
                action, username, full_name, post_date = future.result()

                if action == "unfollow":
                    to_unfollow.append((uid, username, full_name, post_date))
                elif action == "skip_active":
                    skipped_active += 1
                elif action == "skip_no_posts":
                    skipped_no_posts += 1
                    console.print(f"  [yellow]⚠[/] @{username} ({full_name}) — no posts found, skipping")
                elif action == "error":
                    errors += 1

                progress.advance(task)

    if not dry_run and to_unfollow:
        table = Table(title="Accounts to unfollow")
        table.add_column("#", style="dim")
        table.add_column("Username")
        table.add_column("Full Name")
        table.add_column("Last Post")

        for i, (uid, username, full_name, post_date) in enumerate(to_unfollow, 1):
            table.add_row(
                str(i),
                f"@{username}",
                full_name or "",
                post_date.strftime("%Y-%m-%d") if post_date else "N/A",
            )

        console.print()
        console.print(table)
        confirmed = Confirm.ask(f"\nProceed with unfollowing [bold]{len(to_unfollow)}[/] accounts?")
        if not confirmed:
            console.print("[yellow]Aborted by user[/]")
            return

    if not dry_run and to_unfollow:
        console.print()
        unfollowed = 0
        errors = 0

        for uid_str, username, full_name, post_date in to_unfollow:
            result, name, _ = _unfollow_user(uid_str, username, full_name, settings, session_data)

            if result == "unfollowed":
                unfollowed += 1
                days = (datetime.now(timezone.utc) - post_date).days
                console.print(
                    f"  [red]✗[/] @{username} ({full_name}) — last post: "
                    f"{post_date.strftime('%Y-%m-%d')} ([bold]{days}[/] days ago)"
                )
            else:
                errors += 1

        console.print("\n[bold]Summary:[/]")
        console.print(f"  Unfollowed: [bold]{unfollowed}[/]")
        console.print(f"  Errors: [bold]{errors}[/]")
    else:
        for uid, username, full_name, post_date in to_unfollow:
            days = (datetime.now(timezone.utc) - post_date).days
            console.print(
                f"  [red]✗[/] @{username} ({full_name}) — last post: "
                f"{post_date.strftime('%Y-%m-%d')} ([bold]{days}[/] days ago)"
            )

        console.print(f"\n[bold]Summary:[/]")
        console.print(f"  Would unfollow: [bold]{len(to_unfollow)}[/]")
        console.print(f"  Skipped (active): [bold]{skipped_active}[/]")
        console.print(f"  Skipped (no posts): [bold]{skipped_no_posts}[/]")
        console.print(f"  Errors: [bold]{errors}[/]")

        if not to_unfollow:
            console.print("\n[green]No accounts to unfollow![/]")
        elif dry_run:
            console.print("\n[italic]Dry run — no accounts were actually unfollowed[/]")
