#!/usr/bin/env python3
# Copyright 2021 Canonical
# See LICENSE file for licensing details.

import logging
import subprocess

from ops.charm import CharmBase, HookEvent, RelationEvent

from ops.main import main
from ops.model import ActiveStatus, Container, ModelError
from ops.pebble import APIError, ConnectionError, Layer, ServiceStatus

logger = logging.getLogger(__name__)

WORKLOAD_CONTAINER = "influxdb2"


class KubernetesInfluxdbCharm(CharmBase):
    """Charm to run Influxdb2 on Kubernetes."""

    def __init__(self, *args):
        super().__init__(*args)

        # self.framework.observe(self.on.install, self._on_install)
        self.framework.observe(self.on.influxdb2_pebble_ready, self._on_config_changed)
        self.framework.observe(self.on.config_changed, self._on_config_changed)

        # Disabled until LP#1926568 is fixed
        # self.framework.observe(self.on.stop, self._on_stop)

        # Relations
        self.framework.observe(
            self.on["grafana-source"].relation_changed, self._on_grafana_source_relation_changed
        )

    def _on_config_changed(self, event: HookEvent) -> None:
        """Handle the pebble_ready event for the influxdb2 container."""

        container = self.unit.get_container(WORKLOAD_CONTAINER)
        try:
            plan = container.get_plan().to_dict()
        except (APIError, ConnectionError) as error:
            logger.debug(f"The Pebble API is not ready yet. Error message: {error}")
            event.defer()
            return

        logger.debug(f"[*] container plan => {plan}")
        pebble_config = Layer(raw=self._influxdb2_layer())
        # If there's no new config, do nothing
        if plan.get("services", {}) == pebble_config.to_dict()["services"]:
            logger.debug("Pebble plan has already been loaded. No need to update the config.")
            return

        try:
            # Add out initial config layer
            container.add_layer("influxdb2", pebble_config, combine=True)
        except (APIError, ConnectionError) as error:
            logger.debug(f"The Pebble API is not ready yet. Error message: {error}")
            event.defer()
            return

        # If the service is INACTIVE, then skip this step
        if self._is_running(container, WORKLOAD_CONTAINER):
            container.stop(WORKLOAD_CONTAINER)
        container.start(WORKLOAD_CONTAINER)
        self.unit.status = ActiveStatus("Pod is ready")

    #
    # Relations
    #
    def _on_grafana_source_relation_changed(self, event: RelationEvent) -> None:
        """Provide Grafana with data source information."""
        # Only the leader unit can share details
        # In the future, a K8s service should expose all the units in HA mode
        if not self.model.unit.is_leader():
            return

        relation_data = {
            "private-address": subprocess.check_output(["unit-get", "private-address"])
            .decode()
            .strip(),
            "port": "8086",
            "source-type": "influxdb",
        }
        event.relation.data[self.unit].update(relation_data)

    #
    # Helpers
    #
    def _influxdb2_layer(self) -> dict:
        """Returns initial Pebble configuration layer for Influxdb2."""
        return {
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

    def _is_running(self, container: Container, service: str) -> bool:
        """Helper method to determine if a given service is running in a given container"""
        try:
            svc = container.get_service(service)
            return svc.current == ServiceStatus.ACTIVE
        except ModelError:
            return False


if __name__ == "__main__":
    main(KubernetesInfluxdbCharm)
