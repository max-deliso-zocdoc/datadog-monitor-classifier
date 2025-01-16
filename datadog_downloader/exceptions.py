"""Custom exceptions for the Datadog downloader."""


class DatadogDownloaderError(Exception):
    """Base exception for all Datadog downloader errors."""

    pass


class ConfigurationError(DatadogDownloaderError):
    """Raised when there's an issue with the configuration."""

    pass


class APIError(DatadogDownloaderError):
    """Raised when there's an error communicating with the Datadog API."""

    pass
