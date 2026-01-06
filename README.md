# Valheim Dedicated Server Installer

Automated installer for a Valheim dedicated server with Valheim Plus mod on Ubuntu 24.04. Includes an MCP server for Claude integration.

## Features

- Installs SteamCMD and Valheim Dedicated Server
- Installs [Valheim Plus](https://github.com/Grantapher/ValheimPlus) mod
- Creates systemd service for easy server management
- Configures daily auto-updates (5 AM Eastern Time)
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

### Example Usage

Just ask Claude:
- "What's the server status?"
- "Restart the Valheim server"
- "Create a backup before we make changes"
- "Update Valheim Plus to the latest version"
- "Show me the last 100 lines of server logs"
- "Enable the Map section in Valheim Plus config"
