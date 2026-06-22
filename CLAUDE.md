# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This repository contains:
- `install.sh` - Bash installer for deploying a Valheim dedicated server with mods on Ubuntu 24.04
- `mcp-server/` - MCP server providing Claude with native tools to manage the Valheim server

Mods are managed via [Valheim Mod Manager (vmm)](https://github.com/endoze/valheim-mod-manager), which downloads mods from Thunderstore and handles dependencies automatically.

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
   sudo apt install python3-venv -y
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

### Mod Management (vmm)
- `mods_list` - List configured mods from vmm_config.toml
- `mods_add` - Add a mod to config and optionally install it
- `mods_remove` - Remove a mod from config
- `mods_search` - Search for mods on Thunderstore
- `mods_update` - Update all mods to latest versions

## Key File Locations (on target system)

- Server files: `/home/steam/valheim-server/`
- World saves: `/home/steam/.config/unity3d/IronGate/Valheim/`
- Valheim Plus config: `/home/steam/valheim-server/BepInEx/config/valheim_plus.cfg`
- Mod config (vmm): `/home/steam/vmm_config.toml`
- Backups: `/home/steam/valheim-backups/`

## What the Installer Does

1. Creates `steam` system user for running the server
2. Installs Rust and Valheim Mod Manager (vmm) for the steam user
3. Installs SteamCMD and Valheim Dedicated Server (Steam App ID 896660)
4. Configures vmm with BepInEx and Valheim Plus, then installs mods
5. Sets up systemd service (`valheim.service`)
6. Configures daily auto-update cron job (5 AM Eastern) - updates both game and mods
7. Opens firewall ports 2456-2458/UDP if UFW is active

## Running the Installer

```bash
# Interactive
sudo ./install.sh

# Non-interactive
sudo ./install.sh -n "Server Name" -w "WorldName" -p "password" -y -s
```

Flags: `-n` name, `-w` world, `-p` password, `-y` skip confirm, `-s` auto-start, `-h` help

---

## Valheim Server Administration Quick Reference

### Boss Progression & Content Gates

| Boss | Biome | Key Unlock | Server Impact |
|------|-------|------------|---------------|
| Eikthyr | Meadows | Antler Pickaxe | Players can mine copper/tin |
| The Elder | Black Forest | Swamp Key | Unlocks Swamp crypts |
| Bonemass | Swamp | Wishbone | Players can find silver |
| Moder | Mountain | Dragon Tears | Unlocks Artisan Table, blast furnace |
| Yagluth | Plains | — | Currently endgame boss |
| The Queen | Mistlands | — | Requires Moder completion |

**Why this matters:** When users report progression issues, understanding what content each boss unlocks helps diagnose "stuck" players.

### Portal Restrictions

- **Cannot teleport:** All ores (copper, tin, iron, silver, black metal), dragon eggs, flametal
- **V+ can modify:** `[Server] enforceMod=true` + `[Items] noTeleportPrevention=true`
- **Common ask:** "Let us teleport with ore" → `config_set Items enabled true`, `config_set Items noTeleportPrevention true`

### Biome Difficulty Tiers

Meadows → Black Forest → Swamp → Mountain → Plains → Mistlands → Ashlands

### World Save Details

- World files: `<worldname>.db` (terrain/structures) + `<worldname>.fwl` (metadata)
- Character files: Stored client-side, not on server
- Save frequency: Every 20 minutes + on graceful shutdown
- **Critical:** Always stop server gracefully to trigger save

---

## Troubleshooting Guide

### Connection Issues

| Symptom | Likely Cause | Solution |
|---------|--------------|----------|
| "Server not responding" | Ports blocked | Check UFW: `sudo ufw status`, ensure 2456-2458/UDP open |
| "Incompatible version" | Game/server mismatch | Run `update_server`; players must update client |
| "Connection failed" | Server not running | Check `server_status`, review logs for crash |
| "Disconnected" (random) | Memory exhaustion | Check `server_status` memory, consider restart schedule |
| One player can't connect | Client-side issue | Player should verify game files on Steam |

### Mod-Related Problems

| Symptom | Cause | Solution |
|---------|-------|----------|
| BepInEx not loading | Missing doorstop files | Re-run `mods_update`, check `libdoorstop_x64.so` exists |
| NullReferenceException in logs | Mod conflict or missing dependency | Check mod dependencies, disable non-essential mods |
| Config changes not applying | Server not restarted | `server_restart` after config changes |
| V+ features not working | Section not enabled | Ensure `enabled=true` in the relevant config section |

### Server Crashes

**Diagnostic steps:**
1. `server_logs lines=200` — check last entries before crash
2. Look for: "OutOfMemory", "NullReference", "Assertion failed"
3. Check if crash correlates with: player count, auto-update time (5 AM), specific actions

**Common patterns:**
- OOM during events: Reduce `[Events]` settings
- Crash on player join: Mod version mismatch — ensure players have matching V+
- Crash during dungeon generation: Known issue, update server

### Log Patterns to Know

| Pattern | Meaning |
|---------|---------|
| "Got handshake from client" | Player connecting |
| "Got character ZDOID" | Player fully loaded |
| "Closing socket" | Player disconnected |
| "World saved" | Successful save |
| "Steam manager initialized" | Server ready |
| "Incompatible version" | Version mismatch |

---

## Valheim Plus Configuration Reference

### How Configuration Works

- File: `/home/steam/valheim-server/BepInEx/config/valheim_plus.cfg`
- Format: INI-style with `[Section]` headers
- **Every section requires `enabled=true`** to activate its settings
- Server restart required for changes to take effect

### Most Requested Settings

#### [Server] — Core Server Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `enabled` | false | Enable this section |
| `enforceMod` | true | Require clients have V+ |
| `maxPlayers` | 10 | Player limit (up to 64 with V+) |
| `dataRate` | 60 | Network send rate (increase to 150 for better responsiveness) |

#### [Map] — Map Sharing

| Setting | Default | Description |
|---------|---------|-------------|
| `shareMapProgression` | false | Share explored areas between players |
| `shareAllPins` | false | Share all map pins automatically |
| `exploreRadius` | 100 | Exploration reveal radius |

#### [Building] — Construction Tweaks

| Setting | Default | Description |
|---------|---------|-------------|
| `noInvalidPlacementRestriction` | false | Allow placing anywhere |
| `noWeatherDamage` | false | Rain doesn't damage buildings |
| `maximumPlacementDistance` | 5 | Build reach distance |

#### [Player] — Player Stats

| Setting | Default | Description |
|---------|---------|-------------|
| `baseMegingjordBuff` | 150 | Extra carry weight from belt |
| `baseMaximumWeight` | 300 | Base carry capacity |
| `autoRepair` | false | Auto-repair items at workbench |

#### [Items] — Item Behavior

| Setting | Default | Description |
|---------|---------|-------------|
| `noTeleportPrevention` | false | Allow teleporting with ores |
| `itemStackMultiplier` | 1 | Stack size multiplier |

### Quick Config Recipes

**Casual-friendly server:**
```ini
[Player] enabled=true, baseMaximumWeight=450
[Stamina] enabled=true, staminaRegenDelay=0.5
[Food] enabled=true, foodDurationMultiplier=2
```

**Quality-of-life without changing difficulty:**
```ini
[Map] enabled=true, shareMapProgression=true
[Inventory] enabled=true, mergeWithExistingStacks=true
[CraftFromChest] enabled=true, range=20
```

**Building-focused server:**
```ini
[Building] enabled=true, noWeatherDamage=true, noInvalidPlacementRestriction=true
[StructuralIntegrity] enabled=true, disableStructuralIntegrity=true
[Ward] enabled=true, wardRange=50
```

---

## Standard Operating Procedures

### Pre-Maintenance Checklist

Before any update, config change, or maintenance:
1. `server_status` — confirm current state, note player count
2. If players online: warn them, wait 5-10 min
3. `backup_create name="pre_maintenance"` — always backup first
4. Proceed with maintenance
5. `server_start` (if was running)
6. `server_logs lines=50` — verify clean startup

### Safe Update Procedure

1. `backup_create name="pre_update"`
2. `server_stop` (if running)
3. `update_all` (or `update_server` / `update_valheimplus` individually)
4. `server_start`
5. `server_logs lines=100 filter="error"` — check for issues
6. If errors: `backup_restore name="pre_update"`, notify user

### World Migration / Backup Recovery

1. `server_stop`
2. `backup_list` — identify correct backup
3. `backup_restore name="<backup_name>"`
4. `server_start`
5. `server_logs` — confirm world loaded

### Adding New Mods

1. `mods_search "<mod_name>"` — find exact mod identifier
2. Review results — note dependencies
3. `server_stop` — always stop before mod changes
4. `mods_add "<Owner-ModName>"`
5. `server_start`
6. `server_logs lines=100` — check for mod load errors

### Diagnosing "Server Won't Start"

1. `server_status` — check state
2. `server_logs lines=200` — look for errors
3. Common fixes:
   - Port conflict: `ss -tulpn | grep 2456`
   - Permission issue: files must be owned by `steam` user
   - Corrupted save: try restoring from backup
   - Mod issue: check BepInEx loading in logs

---

## Quick Reference

### Port Requirements

| Port | Protocol | Purpose |
|------|----------|---------|
| 2456 | UDP | Game traffic (primary) |
| 2457 | UDP | Steam query |
| 2458 | UDP | Steam master server |

### Memory Guidelines

| Players | Recommended RAM |
|---------|-----------------|
| 1-4 | 4 GB |
| 5-10 | 8 GB |
| 10-20 | 12 GB |
| 20+ | 16 GB+ (schedule restarts every 12-24h) |

### Common Requests → Tool Sequence

| User Says | Tool Sequence |
|-----------|--------------|
| "Check the server" | `server_status` |
| "Restart the server" | `server_restart` (warn if players online) |
| "Enable map sharing" | `config_set Map enabled true` → `config_set Map shareMapProgression true` → `server_restart` |
| "Teleport with ores" | `config_set Items enabled true` → `config_set Items noTeleportPrevention true` → `server_restart` |
| "Update everything" | Pre-maintenance checklist → `update_all` → verify |
| "Server crashed" | `server_logs lines=200` → diagnose → fix → `server_start` |
| "Make a backup" | `backup_create` |
| "Roll back" | `backup_list` → `backup_restore` |
| "Add a mod" | `mods_search` → `server_stop` → `mods_add` → `server_start` |
