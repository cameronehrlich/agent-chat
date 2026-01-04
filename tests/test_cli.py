from typer.testing import CliRunner

from agent_chat import app

def test_channels_command():
    runner = CliRunner()
    result = runner.invoke(app, ["channels", "--subscribe", "#dev"])
    assert result.exit_code == 0
    assert "#dev" in result.stdout

def test_config_command():
    runner = CliRunner()
    result = runner.invoke(app, ["config", "--set", "server.host=1.2.3.4"])
    assert result.exit_code == 0
    assert "1.2.3.4" in result.stdout

def test_register_and_login():
    runner = CliRunner()
    result = runner.invoke(app, ["register", "--nick", "TestNick", "--password", "secret"])
    assert result.exit_code == 0
    result = runner.invoke(app, ["login", "TestNick", "--password", "secret2"])
    assert result.exit_code == 0
