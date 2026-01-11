# Valheim Dedicated Server Installer

Self-host a Valheim server on Ubuntu and manage it entirely through conversation with Claude. This repo provides everything you need: automated installation, mod management via Thunderstore, and an MCP server that lets Claude handle server administration through natural language.

## What's Included

- **Install script** — Sets up SteamCMD, the Valheim dedicated server, and systemd services
- **MCP server** — Enables Claude to manage your server directly (start/stop, mod installation, status checks, etc.)
- **CLAUDE.md** — Project context that helps Claude understand the server architecture and available commands

## Quick Start

1. Install Ubuntu 24.04
2. Install [Claude Code](https://docs.anthropic.com/en/docs/claude-code)
3. Ask Claude to clone this repo and run the install script
4. Start managing your server through conversation

## Requirements

- Ubuntu 24.04
- Root access (sudo)
- Ports 2456-2458 UDP open for incoming connections

## Installation

### Interactive

```bash
git clone https://github.com/Alohamoras/valServer.git
cd valServer
sudo ./install.sh
```

### Non-Interactive

```bash
sudo ./install.sh -n "My Server" -w "MyWorld" -p "secret123" -y -s
```

| Flag | Description |
|------|-------------|
| `-n` | Server name (displayed in server list) |
| `-w` | World name (name of the world save) |
| `-p` | Server password (minimum 5 characters) |
| `-y` | Skip confirmation prompt |
| `-s` | Start server after installation |
| `-h` | Show help message |

## Using Your Server

After installation, just ask Claude. The MCP server is automatically configured during install.

**Example requests:**
- "What's the server status?"
- "Restart the server"
- "Create a backup"
- "Search for mods with 'equipment' in the name"
- "Add the Jotunn mod"
- "Update the server and all mods"
- "Enable map sharing in Valheim Plus"
- "Show me the last 100 lines of server logs"

Claude can handle server lifecycle, mod management, configuration, backups, and updates — all through conversation.

## Features

- Installs SteamCMD and Valheim Dedicated Server
- Installs [Valheim Mod Manager (vmm)](https://github.com/endoze/valheim-mod-manager) for mod management
- Installs [BepInEx](https://github.com/BepInEx/BepInEx) and [Valheim Plus](https://github.com/Grantapher/ValheimPlus) via vmm
- Creates systemd service for easy server management
- Configures daily auto-updates for game and mods (5 AM Eastern Time)
- Automatically configures UFW firewall rules if active

---

## Reference

The sections below document manual commands and file locations. These are provided for troubleshooting, advanced use cases, or if you prefer to manage the server without Claude.

### File Locations

| Description | Path |
|-------------|------|
| Server files | `/home/steam/valheim-server/` |
| World saves | `/home/steam/.config/unity3d/IronGate/Valheim/` |
| Valheim Plus config | `/home/steam/valheim-server/BepInEx/config/valheim_plus.cfg` |
| Mod config (vmm) | `/home/steam/vmm_config.toml` |
| Backups | `/home/steam/valheim-backups/` |
| Update log | `/var/log/valheim-update.log` |

### Manual Server Management

```bash
sudo systemctl start valheim     # Start server
sudo systemctl stop valheim      # Stop server
sudo systemctl restart valheim   # Restart server
sudo systemctl status valheim    # Check status
sudo journalctl -u valheim -f    # View live logs
```

### Manual Updates

Updates run automatically daily at 5 AM Eastern Time. To update manually:

```bash
sudo /home/steam/update-valheim.sh
```

### Manual Mod Management

Mods are managed via [Valheim Mod Manager (vmm)](https://github.com/endoze/valheim-mod-manager), which downloads mods from [Thunderstore](https://thunderstore.io/c/valheim/) and handles dependencies automatically.

```bash
# Search for mods
sudo -u steam bash -c 'source ~/.cargo/env && vmm search "mod name"'

# Add a mod (use Owner-ModName format from search results)
sudo -u steam bash -c 'source ~/.cargo/env && vmm add ValheimModding-Jotunn'

# Install all configured mods
sudo -u steam bash -c 'source ~/.cargo/env && vmm update'
```

### Valheim Plus Configuration

Edit the config file directly:

```bash
sudo nano /home/steam/valheim-server/BepInEx/config/valheim_plus.cfg
```

Restart the server after making changes:

```bash
sudo systemctl restart valheim
```

### MCP Server Details

The MCP server provides Claude with these tools:

| Category | Tools |
|----------|-------|
| Server | `server_status`, `server_start`, `server_stop`, `server_restart`, `server_logs`, `server_info` |
| Config | `config_get`, `config_set`, `config_sections` |
| Backup | `backup_create`, `backup_list`, `backup_restore`, `backup_delete` |
| Update | `update_check`, `update_server`, `update_valheimplus`, `update_all` |
| Mods | `mods_list`, `mods_add`, `mods_remove`, `mods_search`, `mods_update` |

**Manual MCP setup** (only needed if auto-setup failed):

1. Install dependencies:
   ```bash
   cd mcp-server
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   deactivate
   ```

2. Register with Claude Code:
   ```bash
   claude mcp add --transport stdio valheim -- /path/to/valServer/mcp-server/venv/bin/python /path/to/valServer/mcp-server/valheim_server.py
   ```

3. Restart Claude Code
