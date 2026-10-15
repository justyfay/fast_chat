import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from ..constants import ComposeTestData

COMPOSE_FILE = Path(__file__).resolve().parents[2] / "docker-compose.yml"


def docker_compose_available() -> bool:
    """Проверка, что установлены docker и плагин compose."""
    if shutil.which("docker") is None:
        return False
    result = subprocess.run(
        ["docker", "compose", "version"], capture_output=True, check=False
    )
    return result.returncode == 0


pytestmark = pytest.mark.skipif(
    not docker_compose_available(), reason="docker compose не установлен"
)


def run_compose_config(
    workdir: Path, env_overrides: dict[str, str | None] | None = None
) -> subprocess.CompletedProcess:
    """Запускает `docker compose config` в каталоге с копией compose-файла и тестовым `.env`."""
    env_values = {**ComposeTestData.ENV, **(env_overrides or {})}
    env_values = {key: value for key, value in env_values.items() if value is not None}
    (workdir / "docker-compose.yml").write_text(COMPOSE_FILE.read_text())
    (workdir / ".env").write_text(
        "".join(f"{key}={value}\n" for key, value in env_values.items())
    )
    env = {
        key: value
        for key, value in os.environ.items()
        if key not in ComposeTestData.ENV
    }
    return subprocess.run(
        ["docker", "compose", "config", "--format", "json"],
        cwd=workdir,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.fixture
def compose_services(tmp_path: Path) -> dict:
    result = run_compose_config(tmp_path)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)["services"]


@pytest.mark.parametrize("service", ComposeTestData.LOCAL_ONLY_SERVICES)
def test_service_ports_are_bound_to_localhost(
    service: str, compose_services: dict
) -> None:
    """Порты Postgres, Redis, Flower и pgAdmin доступны только с самого хоста"""
    # Act
    ports = compose_services[service]["ports"]

    # Assert
    assert ports
    assert all(port["host_ip"] == "127.0.0.1" for port in ports)


def test_redis_requires_password(compose_services: dict) -> None:
    """Redis запускается с паролем"""
    # Act
    command = compose_services["redis"]["command"]

    # Assert
    assert "--requirepass" in command
    assert (
        command[command.index("--requirepass") + 1]
        == (ComposeTestData.ENV["REDIS_PASSWORD"])
    )


def test_pgadmin_requires_login(compose_services: dict) -> None:
    """pgAdmin работает в серверном режиме, вход обязателен"""
    # Act
    environment = compose_services["pgadmin"]["environment"]

    # Assert
    assert environment["PGADMIN_CONFIG_SERVER_MODE"] == "True"


@pytest.mark.parametrize("variable", ComposeTestData.REQUIRED_VARIABLES)
def test_error_compose_without_required_variable(variable: str, tmp_path: Path) -> None:
    """Без обязательных переменных compose не запускается"""
    # Act
    result = run_compose_config(tmp_path, env_overrides={variable: None})

    # Assert
    assert result.returncode != 0
    assert variable in result.stderr


def test_compose_has_no_default_passwords() -> None:
    """В compose-файле нет значений паролей по умолчанию"""
    # Act
    lines = COMPOSE_FILE.read_text().splitlines()

    # Assert
    defaults = [
        line
        for line in lines
        if re.search(r"(PASS|PASSWORD|SECRET|TOKEN|AUTH)\w*\s*:.*:-", line)
    ]
    assert not defaults
