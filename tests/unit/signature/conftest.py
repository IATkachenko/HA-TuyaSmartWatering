"""pytest configuration."""
import pytest


@pytest.fixture()
def client_id():
    """client_id."""
    return "1KAD46OrT9HafiKdsXeg"


@pytest.fixture()
def secret():
    """Secret for sgnature."""
    return "4OHBOnWOqaEC1mWXOpVL3yV50s0qGSRC"


@pytest.fixture()
def timestamp():
    """Timestamp."""
    return 1588925778000


@pytest.fixture()
def uuid():
    """UUID or nonce."""
    return "5138cc3a9033d69856923fd07b491173"


@pytest.fixture()
def method():
    """Request method."""
    return "GET"


@pytest.fixture()
def parameters():
    """Request parameters."""
    return {
        "area_id": "29a33e8796834b1efa6",
        "call_id": "8afdb70ab2ed11eb85290242ac130003",
    }
