import pytest

from agent_chat import config as config_mod
from agent_chat import state as state_mod
from agent_chat import logging as logging_mod


@pytest.fixture(autouse=True)
def isolated_home(tmp_path, monkeypatch):
    home = tmp_path / "agent-home"
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

    # Mock keyring for tests
    store = {}

    class FakeKeyring:
        def set_password(self, service, user, password):
            store[(service, user)] = password

        def get_password(self, service, user):
            return store.get((service, user))

    config_mod.keyring = FakeKeyring()
    config_mod.KEYRING_AVAILABLE = True
    yield
