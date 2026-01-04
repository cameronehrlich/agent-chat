from agent_chat.config import AgentChatConfig, set_password, get_password

def test_config_roundtrip():
    cfg = AgentChatConfig.load()
    cfg.server.host = "100.64.1.2"
    cfg.identity.nick = "TestNick"
    cfg.save()
    reloaded = AgentChatConfig.load()
    assert reloaded.server.host == "100.64.1.2"
    assert reloaded.identity.nick == "TestNick"
    set_password("TestNick", "secret")
    assert get_password("TestNick") == "secret"
