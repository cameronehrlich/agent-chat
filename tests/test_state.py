from agent_chat.state import AgentChatState, LastSeenEntry

def test_state_defaults(tmp_path):
    state = AgentChatState.load()
    assert "#general" in state.subscribed_channels
    state.ensure_subscription("#dev")
    assert "#dev" in state.subscribed_channels
    state.touch_channel("#dev", "msg123")
    assert state.channels["#dev"].msgid == "msg123"
    state.touch_direct("@BlueLake", "dm1")
    assert state.directs["@BlueLake"].msgid == "dm1"
