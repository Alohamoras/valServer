# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This repository contains:
- `install.sh` - Bash installer for deploying a Valheim dedicated server with Valheim Plus on Ubuntu 24.04
- `mcp-server/` - MCP server providing Claude with native tools to manage the Valheim server

## MCP Server Setup

The MCP server gives Claude direct tools to manage the Valheim server. Setup is automated by `install.sh` when run from the repository directory.

**Automated setup (recommended):**

The installer automatically:
- Creates a Python venv in `mcp-server/`
- Installs dependencies
- Registers the MCP server with Claude Code using `claude mcp add`

Just restart Claude Code after installation to enable the tools.

**Manual setup:**

If you need to set up manually:

1. Install dependencies:
   ```bash
   sudo apt install python3.12-venv -y
   cd mcp-server
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   deactivate
   ```

2. Register the MCP server with Claude Code:
   ```bash
   claude mcp add --transport stdio valheim -- /path/to/valServer/mcp-server/venv/bin/python /path/to/valServer/mcp-server/valheim_server.py
   ```

3. Restart Claude Code

## Available MCP Tools

### Server Management
- `server_status` - Get running state, uptime, memory usage
- `server_start` - Start the server
- `server_stop` - Stop the server (graceful shutdown)
- `server_restart` - Restart the server
- `server_logs` - Get recent logs (with optional filter)
- `server_info` - Get server name, world, paths

### Configuration (Valheim Plus)
- `config_get` - Read config values (all or by section)
- `config_set` - Set a config value
- `config_sections` - List available config sections

### Backups
- `backup_create` - Create world backup
- `backup_list` - List available backups
- `backup_restore` - Restore a backup
- `backup_delete` - Delete a backup

### Updates
- `update_check` - Check for available updates
- `update_server` - Update Valheim via SteamCMD
- `update_valheimplus` - Update Valheim Plus
- `update_all` - Update everything

## Key File Locations (on target system)

- Server files: `/home/steam/valheim-server/`
- World saves: `/home/steam/.config/unity3d/IronGate/Valheim/`
- Valheim Plus config: `/home/steam/valheim-server/BepInEx/config/valheim_plus.cfg`
- Backups: `/home/steam/valheim-backups/`

## What the Installer Does

1. Installs SteamCMD and Valheim Dedicated Server (Steam App ID 896660)
2. Installs Valheim Plus mod from the Grantapher fork
3. Creates `steam` system user for running the server
4. Sets up systemd service (`valheim.service`)
5. Configures daily auto-update cron job (5 AM Eastern)
6. Opens firewall ports 2456-2458/UDP if UFW is active

## Running the Installer

```bash
# Interactive
sudo ./install.sh

# Non-interactive
sudo ./install.sh -n "Server Name" -w "WorldName" -p "password" -y -s
```

Flags: `-n` name, `-w` world, `-p` password, `-y` skip confirm, `-s` auto-start, `-h` help
