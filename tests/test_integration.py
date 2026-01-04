import os
import shutil
import socket
import subprocess
import time
from pathlib import Path

import pytest
from typer.testing import CliRunner

from agent_chat import app
from agent_chat import config as config_mod
from agent_chat import logging as logging_mod
from agent_chat import state as state_mod
from agent_chat.config import AgentChatConfig

pytestmark = pytest.mark.integration


def _wait_for_port(host: str, port: int, timeout: float = 15.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=1):
                return
        except OSError:
            time.sleep(0.2)
    raise RuntimeError(f"Port {host}:{port} did not open")


@pytest.fixture(scope="session")
def ergo_server(tmp_path_factory):
    if shutil.which("docker") is None:
        pytest.skip("Docker not available")
    workdir = tmp_path_factory.mktemp("ergo")
    config_file = workdir / "ircd.yaml"
    config_file.write_text(
        """
server:
    name: test.local
    listeners:
        "0.0.0.0:6667": {}
network:
    name: TestNet
accounts:
    registration:
        enabled: false
history:
    enabled: true
    channel-length: 4096
    client-length: 512
    chathistory-maxmessages: 1000
    restrictions:
        expire-time: 168h
channels:
    default-modes: +nt
"""
    )
    port = 18667
    cmd = [
        "docker",
        "run",
        "-d",
        "--rm",
        "-p",
        f"{port}:6667",
        "-v",
        f"{config_file}:/etc/ergo/ircd.yaml:ro",
        "ghcr.io/ergochat/ergo:stable",
        "run",
        "--config",
        "/etc/ergo/ircd.yaml",
    ]
    container_id = subprocess.check_output(cmd).decode().strip()
    try:
        _wait_for_port("127.0.0.1", port)
        yield ("127.0.0.1", port, container_id)
    finally:
        subprocess.run(["docker", "rm", "-f", container_id], check=False)


@pytest.fixture()
def configured_cli(ergo_server, monkeypatch, tmp_path):
    host, port, _ = ergo_server
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("AGENT_CHAT_HOME", str(home))
    config_mod.APP_DIR = home
    config_mod.CONFIG_FILE = home / "config.toml"
    config_mod.CREDENTIALS_FILE = home / "credentials.json"
    config_mod.LOCK_FILE = config_mod.CONFIG_FILE.with_suffix(".lock")
    state_mod.APP_DIR = home
    state_mod.STATE_FILE = home / "state.json"
    state_mod.STATE_LOCK = state_mod.STATE_FILE.with_suffix(".lock")
    logging_mod.APP_DIR = home
    logging_mod.LOG_DIR = home / "logs"
    logging_mod.LOG_FILE = logging_mod.LOG_DIR / "ac.log"
    config = AgentChatConfig.load()
    config.server.host = host
    config.server.port = port
    config.server.tls = False
    config.identity.nick = "IntegrationBot"
    config.save()
    return CliRunner()


def test_send_and_listen(configured_cli):
    runner = configured_cli
    assert runner.invoke(app, ["status"]).exit_code == 0
    result = runner.invoke(app, ["send", "#alerts", "integration test"])
    assert result.exit_code == 0
    time.sleep(1)
    listen = runner.invoke(app, ["listen", "#alerts", "--last", "5"])
    assert listen.exit_code == 0
    notify = runner.invoke(app, ["notify", "--oneline"])
    assert notify.exit_code == 0
