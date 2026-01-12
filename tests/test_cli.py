from typer.testing import CliRunner

from agent_chat import app

def test_channels_command():
    runner = CliRunner()
    result = runner.invoke(app, ["channels", "--subscribe", "#dev"])
    assert result.exit_code == 0
    assert "#dev" in result.stdout

def test_config_command():
    runner = CliRunner()
    result = runner.invoke(app, ["config", "--set", "server.url=http://1.2.3.4:8008"])
    assert result.exit_code == 0
    assert "1.2.3.4" in result.stdout

def test_config_identity():
    runner = CliRunner()
    result = runner.invoke(app, ["config", "--set", "identity.username=testagent"])
    assert result.exit_code == 0
    assert "testagent" in result.stdout
