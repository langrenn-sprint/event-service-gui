"""Contract test cases for live."""
from typing import Any

import pytest
import requests


@pytest.mark.contract
def test_live(http_service: Any) -> None:
    """Should return status 200 and html."""
    url = f"{http_service}/live"
    response = requests.get(url)

    assert response.status_code == 200
    assert response.headers["content-type"] == "text/html; charset=utf-8"

    assert len(response.text) > 0
