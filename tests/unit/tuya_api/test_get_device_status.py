"""Test fetching device status."""

import os

import pytest

from custom_components.tuya_smart_watering.tuya_api import TuyaApi


@pytest.mark.asyncio
async def test_get_device():
    """Get device status via TuyaAPI."""
    tuya_instance = TuyaApi(
        client_id=os.environ["CLIENT_ID"],
        secret=os.environ["SECRET"],
        server="openapi.tuyaeu.com",
    )

    print("\n")
    print(await tuya_instance.status(device_id=os.environ["DEVICE_ID"]))


@pytest.mark.asyncio
async def test_get_device_schema():
    """Get device status via TuyaAPI."""
    tuya_instance = TuyaApi(
        client_id=os.environ["CLIENT_ID"],
        secret=os.environ["SECRET"],
        server="openapi.tuyaeu.com",
    )

    print("\n")
    print(await tuya_instance.schema(device_id=os.environ["DEVICE_ID"]))
