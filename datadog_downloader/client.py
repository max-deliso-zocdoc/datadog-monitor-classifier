"""Datadog API client implementation."""

import logging
import re
from dataclasses import dataclass
from typing import List, Dict, Optional
from datadog_api_client import ApiClient, Configuration
from datadog_api_client.v1.api.metrics_api import MetricsApi
from datadog_api_client.v1.api.monitors_api import MonitorsApi

from .config import settings
from .exceptions import APIError

logger = logging.getLogger(__name__)


@dataclass
class NotificationTarget:
    """Represents a notification target with context."""
    target: str  # The @ mention
    context: str  # The surrounding message context
    is_recovery: bool = False  # Whether this is a recovery notification


@dataclass
class Monitor:
    """Represents a Datadog monitor with classification information."""
    id: int
    name: str
    message: str
    tags: List[str]
    notify_targets: List[NotificationTarget]  # Enhanced notification targets
    project: Optional[str] = None
    type: str = ""
    query: str = ""
    priority: str = "normal"  # Priority/severity of the monitor
    state: str = ""  # Current state of the monitor
    options: Dict = None  # Monitor options
    overall_state: str = ""  # Overall state including all groups
    matching_downtimes: List[Dict] = None  # Active downtimes


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
        self.monitors_api = MonitorsApi(self.api_client)
        logger.info("Initialized Datadog client")

    def get_metrics_list(self) -> List[str]:
        """Get list of all available metrics."""
        try:
            response = self.metrics_api.list_metrics(q="")
            if hasattr(response, 'metrics'):
                return response.metrics
            elif hasattr(response, 'results'):
                return response.results
            else:
                raise APIError("Unexpected response structure - no metrics or results found")
        except Exception as e:
            logger.error(f"Failed to fetch metrics: {str(e)}", exc_info=True)
            raise APIError(f"Failed to fetch metrics: {str(e)}")

    def _parse_notifications(self, message: str) -> List[NotificationTarget]:
        """Parse notification targets from monitor message with context."""
        if not message:
            return []

        notify_targets = []

        # Split message into alert and recovery sections
        sections = message.split("{{#is_recovery}}")
        alert_message = sections[0]
        recovery_message = sections[1] if len(sections) > 1 else ""

        # Helper function to extract notifications with context
        def extract_notifications(text: str, is_recovery: bool) -> None:
            lines = text.split('\n')
            for line in lines:
                # Find all @mentions in the line
                mentions = re.finditer(r'(@\S+)', line)
                for match in mentions:
                    target = match.group(1)
                    # Get some context around the @mention (the whole line for context)
                    notify_targets.append(NotificationTarget(
                        target=target,
                        context=line.strip(),
                        is_recovery=is_recovery
                    ))

        # Extract from both alert and recovery sections
        extract_notifications(alert_message, False)
        if recovery_message:
            extract_notifications(recovery_message, True)

        return notify_targets

    def _to_dict(self, obj) -> dict:
        """Safely convert an object to a dictionary."""
        if isinstance(obj, dict):
            return obj

        # If it's a datadog API object, try to access its _data_store
        if hasattr(obj, '_data_store'):
            data = dict(obj._data_store)
            # Convert type to string if it exists
            if 'type' in data:
                data['type'] = str(data['type'])
            return data

        # Fallback to getting all attributes
        result = {}
        for attr in dir(obj):
            if not attr.startswith('_') and not callable(getattr(obj, attr)):
                try:
                    value = getattr(obj, attr)
                    # Convert type to string if it's the type attribute
                    if attr == 'type':
                        value = str(value)
                    result[attr] = value
                except Exception:
                    continue
        return result

    def _get_monitor_severity(self, monitor_dict: dict) -> str:
        """Determine monitor severity from its options and tags."""
        # Check priority tag first
        for tag in monitor_dict.get('tags', []):
            if tag.startswith("priority:"):
                return tag.split(":", 1)[1]

        # Check options safely
        options = monitor_dict.get('options', {})
        if isinstance(options, dict):
            thresholds = options.get('thresholds', {})
            if isinstance(thresholds, dict):
                if thresholds.get('critical') is not None:
                    return "high"
                elif thresholds.get('warning') is not None:
                    return "medium"

        return "normal"

    def get_monitors(self) -> List[Monitor]:
        """Get all monitors and classify them."""
        try:
            logger.info("Calling list_monitors API endpoint...")
            response = self.monitors_api.list_monitors()

            # Debug the raw response
            logger.info(f"API Response type: {type(response)}")
            logger.info(f"Number of monitors in response: {len(response) if response else 0}")

            if not response:
                logger.warning("Received empty response from Datadog API")
                return []

            monitors = []

            for i, monitor in enumerate(response):
                try:
                    logger.debug(f"Processing monitor {i+1}/{len(response)}")
                    # Convert monitor to dictionary for safer attribute access
                    monitor_dict = self._to_dict(monitor)
                    logger.debug(f"Monitor basic info - ID: {monitor_dict.get('id')}, Name: {monitor_dict.get('name')}")

                    # Get detailed monitor information
                    try:
                        logger.debug(f"Fetching detailed information for monitor {monitor_dict.get('id')}")
                        details = self.monitors_api.get_monitor(monitor_dict['id'])
                        details_dict = self._to_dict(details)
                        logger.debug("Successfully fetched monitor details")
                    except Exception as e:
                        logger.warning(f"Failed to get details for monitor {monitor_dict.get('id')}: {str(e)}")
                        details_dict = monitor_dict

                    # Ensure type is a string
                    if 'type' in details_dict:
                        details_dict['type'] = str(details_dict['type'])

                    # Create Monitor object with enhanced information
                    mon = Monitor(
                        id=details_dict.get('id', 0),
                        name=details_dict.get('name', ''),
                        message=details_dict.get('message', ''),
                        tags=details_dict.get('tags', []),
                        notify_targets=self._parse_notifications(details_dict.get('message', '')),
                        type=str(details_dict.get('type', '')),  # Convert type to string
                        query=details_dict.get('query', ''),
                        priority=self._get_monitor_severity(details_dict),
                        state=details_dict.get('state', ''),
                        options=details_dict.get('options', {}),
                        overall_state=details_dict.get('overall_state', ''),
                        matching_downtimes=details_dict.get('matching_downtimes', [])
                    )

                    # Classify project based on tags and name
                    mon.project = self._classify_project(mon)
                    monitors.append(mon)
                    logger.debug(f"Successfully processed monitor {monitor_dict.get('id')}")
                except Exception as e:
                    logger.warning(f"Failed to process monitor: {str(e)}", exc_info=True)
                    continue

            logger.info(f"Successfully processed {len(monitors)} monitors")
            return monitors
        except Exception as e:
            logger.error(f"Failed to fetch monitors: {str(e)}", exc_info=True)
            raise APIError(f"Failed to fetch monitors: {str(e)}")

    def _classify_project(self, monitor: Monitor) -> str:
        """Classify which project a monitor belongs to based on its tags and name."""
        # Look for project tags
        for tag in monitor.tags or []:
            if tag.startswith("project:"):
                return tag.split(":", 1)[1]
            if tag.startswith("service:"):
                return tag.split(":", 1)[1]
            if tag.startswith("team:"):
                return tag.split(":", 1)[1]

        # Look for common project names in the monitor name
        name_lower = monitor.name.lower()
        for keyword in ["api", "web", "frontend", "backend", "db", "database", "service"]:
            if keyword in name_lower:
                return keyword

        return "unknown"
