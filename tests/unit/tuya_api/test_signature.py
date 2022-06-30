"""Test for Tuya signing."""
import pytest

from custom_components.tuya_smart_watering.tuya_api import Signature


@pytest.mark.parametrize(
    argnames="access_token, query, result",
    argvalues=[
        (
            "",
            "/v1.0/token?grant_type=1",
            "9E48A3E93B302EEECC803C7241985D0A34EB944F40FB573C7B5C2A82158AF13E",
        ),
        (
            "3f4eda2bdec17232f67c0b188af3eec1",
            "/v2.0/apps/schema/users?page_no=1&page_size=50",
            "AE4481C692AA80B25F3A7E12C3A5FD9BBF6251539DD78E565A1A72A508A88784",
        ),
    ],
    ids=["without token", "with token"],
)
def test_signature(
    client_id, secret, timestamp, uuid, method, parameters, access_token, query, result
):
    """Test signature generation."""
    assert (
        Signature.get_sign(
            client_id=client_id,
            secret=secret,
            timestamp=timestamp,
            uuid=uuid,
            method=method,
            parameters=parameters,
            access_token=access_token,
            request=query,
            body="",
        )
        == result
    )
