# Agent Chat – Handoff Notes (2026-01-04)

## Environment snapshot

- **CLI install:** `pip install -e .` already run; `ac` resolves to `/opt/homebrew/bin/ac`.
- **Config/state:** `~/.agent-chat/config.toml`, `state.json`, `logs/ac.log`.
- **Credentials:** still plaintext in `~/.agent-chat/credentials.json` until Keychain work lands.
- **Ergo server:** binary at `~/bin/ergo`, config/db under `~/.agent-chat-ergo/`.
  - PM2 process name `agent-chat`; restart with  
    `ERGO_BIN=$HOME/bin/ergo ERGO_CONFIG=$HOME/.agent-chat-ergo/ircd.yaml pm2 restart agent-chat`.
  - Logs: `~/.pm2/logs/agent-chat-{out,error}.log`.

## Work completed this session

1. **CHATHISTORY reliability**
   - `listen`/`notify` now join every channel before issuing CHATHISTORY so Ergo accepts the request.
   - `IRCSession.fetch_history` was hardened to watch both `privmsg`/`pubmsg` events inside the target batch.
   - Verified by sending `message via CLI` / `testing history after batch fix` and retrieving them.
2. **Ergo configuration**
   - Updated `~/.agent-chat-ergo/ircd.yaml` to keep history accessible (`query-cutoff: 'none'`, `grace-period: 1h`).
   - Restarted PM2 to apply the change.
3. **Documentation**
   - README now captures setup, PM2 usage, state file locations, and next steps.
4. **Channel check-ins**
   - `ac send '#general' ...` is working; history requests currently show the most recent join/quit because the cache is up to date.

## How to continue

1. **If you need fresh backlog**
   - Edit or delete `~/.agent-chat/state.json` entries for a channel to force CHATHISTORY to replay older messages.
2. **Monitoring**
   - `ac status`, `ac listen '#general' --last 20`, `ac notify --oneline`.
   - `pm2 logs agent-chat --lines 100` if the CLI reports timeouts.
3. **Tests**
   - Run `pytest` (Docker Desktop must be running for integration tests).

## Open items / next steps

- Replace plaintext credential storage with macOS Keychain (`keyring`) as noted in SPEC.
- Decide whether to scope in/out the optional TUI (`ac tui`) for v1 and update the spec accordingly.
- Improve/extend `scripts/install.sh` so non-macOS hosts have a documented route (currently assumes Homebrew).
- Consider adding convenience commands for clearing/replaying state (`ac history reset #channel`?).
- Keep Ergo running via PM2; if it crashes again, check for config validation errors in the PM2 logs.

Ping `#general` with `ac send` if you hand off again so the next agent knows where things stand.
