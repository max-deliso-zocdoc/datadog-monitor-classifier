"""Main entry point for the Datadog downloader."""
import logging

from .client import DatadogClient
from .logging_config import setup_logging

logger = logging.getLogger(__name__)


def main():
    """Main function to run the Datadog downloader."""
    setup_logging()
    logger.info("Starting Datadog downloader")

    client = DatadogClient()
    metrics = client.get_metrics_list()
    logger.info(f"Found {len(metrics)} metrics")

    for metric in metrics:
        logger.info(f"Metric: {metric}")


if __name__ == "__main__":
    main()