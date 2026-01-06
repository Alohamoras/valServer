# Valheim Dedicated Server Installer

Automated installer for a Valheim dedicated server with Valheim Plus mod on Ubuntu 24.04.

## Features

- Installs SteamCMD and Valheim Dedicated Server
- Installs [Valheim Plus](https://github.com/Grantapher/ValheimPlus) mod
- Creates systemd service for easy server management
- Configures daily auto-updates (5 AM Eastern Time)
- Automatically configures UFW firewall rules if active

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
