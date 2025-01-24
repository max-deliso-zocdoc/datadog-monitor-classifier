"""Main entry point for the Datadog downloader."""
import logging
import argparse
from collections import defaultdict
from datetime import datetime, timedelta
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeRemainingColumn
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from .client import DatadogClient
from .db import MonitorDB
from .logging_config import setup_logging

logger = logging.getLogger(__name__)
console = Console()

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Download and analyze Datadog monitors.")
    parser.add_argument(
        "--max-fetch",
        type=int,
        help="Maximum number of monitors to fetch. If not specified, fetches all monitors.",
        default=None
    )
    parser.add_argument(
        "--force-refresh",
        action="store_true",
        help="Force refresh all monitors regardless of last fetch time."
    )
    return parser.parse_args()

def format_notification_targets(notify_targets):
    """Format notification targets into a readable string."""
    if not notify_targets:
        return "No notifications configured"

    # Separate alert and recovery notifications
    alert_notifications = [n for n in notify_targets if not n.is_recovery]
    recovery_notifications = [n for n in notify_targets if n.is_recovery]

    result = []
    if alert_notifications:
        result.append("Alert notifications:")
        for notify in alert_notifications:
            result.append(f"    {notify.target} - Context: {notify.context}")

    if recovery_notifications:
        if alert_notifications:  # Add spacing if we had alert notifications
            result.append("")
        result.append("Recovery notifications:")
        for notify in recovery_notifications:
            result.append(f"    {notify.target} - Context: {notify.context}")

    return "\n".join(result)

def main():
    """Main function to run the Datadog downloader."""
    setup_logging()
    args = parse_args()

    # Create a fancy title
    title = Text("Datadog Monitor Downloader", style="bold magenta")
    console.print(Panel(title, border_style="blue"))

    client = DatadogClient()
    db = MonitorDB(fetch_interval=timedelta(days=1))

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeRemainingColumn(),
        console=console,
        transient=True
    ) as progress:
        # Fetch monitors with progress
        fetch_task = progress.add_task("Fetching monitors from Datadog...", total=None)
        monitors = client.get_monitors(max_fetch=args.max_fetch)
        progress.update(fetch_task, total=1, completed=1)

        # Show total monitors found
        console.print(f"[green]Found {len(monitors)} monitors in Datadog[/green]")

        # Get monitors that need refresh
        existing_monitor_ids = db.get_all_monitor_ids()
        # Force refresh if database is empty or --force-refresh is set
        monitors_to_refresh = {m.id for m in monitors} if not existing_monitor_ids or args.force_refresh else db.get_monitors_needing_refresh()
        console.print(f"[yellow]Found {len(monitors_to_refresh)} monitors that need to be refreshed[/yellow]")

        # Store monitors with progress
        refresh_task = progress.add_task(
            "Refreshing monitors...",
            total=len(monitors_to_refresh)
        )

        # Store only monitors that need refresh
        active_monitor_ids = []
        refreshed_count = 0
        for monitor in monitors:
            active_monitor_ids.append(monitor.id)
            if monitor.id in monitors_to_refresh:
                try:
                    db.upsert_monitor(monitor)
                    refreshed_count += 1
                    progress.update(refresh_task, advance=1)
                except Exception as e:
                    logger.error(f"Failed to store monitor {monitor.id}: {str(e)}")

        # Mark inactive monitors
        if active_monitor_ids:
            db.mark_inactive_monitors(active_monitor_ids)

        # Get project statistics
        project_counts = db.get_monitor_count_by_project()

        # Print final statistics in a panel
        stats = [
            Text("Monitor Statistics", style="bold blue"),
            Text(f"Total Monitors in Datadog: {len(monitors)}", style="green"),
            Text(f"Monitors Refreshed: {refreshed_count}", style="yellow"),
            Text(f"Total Active Monitors in DB: {sum(project_counts.values())}", style="cyan"),
            Text("\nMonitors by Project:", style="bold magenta")
        ]

        for project, count in project_counts.items():
            stats.append(Text(f"  {project}: {count} monitors", style="bright_blue"))

        console.print(Panel("\n".join(str(s) for s in stats), border_style="blue"))

if __name__ == "__main__":
    main()