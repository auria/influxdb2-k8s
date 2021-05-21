# Copyright 2021 Canonical
# See LICENSE file for licensing details.

from typing import Dict
import unittest
import unittest.mock as mock

from ops.testing import Harness
from charm import KubernetesInfluxdbCharm


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
    # Test Relations
    #
    @mock.patch("subprocess.check_output")
    def test__grafana_source_data(self, mock_check_output: mock.MagicMock) -> None:
        # Initialize values
        interface: str = "grafana-source"
        rel_app: str = "grafana"
        rel_unit: str = "grafana/0"
        rel_data: Dict[str, str] = {}
        mock_check_output.return_value = b"10.0.0.1"

        # Initialize unit state (related to grafana)
        self.harness.set_leader(True)
        rel_id = self.harness.add_relation(interface, rel_app)
        self.harness.add_relation_unit(rel_id, rel_unit)

        # Trigger the -relation-changed hook, which will call the observed event
        self.harness.update_relation_data(rel_id, rel_app, rel_data)

        self.assertIsInstance(rel_id, int)

        # Verify the relation data set by the influxdb2 charm
        relation = self.harness.model.get_relation("grafana-source")
        self.assertEqual(relation.data[self.harness.charm.unit].get("private-address", ""), "10.0.0.1")
        self.assertEqual(relation.data[self.harness.charm.unit].get("port", ""), "8086")
        self.assertEqual(relation.data[self.harness.charm.unit].get("source-type", ""), "influxdb")

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

if __name__ == "__main__":
    unittest.main()