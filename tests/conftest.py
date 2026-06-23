import os

import pytest


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if os.getenv("EXTRACTORY_ENABLE_LIVE_TESTS") == "true":
        return
    skip_live = pytest.mark.skip(reason="Set EXTRACTORY_ENABLE_LIVE_TESTS=true to run live tests")
    for item in items:
        if "live" in item.keywords:
            item.add_marker(skip_live)
