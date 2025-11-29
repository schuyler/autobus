import pytest
import autobus


@pytest.fixture(autouse=True)
def reset_autobus():
    """Reset the global autobus client before each test."""
    autobus._reset_client()
    yield
    autobus._reset_client()
