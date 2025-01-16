"""Datadog API client implementation."""

import logging
from datadog_api_client import ApiClient, Configuration
from datadog_api_client.v1.api.metrics_api import MetricsApi

from .config import settings
from .exceptions import APIError

logger = logging.getLogger(__name__)


class DatadogClient:
    """Client for interacting with the Datadog API."""

    def __init__(self):
        """Initialize the Datadog client with configuration from environment."""
        configuration = Configuration(
            host=f"https://api.{str(settings.datadog_site)}",
            api_key={
                "apiKeyAuth": str(settings.datadog_api_key),
                "appKeyAuth": str(settings.datadog_app_key),
            },
        )
        self.api_client = ApiClient(configuration)
        self.metrics_api = MetricsApi(self.api_client)
        logger.info("Initialized Datadog client")

    def get_metrics_list(self):
        """Get list of active metrics from Datadog."""
        try:
            logger.info("Fetching metrics list from Datadog")
            response = self.metrics_api.list_metrics(q="")
            logger.debug(f"Raw response: {response}")
            metrics = response.metrics
            logger.info(f"Successfully retrieved {len(metrics)} metrics")
            return metrics
        except Exception as e:
            logger.error(f"Failed to fetch metrics: {str(e)}", exc_info=True)
            raise APIError(f"Failed to fetch metrics: {str(e)}")
