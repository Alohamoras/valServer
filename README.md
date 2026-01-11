# Valheim Dedicated Server Installer

Self-host a Valheim server on Ubuntu and manage it entirely through conversation with Claude. This repo provides everything you need: automated installation, mod management via Thunderstore, and an MCP server that lets Claude handle server administration through natural language.

## What's Included

- **Install script** — Sets up SteamCMD, the Valheim dedicated server, and systemd services
- **MCP server** — Enables Claude to manage your server directly (start/stop, mod installation, status checks, etc.)
- **claude.md** — Project context that helps Claude understand the server architecture and available commands

## Quick Start

1. Install Ubuntu 24.04
2. Install [Claude Code](https://docs.anthropic.com/en/docs/claude-code)
3. Ask Claude to clone this repo and run the install script
4. Start managing your server through conversation — search for mods, check status, update the server, and more

## Features

- Installs SteamCMD and Valheim Dedicated Server
- Installs [Valheim Mod Manager (vmm)](https://github.com/endoze/valheim-mod-manager) for mod management
- Installs [BepInEx](https://github.com/BepInEx/BepInEx) and [Valheim Plus](https://github.com/Grantapher/ValheimPlus) via vmm
- Creates systemd service for easy server management
- Configures daily auto-updates for game and mods (5 AM Eastern Time)
- Automatically configures UFW firewall rules if active
- **MCP server for Claude AI integration** (manage server via natural language)

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

### One-Liner (Non-Interactive)

```bash
sudo ./install.sh -n "My Server" -w "MyWorld" -p "secret123" -y -s
```

### Options

| Flag | Description |
|------|-------------|
| `-n` | Server name (displayed in server list) |
| `-w` | World name (name of the world save) |
| `-p` | Server password (minimum 5 characters) |
| `-y` | Skip confirmation prompt |
| `-s` | Start server after installation |
| `-h` | Show help message |

## Server Management

```bash
sudo systemctl start valheim     # Start server
sudo systemctl stop valheim      # Stop server
sudo systemctl restart valheim   # Restart server
sudo systemctl status valheim    # Check status
sudo journalctl -u valheim -f    # View live logs
```

## Updating

Updates run automatically daily at 5 AM Eastern Time. To update manually:

```bash
sudo /home/steam/update-valheim.sh
```

## File Locations

| Description | Path |
|-------------|------|
| Server files | `/home/steam/valheim-server/` |
| World saves | `/home/steam/.config/unity3d/IronGate/Valheim/` |
| Valheim Plus config | `/home/steam/valheim-server/BepInEx/config/valheim_plus.cfg` |
| Mod config (vmm) | `/home/steam/vmm_config.toml` |
| Backups | `/home/steam/valheim-backups/` |
| Update log | `/var/log/valheim-update.log` |

## Valheim Plus Configuration

Edit the Valheim Plus config to customize gameplay:

```bash
sudo nano /home/steam/valheim-server/BepInEx/config/valheim_plus.cfg
```

Restart the server after making changes:

```bash
sudo systemctl restart valheim
```

## Mod Management

Mods are managed via [Valheim Mod Manager (vmm)](https://github.com/endoze/valheim-mod-manager), which downloads mods from [Thunderstore](https://thunderstore.io/c/valheim/) and handles dependencies automatically.

### Adding Mods

```bash
# Search for mods
sudo -u steam bash -c 'source ~/.cargo/env && vmm search "mod name"'

# Add a mod (use Owner-ModName format from search results)
sudo -u steam bash -c 'source ~/.cargo/env && vmm add ValheimModding-Jotunn'

# Install all configured mods
sudo -u steam bash -c 'source ~/.cargo/env && vmm update'
```

### Updating Mods

The daily auto-update cron job updates both the game and all mods. To update mods manually:

```bash
sudo -u steam bash -c 'source ~/.cargo/env && vmm update'
sudo systemctl restart valheim
```

### Mod Configuration

Mods are configured in `/home/steam/vmm_config.toml`. The MCP server provides tools to manage mods without manual file editing.

## Claude AI Integration (MCP Server)

This project includes an MCP server that allows Claude to manage your Valheim server directly.

### Setup

1. Install Python dependencies:
   ```bash
   cd mcp-server
   pip install -r requirements.txt
   ```

2. Add to your Claude Code settings (`~/.claude/settings.json`):
   ```json
   {
     "mcpServers": {
       "valheim": {
         "command": "python",
         "args": ["/path/to/valServer/mcp-server/valheim_server.py"]
       }
     }
   }
   ```

3. Restart Claude Code

### Available Tools

| Category | Tools |
|----------|-------|
| Server | `server_status`, `server_start`, `server_stop`, `server_restart`, `server_logs`, `server_info` |
| Config | `config_get`, `config_set`, `config_sections` |
| Backup | `backup_create`, `backup_list`, `backup_restore`, `backup_delete` |
| Update | `update_check`, `update_server`, `update_valheimplus`, `update_all` |
| Mods | `mods_list`, `mods_add`, `mods_remove`, `mods_search`, `mods_update` |

### Example Usage

Just ask Claude:
- "What's the server status?"
- "Restart the Valheim server"
- "Create a backup before we make changes"
- "Update Valheim Plus to the latest version"
- "Show me the last 100 lines of server logs"
- "Enable the Map section in Valheim Plus config"
- "Search for equipment mods"
- "Add the Jotunn mod"
