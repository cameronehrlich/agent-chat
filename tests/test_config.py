from agent_chat.config import AgentChatConfig

def test_config_roundtrip():
    cfg = AgentChatConfig.load()
    cfg.server.url = "http://100.64.1.2:8008"
    cfg.identity.username = "testagent"
    cfg.save()
    reloaded = AgentChatConfig.load()
    assert reloaded.server.url == "http://100.64.1.2:8008"
    assert reloaded.identity.username == "testagent"

def test_config_defaults():
    cfg = AgentChatConfig.load()
    # Should have sensible defaults
    assert cfg.server.url is not None
    assert cfg.identity.display_name is not None
