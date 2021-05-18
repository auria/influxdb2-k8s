#!/usr/bin/env python3
# Copyright 2021 Alvaro
# See LICENSE file for licensing details.

import logging

import kubernetes
from ops.charm import CharmBase
# from ops.charm import CharmBase, InstallEvent, PebbleReadyEvent, StopEvent
from ops.framework import EventBase, StoredState
from ops.main import main
from ops.model import ActiveStatus, BlockedStatus, Container, MaintenanceStatus, ModelError
from ops.pebble import APIError, ConnectionError, ServiceStatus, Layer

logger = logging.getLogger(__name__)

WORKLOAD_CONTAINER = "influxdb2"


class KubernetesInfluxdbCharm(CharmBase):
    """Charm to run Influxdb2 on Kubernetes."""

    _authed = False
    _stored = StoredState()

    def __init__(self, *args):
        super().__init__(*args)

        # self.framework.observe(self.on.install, self._on_install)
        self.framework.observe(self.on.config_changed, self._on_config_changed)

        # Disabled until LP#1926568 is fixed
        # self.framework.observe(self.on.stop, self._on_stop)
   
    # def _on_install(self, event: InstallEvent) -> None:
    #     if not self.k8s_auth():
    #         event.defer()
    #         return
    #     self._create_additional_resources()

    # def _on_stop(self, event: StopEvent) -> None:
    #     """Cleanup Kubernetes resources."""
    #     # Authenticate with the Kubernetes API
    #     self.k8s_auth()
    #     # Get an API client
    #     cl = kubernetes.client.ApiClient()
    #     core_api = kubernetes.client.CoreV1Api(cl)
    #     # auth_api = kubernetes.client.RbacAuthorizationV1Api(cl)

    #     logger.debug("Cleaning up Kubernetes resources")
    #     # Remove some secrets
    #     core_api.delete_namespaced_secret(namespace=self.model.name, name="influxdb2-auth")
    #     # Remove the service account
    #     # core_api.delete_namespaced_service_account(namespace=self.model.name, "influxdb2")
    #     # Remove the service
    #     core_api.delete_namespaced_service(namespace=self.model.name, name="influxdb2")

    def _on_config_changed(self, event: EventBase) -> None:
        """Handle the pebble_ready event for the influxdb2 container."""
        # if not self.k8s_auth():
        #     event.defer()
        #     return

        # if not self._check_patched():
        #     self._patch_influxdb2_stateful_set()
        #     self.unit.status = MaintenanceStatus("Waiting for changes to apply")

        container = self.unit.get_container(WORKLOAD_CONTAINER)
        plan = container.get_plan().to_dict()
        logger.debug(f"[*] container plan => {plan}")
        pebble_config = Layer(raw=self._influxdb2_layer())
        # # If there's no new config, do nothing
        # if plan["services"] == pebble_config["services"]:
        #     self.unit.status = ActiveStatus("influxdb2 noop")
        #     return

        try:
            # Add out initial config layer
            container.add_layer("influxdb2", pebble_config, combine=True)
        except (APIError, ConnectionError) as error:
            logger.debug(f"The Pebble API is not ready yet. Error message: {error}")
            return

        # If the service is INACTIVE, then skip this step
        if self._is_running(container, WORKLOAD_CONTAINER):
            container.stop(WORKLOAD_CONTAINER)
        container.start(WORKLOAD_CONTAINER)
        self.unit.status = ActiveStatus("Unit is ready")
    
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
    
    def _check_patched(self) -> bool:
        """Slightly naive check to see if the StatefulSet has already been patched."""
        # Auth with the k8s api to check if the StatefulSet is already patched
        if not self.k8s_auth():
            return False

        # Get an API client
        cl = kubernetes.client.ApiClient()
        apps_api = kubernetes.client.AppsV1Api(cl)
        stateful_set = apps_api.read_namespaced_stateful_set(
            name=self.app.name, namespace=self.model.name)
        return stateful_set.spec.template.spec.service_account_name == "influxdb2"

    def _patch_influxdb2_stateful_set(self) -> None:
        """Patch the StatefulSet created by Juju to include specific ServiceAccount and Secret mounts."""
        self.unit.status = MaintenanceStatus("Patching StatefulSet for additional k8s permissions")
        # Get an API client
        cl = kubernetes.client.ApiClient()
        apps_api = kubernetes.client.AppsV1Api(cl)
        core_api = kubernetes.client.CoreV1Api(cl)

        # Read the StatefulSet we're deployed into
        stateful_set = apps_api.read_namespaced_stateful_set(
            name=self.app.name, namespace=self.model.name)
        # Add the service account to the spec
        stateful_set.spec.template.spec.service_account_name = "influxdb2"
        # Get the details of the kubernetes influxdb2 service account
        service_account = core_api.read_namespaced_service_account(
            name="influxdb2", namespace=self.model.name
        )

        # Create a Volume and VolumeMount for the influxdb2 service account
        service_account_volume_mount = kubernetes.client.V1VolumeMount(
            mount_path="/var/run/secrets/kubernetes.io/serviceaccount",
            name="influxdb2-service-account",
        )
        service_account_volume = kubernetes.client.V1Volume(
            name="influxdb2-service-account",
            secret=kubernetes.client.V1SecretVolumeSource(
                secret_name=service_account.secrets[0].name),
        )
        # Add them to the StatefulSet
        stateful_set.spec.template.spec.volumes.append(service_account_volume)
        stateful_set.spec.template.spec.containers[1].volume_mounts.append(
            service_account_volume_mount)

        # Patch the StatefulSet
        apps_api.patch_namespaced_stateful_set(
            name=self.app.name, namespace=self.model.name, body=stateful_set)
        logger.debug("Patched StatefulSet...")

    # def _create_additional_resources(self) -> None:
    #     """Create additional Kubernetes resources."""
    #     self.unit.status = MaintenanceStatus("Creating k8s resources")
    #     # Get an API client
    #     cl = kubernetes.client.ApiClient()
    #     core_api = kubernetes.client.CoreV1Api(cl)
    #     auth_api = kubernetes.client.RbacAuthorizationV1Api(cl)
    #     try:
    #         # Create the "influxdb2" service
    #         logger.debug("Creating additional Kubernetes Services")
    #         core_api.create_namespaced_service(
    #             namespace=self.model.name,
    #             body=kubernetes.client.V1Service(
    #                 api_version="v1",
    #                 metadata=self._template_meta("influxdb2"),
    #                 spec=kubernetes.client.V1ServiceSpec(
    #                     ports=[kubernetes.client.V1ServicePort(port=80, target_port=8086)],
    #                     selector={"app.kubernetes.io/name": self.app.name},
    #                 ),
    #             ),
    #         )
    #     except kubernetes.client.exceptions.ApiException as e:
    #         # 409 Conflict
    #         if e.status != 409:
    #             raise

    #     try:
    #         # Create the "infludb2-auth" secret
    #         logger.debug("Creating additonal Kubernetes Secrets")
    #         core_api.create_namespaced_secret(
    #             namespace=self.model.name,
    #             body=kubernetes.client.V1Secret(
    #                 api_version="v1",
    #                 metadata=self._template_meta("influxdb2-auth"),
    #                 type="Opaque",
    #             ),
    #         )
    #     except kubernetes.client.exceptions.ApiException as e:
    #         if e.status != 409:
    #             raise

    def _template_meta(self, name) -> kubernetes.client.V1ObjectMeta:
        """Helper method to return common Kubernetes V1ObjectMeta."""
        return kubernetes.client.V1ObjectMeta(
            namespace=self.model.name,
            name=name,
            labels={"app.kubernetes.io/name": self.app.name},
        )
    
    def _is_running(self, container: Container, service: str) -> bool:
        """Helper method to determine if a given service is running in a given container"""
        try:
            svc = container.get_service(service)
            return svc.current == ServiceStatus.ACTIVE
        except ModelError:
            return False

    def k8s_auth(self) -> bool:
        """Authenticate to Kubernetes."""
        if self._authed:
            return True

        try:
            # Authenticate against the Kubernetes API using a mounted ServiceAccount token
            kubernetes.config.load_incluster_config()
            # Test the service account we've got for sufficient perms
            kubernetes.client.RbacAuthorizationV1Api(kubernetes.client.ApiClient())
            # auth_api.read_namespaced_role(namespace=self.model.name, name=self.app.name)
        except Exception as e:
            logger.debug(f"k8s_auth error: {e}")
            # If we can't read a namespaced role, we definitely don't have enough permissions
            self.unit.status = BlockedStatus("Run juju trust on this application to continue")
            return False

        self._authed = True
        return True


if __name__ == "__main__":
    main(KubernetesInfluxdbCharm)
