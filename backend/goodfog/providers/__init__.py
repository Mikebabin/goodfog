class ProviderError(Exception):
    """Upstream fetch or parse failed; the poller keeps the previous snapshot."""
