# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This repository contains a single bash installer script (`install.sh`) for deploying a Valheim dedicated game server with Valheim Plus mod on Ubuntu 24.04.

## What the Installer Does

The script performs a complete server setup:
1. Installs SteamCMD and Valheim Dedicated Server (Steam App ID 896660)
2. Installs Valheim Plus mod from the Grantapher fork
3. Creates a `steam` system user for running the server
4. Sets up a systemd service (`valheim.service`) for server management
5. Configures a daily auto-update cron job (5 AM Eastern Time)
6. Opens firewall ports 2456-2458/UDP if UFW is active

## Key File Locations (on target system after install)

- Server files: `/home/steam/valheim-server/`
- World saves: `/home/steam/.config/unity3d/IronGate/Valheim/`
- Valheim Plus config: `/home/steam/valheim-server/BepInEx/config/valheim_plus.cfg`
- Update script: `/home/steam/update-valheim.sh`
- Update log: `/var/log/valheim-update.log`

## Server Management (post-install)

```bash
sudo systemctl start valheim      # Start server
sudo systemctl stop valheim       # Stop server
sudo systemctl status valheim     # Check status
sudo journalctl -u valheim -f     # View logs
sudo /home/steam/update-valheim.sh  # Manual update
```

## Running the Installer

```bash
sudo ./install.sh
```

The script prompts interactively for server name, world name, and password (minimum 5 characters).
