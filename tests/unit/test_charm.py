# Copyright 2021 Canonical
# See LICENSE file for licensing details.

from typing import Dict, Optional
import unittest
import unittest.mock as mock
from ops.model import ActiveStatus

from charm import KubernetesInfluxdbCharm, WORKLOAD_CONTAINER
from ops.pebble import ConnectionError
from ops.testing import Harness


class TestKuberneteseInfluxdbCharm(unittest.TestCase):
    def setUp(self) -> None:
        """Setup the harness object."""
        self.harness = Harness(KubernetesInfluxdbCharm)
        self.harness.begin()
        self.harness.add_oci_resource("influxdb2-image")

    def tearDown(self):
        """Cleanup the harness."""
        self.harness.cleanup()

    #
    # Hooks
    #
    def test__on_config_changed(self) -> None:
        self.harness.update_config({"port": "9999"})
        self.assertEqual(self.harness.charm.unit.status, ActiveStatus("Pod is ready"))

    def test__on_config_changed_pebble_api_connection_error_1(self) -> None:
        self.harness.charm.unit.get_container = mock.MagicMock()
        self.harness.charm.unit.get_container.return_value.get_plan = mock.MagicMock(
            side_effect=ConnectionError("connection timeout")
        )
        with self.assertLogs(level="DEBUG") as logger:
            self.harness.update_config({"port": "9999"})
            self.assertIn(
                "DEBUG:charm:The Pebble API is not ready yet. Error message: connection timeout",
                logger.output,
            )
            self.assertNotIn(
                "DEBUG:charm:Pebble plan has already been loaded. No need to update the config.",
                logger.output,
            )

    def test__on_config_changed_pebble_api_connection_error_2(self) -> None:
        self.harness.charm.unit.get_container = mock.MagicMock()
        self.harness.charm.unit.get_container.return_value.get_plan.return_value.to_dict = (
            mock.MagicMock(return_value={})
        )
        self.harness.charm.unit.get_container.return_value.add_layer = mock.MagicMock(
            side_effect=ConnectionError("connection timeout")
        )
        with self.assertLogs(level="DEBUG") as logger:
            self.harness.update_config({"port": "9999"})
            self.assertIn(
                "DEBUG:charm:The Pebble API is not ready yet. Error message: connection timeout",
                logger.output,
            )
            self.assertNotIn(
                "DEBUG:charm:Pebble plan has already been loaded. No need to update the config.",
                logger.output,
            )

    def test__on_config_changed_same_plan(self) -> None:
        self.harness.charm.unit.get_container = mock.MagicMock()
        self.harness.charm.unit.get_container.return_value.get_plan.return_value.to_dict = (
            mock.MagicMock(return_value=self.harness.charm._influxdb2_layer())
        )
        with self.assertLogs(level="DEBUG") as logger:
            self.harness.update_config({"port": "9999"})
            self.assertIn(
                "DEBUG:charm:Pebble plan has already been loaded. No need to update the config.",
                logger.output,
            )
            self.assertNotIn(
                "DEBUG:charm:The Pebble API is not ready yet. Error message: connection timeout",
                logger.output,
            )

    #
    # Test Relations
    #
    def test__grafana_source_data(self, expected_reldata: Optional[Dict] = None) -> None:
        # Initialize values
        interface: str = "grafana-source"
        rel_app: str = "grafana"
        rel_unit: str = "grafana/0"
        rel_data: Dict[str, str] = {}
        expected: Dict[str, str] = {}

        if expected_reldata is None:
            # relation not initialized
            expected_reldata = {key: "" for key in ["private-address", "port", "source-type"]}

        # Initialize unit state (related to grafana)
        rel_id = self.harness.add_relation(interface, rel_app)
        self.harness.add_relation_unit(rel_id, rel_unit)

        # Trigger the -relation-changed hook, which will call the observed event
        self.harness.update_relation_data(rel_id, rel_app, rel_data)

        self.assertIsInstance(rel_id, int)

        # Verify the relation data set by the influxdb2 charm
        relation = self.harness.model.get_relation(interface)

        for key, expected_val in expected.items():
            self.assertEqual(relation.data[self.harness.charm.unit].get(key, ""), expected_val)

    @mock.patch("subprocess.check_output")
    def test__grafana_source_data_leader(self, mock_check_output: mock.MagicMock) -> None:
        mock_check_output.return_value = b"10.0.0.1"
        expected_reldata: Dict[str, str] = {
            "private-address": "10.0.0.1",
            "port": "8086",
            "source-type": "influxdb",
        }
        self.harness.set_leader(True)
        self.test__grafana_source_data(expected_reldata=expected_reldata)

    #
    # Test Helpers
    #
    def test__influxdb2_layer(self) -> None:
        expected = {
            "summary": "influxdb2 layer",
            "description": "pebble config layer for influxdb2",
            "services": {
                "influxdb2": {
                    "override": "replace",
                    "summary": "influxdb2 service",
                    "command": "/entrypoint.sh influxd",
                    "startup": "enabled",
                    "environment": {
                        "DOCKER_INFLUXDB_INIT_MODE": "setup",
                        "DOCKER_INFLUXDB_INIT_USERNAME": "admin",
                        "DOCKER_INFLUXDB_INIT_PASSWORD": "thisisatest123",
                        "DOCKER_INFLUXDB_INIT_ORG": "influxdata",
                        "DOCKER_INFLUXDB_INIT_BUCKET": "default",
                        "DOCKER_INFLUXDB_INIT_RETENTION": "0s",
                        "DOCKER_INFLUXDB_INIT_ADMIN_TOKEN": "asdfasdfasdf",
                        "INFLUXD_BOLT_PATH": "/var/lib/influxdbv2/influxd.bolt",
                        "INFLUXD_ENGINE_PATH": "/var/lib/influxdbv2",
                        "INFLUXD_HTTP_BIND_ADDRESS": ":8086",
                    },
                }
            },
        }

        self.assertEqual(set(self.harness.charm._influxdb2_layer()), set(expected))

    def test__is_running(self) -> None:
        container = self.harness.charm.unit.get_container(WORKLOAD_CONTAINER)
        service_not_running = self.harness.charm._is_running(container, "influxd")
        self.assertFalse(service_not_running)


if __name__ == "__main__":
    unittest.main()
