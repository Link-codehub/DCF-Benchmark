"""Experimental Docker environment with IPv4-only egress enforcement."""

from pathlib import Path
from harbor.environments.docker.docker import DockerEnvironment


class IPv4DockerEnvironment(DockerEnvironment):
    _DOCKER_COMPOSE_EGRESS_CONTROL_PATH = Path(__file__).with_name("ipv4_egress") / "compose.yaml"
    _EGRESS_CONTROL_SERVICE_NAME = "dcf-egress-firewall"
    _EGRESS_CONTROL_SIDECAR_READY_FILE = "/tmp/dcf-egress-ready"
    _EGRESS_CONTROL_KERNEL_PROBE_SCRIPT = (
        "if [ ! -f /proc/config.gz ]; then exit 0; fi; "
        "zcat /proc/config.gz 2>/dev/null | grep -qE '^CONFIG_NFT_FIB_IPV4=[ym]'"
    )

    _EGRESS_CONTROL_SIDECAR_DOCKER_NAME = "dcf-ipv4-gost-egress"

    def __init__(self, *args, **kwargs):
        kwargs["network_policy"] = kwargs["task_env_config"].resolve_baseline()
        super().__init__(*args, **kwargs)

    async def _ensure_egress_control_sidecar_image_built(self) -> None:
        self._env_vars.egress_control_sidecar_image_name = "dcf-ipv4-gost-egress:v1"
