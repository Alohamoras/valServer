 What works well:
  ┌────────────┬─────────────────────────────────────────────────────────────────────────────────────────────────┐
  │ Component  │                                            Strength                                             │
  ├────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ MCP server │ Gives Claude actions, not just knowledge. Claude can actually do things, not just explain how   │
  ├────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ CLAUDE.md  │ Domain knowledge that Claude wouldn't otherwise have (V+ config details, troubleshooting, SOPs) │
  ├────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ Scripts    │ Handles complex setup once; user doesn't need Linux expertise after install                     │
  ├────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ Separation │ Clean layers: scripts for setup, MCP for runtime actions, CLAUDE.md for knowledge               │
  └────────────┴─────────────────────────────────────────────────────────────────────────────────────────────────┘
  The insight: Most "AI wrappers" just give an LLM knowledge. This project gives Claude capability - the MCP tools let Claude take action, not just advise.

  Potential enhancements to consider:

  1. Doctor/health check tool - You asked about this earlier; an MCP tool that runs diagnostics
  2. Alerting integration - Discord webhook when server crashes or needs attention
  3. Player management - Ban/whitelist tools if the game supports it
  4. Session memory - Some way for Claude to remember past issues (maybe a simple log file it can read/write)
  5. Scheduled tasks via Claude - "Remind me to update the server tomorrow" type workflows

  Limitations of the approach:

  - Tied to Claude Code specifically (won't work with regular Claude chat)
  - Requires Claude Code running to manage server (no autonomous monitoring)
  - Each session starts fresh - no memory of past conversations
