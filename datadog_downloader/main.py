"""Main entry point for the Datadog downloader."""
import logging
from collections import defaultdict
from datetime import datetime, timedelta

from .client import DatadogClient
from .db import MonitorDB
from .logging_config import setup_logging

logger = logging.getLogger(__name__)


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
    logger.info("Starting Datadog downloader")

    client = DatadogClient()
    db = MonitorDB(fetch_interval=timedelta(days=1))

    logger.info("Fetching monitors...")
    monitors = client.get_monitors()
    logger.info(f"Found {len(monitors)} monitors in Datadog")

    # Get monitors that need refresh
    monitors_to_refresh = db.get_monitors_needing_refresh()
    logger.info(f"Found {len(monitors_to_refresh)} monitors that need to be refreshed")

    # Store only monitors that need refresh
    active_monitor_ids = []
    refreshed_count = 0
    for monitor in monitors:
        active_monitor_ids.append(monitor.id)
        if monitor.id in monitors_to_refresh:
            try:
                db.upsert_monitor(monitor)
                refreshed_count += 1
            except Exception as e:
                logger.error(f"Failed to store monitor {monitor.id}: {str(e)}", exc_info=True)

    # Mark monitors not in this fetch as inactive
    if active_monitor_ids:
        db.mark_inactive_monitors(active_monitor_ids)

    # Get statistics from database
    project_counts = db.get_monitor_count_by_project()

    # Print summary
    logger.info("\nMonitor Statistics:")
    logger.info(f"Total Monitors in Datadog: {len(monitors)}")
    logger.info(f"Monitors Refreshed: {refreshed_count}")
    logger.info(f"Total Active Monitors in DB: {sum(project_counts.values())}")
    logger.info("\nMonitors by Project:")
    for project, count in sorted(project_counts.items()):
        logger.info(f"  {project.upper()}: {count} monitors")


if __name__ == "__main__":
    main()