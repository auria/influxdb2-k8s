import logging
from typing import Dict


import pytest
from pytest_operator.plugins import OpsTest


log = logging.getLogger(__name__)


@pytest.mark.abort_on_fail
async def test_build_and_deploy(ops_test: OpsTest) -> None:
    bundle = ops_test.render_bundle(
        "tests/data/bundle.yaml",
        master_charm=await ops_test.build_charm(".")
    )
    await ops_test.model.deploy(bundle, trust=True)
    await ops_test.model.wait_for_idle(wait_for_active=True, timeout=60 * 10)


async def test_status_messages(ops_test: OpsTest) -> None:
    """Validate that the status messages are correct."""
    expected_messages: Dict[str, str] = {
        "influxdb2-k8s": "Pod is ready",
    }
    for app, message in expected_messages.items():
        for unit in ops_test.model.applications[app].units:
            assert unit.workload_status_message == message
