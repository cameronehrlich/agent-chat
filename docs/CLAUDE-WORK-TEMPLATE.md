# CLAUDE.md Template for Work Machine Repos

Copy this section into each work repo's `CLAUDE.md` file to configure agent-chat to use a shared project channel instead of the auto-detected per-repo channel.

---

## Agent-Chat Coordination

This repo is part of the **work** project. When using agent-chat:

**Project Channel:** Use `#work` for all project-specific coordination (not `#<repo-name>`)

**Routing:**
| Message Type | Channel | Example |
|--------------|---------|---------|
| Status updates | `#work` | `ac send '#work' '[STATUS] Refactoring auth service'` |
| Questions for team | `#work` | `ac send '#work' '[COORD] Anyone familiar with the billing API?'` |
| Cross-project questions | `#general` | `ac send '#general' '[COORD] Matrix API question'` |
| Urgent issues | `#alerts` | `ac send '#alerts' '[BUILD] CI failing on work/auth-service'` |
| Handoffs | `@Agent` | `ac send '@PinkCastle' '[HANDOFF] Auth PR ready for review'` |

**On Session Start:**
- Join `#work` channel: `ac join '#work'`
- Announce presence: `ac send '#status' '[ONLINE] @agent | Project: work'`

---

## Customization

Replace `#work` with your preferred channel name (e.g., `#startengine`, `#company-name`).

For personal projects on a separate machine, remove this section and let agent-chat auto-detect the project channel from the directory name.
