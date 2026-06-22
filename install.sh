#!/bin/bash
#
# Valheim Dedicated Server Installer for Ubuntu 24.04
# Includes: SteamCMD, Valheim Dedicated Server, Valheim Plus, systemd service, auto-updates
#

set -e

# --- Usage ---
usage() {
    echo "Usage: $0 [-n server_name] [-w world_name] [-p password] [-y]"
    echo ""
    echo "Options:"
    echo "  -n    Server name (displayed in server list)"
    echo "  -w    World name (name of the world save)"
    echo "  -p    Server password (minimum 5 characters)"
    echo "  -y    Skip confirmation prompt"
    echo "  -s    Start server after installation"
    echo "  -h    Show this help message"
    echo ""
    echo "Examples:"
    echo "  Interactive:  sudo $0"
    echo "  One-liner:    sudo $0 -n \"My Server\" -w \"MyWorld\" -p \"secret123\" -y -s"
    exit 0
}

# --- Parse command line arguments ---
SERVER_NAME=""
WORLD_NAME=""
SERVER_PASSWORD=""
AUTO_CONFIRM=false
AUTO_START=false

while getopts "n:w:p:ysh" opt; do
    case $opt in
        n) SERVER_NAME="$OPTARG" ;;
        w) WORLD_NAME="$OPTARG" ;;
        p) SERVER_PASSWORD="$OPTARG" ;;
        y) AUTO_CONFIRM=true ;;
        s) AUTO_START=true ;;
        h) usage ;;
        *) usage ;;
    esac
done

# --- Configuration ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STEAM_USER="steam"
STEAM_HOME="/home/${STEAM_USER}"
STEAMCMD_DIR="${STEAM_HOME}/steamcmd"
VALHEIM_DIR="${STEAM_HOME}/valheim-server"
VALHEIM_DATA_DIR="${STEAM_HOME}/.config/unity3d/IronGate/Valheim"
VMM_CONFIG="${STEAM_HOME}/vmm_config.toml"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# --- Pre-flight checks ---
if [[ $EUID -ne 0 ]]; then
    log_error "This script must be run as root (use sudo)"
    exit 1
fi

if ! grep -q "Ubuntu 24" /etc/os-release 2>/dev/null; then
    log_warn "This script is designed for Ubuntu 24.04. Proceeding anyway..."
fi

# --- Prompt for server configuration (if not provided via flags) ---
echo ""
echo "=== Valheim Server Configuration ==="
echo ""

if [[ -z "$SERVER_NAME" ]]; then
    read -p "Server Name (displayed in server list): " SERVER_NAME
    while [[ -z "$SERVER_NAME" ]]; do
        log_error "Server name cannot be empty"
        read -p "Server Name: " SERVER_NAME
    done
fi

if [[ -z "$WORLD_NAME" ]]; then
    read -p "World Name (name of the world save): " WORLD_NAME
    while [[ -z "$WORLD_NAME" ]]; do
        log_error "World name cannot be empty"
        read -p "World Name: " WORLD_NAME
    done
fi

if [[ -z "$SERVER_PASSWORD" ]]; then
    while true; do
        read -s -p "Server Password (min 5 characters, won't be displayed): " SERVER_PASSWORD
        echo ""
        if [[ ${#SERVER_PASSWORD} -lt 5 ]]; then
            log_error "Password must be at least 5 characters"
        else
            read -s -p "Confirm Password: " SERVER_PASSWORD_CONFIRM
            echo ""
            if [[ "$SERVER_PASSWORD" != "$SERVER_PASSWORD_CONFIRM" ]]; then
                log_error "Passwords do not match"
            else
                break
            fi
        fi
    done
else
    if [[ ${#SERVER_PASSWORD} -lt 5 ]]; then
        log_error "Password must be at least 5 characters"
        exit 1
    fi
fi

echo ""
log_info "Configuration:"
log_info "  Server Name: ${SERVER_NAME}"
log_info "  World Name:  ${WORLD_NAME}"
log_info "  Password:    ********"
echo ""

if [[ "$AUTO_CONFIRM" != true ]]; then
    read -p "Proceed with installation? (y/n): " CONFIRM
    if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then
        log_info "Installation cancelled"
        exit 0
    fi
fi

# --- Install dependencies ---
log_info "Installing dependencies..."
dpkg --add-architecture i386
apt-get update
apt-get install -y lib32gcc-s1 lib32stdc++6 libsdl2-2.0-0 libsdl2-2.0-0:i386 curl wget tar jq python3-venv git build-essential acl

# --- Create steam user ---
if ! id "$STEAM_USER" &>/dev/null; then
    log_info "Creating ${STEAM_USER} user..."
    useradd -m -s /bin/bash "$STEAM_USER"
else
    log_info "User ${STEAM_USER} already exists"
fi

# --- Install Rust and Valheim Mod Manager (vmm) ---
log_info "Installing Rust for ${STEAM_USER} user..."
if ! sudo -u "$STEAM_USER" bash -c 'command -v cargo &>/dev/null'; then
    sudo -u "$STEAM_USER" bash -c 'curl --proto "=https" --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y'
else
    log_info "Rust already installed for ${STEAM_USER}"
fi

log_info "Installing Valheim Mod Manager (vmm)..."
VMM_REPO_DIR="${STEAM_HOME}/valheim-mod-manager"
if [[ ! -d "$VMM_REPO_DIR" ]]; then
    sudo -u "$STEAM_USER" git clone https://github.com/endoze/valheim-mod-manager.git "$VMM_REPO_DIR"
fi
cd "$VMM_REPO_DIR"
sudo -u "$STEAM_USER" bash -c "source ${STEAM_HOME}/.cargo/env && cargo install --path ."
log_info "vmm installed successfully"

# --- Install SteamCMD ---
log_info "Installing SteamCMD..."
sudo -u "$STEAM_USER" mkdir -p "$STEAMCMD_DIR"
cd "$STEAMCMD_DIR"

if [[ ! -f "${STEAMCMD_DIR}/steamcmd.sh" ]]; then
    sudo -u "$STEAM_USER" wget -q "https://steamcdn-a.akamaihd.net/client/installer/steamcmd_linux.tar.gz"
    sudo -u "$STEAM_USER" tar -xzf steamcmd_linux.tar.gz
    rm -f steamcmd_linux.tar.gz
fi

# --- Install Valheim Dedicated Server ---
log_info "Installing Valheim Dedicated Server (this may take a while)..."
sudo -u "$STEAM_USER" mkdir -p "$VALHEIM_DIR"

sudo -u "$STEAM_USER" "${STEAMCMD_DIR}/steamcmd.sh" \
    +force_install_dir "$VALHEIM_DIR" \
    +login anonymous \
    +app_update 896660 validate \
    +quit

# --- Install Mods via vmm (BepInEx + Valheim Plus) ---
log_info "Configuring Valheim Mod Manager..."
cd "$STEAM_HOME"

# Backup original files before mod installation
sudo -u "$STEAM_USER" mkdir -p "${VALHEIM_DIR}/backup_original"
cd "$VALHEIM_DIR"
for file in valheim_server.x86_64 UnityPlayer.so; do
    if [[ -f "$file" ]] && [[ ! -f "${VALHEIM_DIR}/backup_original/$file" ]]; then
        sudo -u "$STEAM_USER" cp "$file" "${VALHEIM_DIR}/backup_original/"
    fi
done

# Create vmm configuration
log_info "Creating vmm_config.toml..."
cat > "$VMM_CONFIG" << EOF
mod_list = ["denikson-BepInExPack_Valheim", "Grantapher-ValheimPlus_Grantapher_Temporary"]
log_level = "info"
cache_dir = "${STEAM_HOME}/.config/vmm"
install_dir = "${VALHEIM_DIR}"
EOF
chown "${STEAM_USER}:${STEAM_USER}" "$VMM_CONFIG"

# Create vmm cache directory
sudo -u "$STEAM_USER" mkdir -p "${STEAM_HOME}/.config/vmm"

# Install mods using vmm
log_info "Downloading mod manifest from Thunderstore..."
cd "$STEAM_HOME"
sudo -u "$STEAM_USER" bash -c "source ${STEAM_HOME}/.cargo/env && vmm update manifest"

log_info "Installing mods (BepInEx + Valheim Plus)..."
sudo -u "$STEAM_USER" bash -c "source ${STEAM_HOME}/.cargo/env && vmm update mods"

# vmm places mods in subfolders - copy contents to correct locations
log_info "Copying mod files to correct locations..."
BEPINEX_PACK_DIR="${VALHEIM_DIR}/denikson-BepInExPack_Valheim/BepInExPack_Valheim"
if [[ -d "$BEPINEX_PACK_DIR" ]]; then
    cp -r "${BEPINEX_PACK_DIR}"/* "${VALHEIM_DIR}/"
fi

VPLUS_DIR="${VALHEIM_DIR}/Grantapher-ValheimPlus_Grantapher_Temporary"
if [[ -d "$VPLUS_DIR/BepInEx" ]]; then
    cp -r "${VPLUS_DIR}/BepInEx"/* "${VALHEIM_DIR}/BepInEx/"
fi

chown -R "${STEAM_USER}:${STEAM_USER}" "$VALHEIM_DIR"

# --- Create server start script ---
log_info "Creating server start script..."
cat > "${VALHEIM_DIR}/start_server.sh" << 'STARTSCRIPT'
#!/bin/bash
# BepInEx/Doorstop settings
export DOORSTOP_ENABLED=1
export DOORSTOP_TARGET_ASSEMBLY=./BepInEx/core/BepInEx.Preloader.dll

export LD_LIBRARY_PATH="./doorstop_libs:./linux64:$LD_LIBRARY_PATH"
export LD_PRELOAD="libdoorstop_x64.so:$LD_PRELOAD"
export SteamAppId=892970

cd "VALHEIM_DIR_PLACEHOLDER"

./valheim_server.x86_64 \
    -nographics \
    -batchmode \
    -port 2456 \
    -public 1 \
    -name "SERVER_NAME_PLACEHOLDER" \
    -world "WORLD_NAME_PLACEHOLDER" \
    -password "SERVER_PASSWORD_PLACEHOLDER" \
    -savedir "VALHEIM_DATA_DIR_PLACEHOLDER"
STARTSCRIPT

# Replace placeholders
sed -i "s|VALHEIM_DIR_PLACEHOLDER|${VALHEIM_DIR}|g" "${VALHEIM_DIR}/start_server.sh"
sed -i "s|SERVER_NAME_PLACEHOLDER|${SERVER_NAME}|g" "${VALHEIM_DIR}/start_server.sh"
sed -i "s|WORLD_NAME_PLACEHOLDER|${WORLD_NAME}|g" "${VALHEIM_DIR}/start_server.sh"
sed -i "s|SERVER_PASSWORD_PLACEHOLDER|${SERVER_PASSWORD}|g" "${VALHEIM_DIR}/start_server.sh"
sed -i "s|VALHEIM_DATA_DIR_PLACEHOLDER|${VALHEIM_DATA_DIR}|g" "${VALHEIM_DIR}/start_server.sh"

chmod +x "${VALHEIM_DIR}/start_server.sh"
chown "${STEAM_USER}:${STEAM_USER}" "${VALHEIM_DIR}/start_server.sh"

# Create save directory
sudo -u "$STEAM_USER" mkdir -p "$VALHEIM_DATA_DIR"

# --- Create systemd service ---
log_info "Creating systemd service..."
cat > /etc/systemd/system/valheim.service << EOF
[Unit]
Description=Valheim Dedicated Server
Wants=network-online.target
After=network-online.target

[Service]
Type=simple
User=${STEAM_USER}
Group=${STEAM_USER}
WorkingDirectory=${VALHEIM_DIR}
ExecStart=${VALHEIM_DIR}/start_server.sh
Restart=on-failure
RestartSec=30
StandardOutput=journal
StandardError=journal

# Give the server time to save on shutdown
TimeoutStopSec=120
KillSignal=SIGINT

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable valheim.service

# --- Create update script ---
log_info "Creating update script..."
cat > "${STEAM_HOME}/update-valheim.sh" << 'UPDATESCRIPT'
#!/bin/bash
#
# Valheim Server Update Script
# Updates Valheim Dedicated Server and all mods via vmm.
#
# Invoked by /etc/cron.d/valheim-update as root. SteamCMD and vmm must run
# as the steam user — running them as root sends Steam state to /root/Steam
# (causing "Missing configuration") and breaks vmm's PATH lookup (~/.cargo/env
# resolves $HOME=/root, so /home/steam/.cargo/bin/vmm is never on PATH).
#

STEAMCMD_DIR="STEAMCMD_DIR_PLACEHOLDER"
VALHEIM_DIR="VALHEIM_DIR_PLACEHOLDER"
STEAM_USER="STEAM_USER_PLACEHOLDER"
LOG_FILE="/var/log/valheim-update.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log "=== Starting Valheim update ==="

# Check if server is running
SERVER_WAS_RUNNING=false
if systemctl is-active --quiet valheim.service; then
    SERVER_WAS_RUNNING=true
    log "Stopping Valheim server..."
    systemctl stop valheim.service
    sleep 10
fi

# Update Valheim Dedicated Server (must run as steam user — see header)
log "Updating Valheim Dedicated Server..."
if sudo -u "$STEAM_USER" -H "${STEAMCMD_DIR}/steamcmd.sh" \
    +force_install_dir "$VALHEIM_DIR" \
    +login anonymous \
    +app_update 896660 validate \
    +quit >> "$LOG_FILE" 2>&1; then
    log "Valheim server updated successfully"
else
    log "WARNING: SteamCMD update failed (exit $?)"
fi

# Update mods via vmm (must run as steam user — see header)
log "Updating mod manifest from Thunderstore..."
if sudo -u "$STEAM_USER" -H bash -lc 'source ~/.cargo/env && cd ~ && vmm update manifest' >> "$LOG_FILE" 2>&1; then
    log "Mod manifest updated successfully"
else
    log "WARNING: Failed to update mod manifest"
fi

log "Updating mods..."
if sudo -u "$STEAM_USER" -H bash -lc 'source ~/.cargo/env && cd ~ && vmm update mods' >> "$LOG_FILE" 2>&1; then
    log "Mods updated successfully"
else
    log "WARNING: Failed to update mods"
fi

# Restart server if it was running
if [ "$SERVER_WAS_RUNNING" = true ]; then
    log "Starting Valheim server..."
    systemctl start valheim.service
fi

log "=== Update complete ==="
UPDATESCRIPT

sed -i "s|STEAMCMD_DIR_PLACEHOLDER|${STEAMCMD_DIR}|g" "${STEAM_HOME}/update-valheim.sh"
sed -i "s|VALHEIM_DIR_PLACEHOLDER|${VALHEIM_DIR}|g" "${STEAM_HOME}/update-valheim.sh"
sed -i "s|STEAM_USER_PLACEHOLDER|${STEAM_USER}|g" "${STEAM_HOME}/update-valheim.sh"

chmod +x "${STEAM_HOME}/update-valheim.sh"
chown "${STEAM_USER}:${STEAM_USER}" "${STEAM_HOME}/update-valheim.sh"

# Create log file
touch /var/log/valheim-update.log
chown "${STEAM_USER}:${STEAM_USER}" /var/log/valheim-update.log

# --- Create cron job for daily updates at 5am EST ---
log_info "Setting up daily auto-update cron job (5:00 AM EST)..."

# 5am EST = 10:00 UTC (or 9:00 UTC during daylight saving)
# Using America/New_York timezone to handle DST automatically
cat > /etc/cron.d/valheim-update << EOF
# Valheim Server Auto-Update
# Runs daily at 5:00 AM Eastern Time
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin

0 5 * * * root TZ=America/New_York ${STEAM_HOME}/update-valheim.sh >> /var/log/valheim-update.log 2>&1
EOF

chmod 644 /etc/cron.d/valheim-update

# --- Configure firewall (if ufw is active) ---
if command -v ufw &>/dev/null && ufw status | grep -q "Status: active"; then
    log_info "Configuring UFW firewall..."
    ufw allow 2456:2458/udp comment "Valheim Server"
fi

# --- Determine the user who will run Claude Code (and the MCP server) ---
if [[ -n "$SUDO_USER" ]]; then
    CLAUDE_USER="$SUDO_USER"
else
    CLAUDE_USER="$USER"
fi

# --- Grant MCP user access to /home/steam paths ---
# The MCP server runs as $CLAUDE_USER (not root, not steam). By default
# /home/steam is 0750, which blocks even read access. Open up traversal and
# apply ACLs to the specific paths the MCP needs to read or write. Default
# ACLs make new files (e.g. valheim_plus.cfg generated on first server run,
# new backup archives) inherit the same permissions automatically.
if [[ -n "$CLAUDE_USER" ]] && [[ "$CLAUDE_USER" != "root" ]] && [[ "$CLAUDE_USER" != "$STEAM_USER" ]]; then
    log_info "Granting MCP user '${CLAUDE_USER}' access to ${STEAM_HOME} paths..."

    # Traversal into /home/steam
    chmod 755 "$STEAM_HOME"

    # Ensure the backup dir exists so we can apply a default ACL to it
    sudo -u "$STEAM_USER" mkdir -p "${STEAM_HOME}/valheim-backups"

    # Read+write on the files/dirs the MCP modifies
    setfacl    -m "u:${CLAUDE_USER}:rw"  "$VMM_CONFIG"
    setfacl -R -m "u:${CLAUDE_USER}:rwX" "${VALHEIM_DIR}/BepInEx/config" 2>/dev/null || true
    setfacl -d -m "u:${CLAUDE_USER}:rwX" "${VALHEIM_DIR}/BepInEx/config" 2>/dev/null || true
    setfacl -R -m "u:${CLAUDE_USER}:rwX" "${STEAM_HOME}/valheim-backups"
    setfacl -d -m "u:${CLAUDE_USER}:rwX" "${STEAM_HOME}/valheim-backups"

    # Read on the world saves dir (needed by backup_create)
    setfacl -R -m "u:${CLAUDE_USER}:rX" "${VALHEIM_DATA_DIR}" 2>/dev/null || true
    setfacl -d -m "u:${CLAUDE_USER}:rX" "${VALHEIM_DATA_DIR}" 2>/dev/null || true
fi

# --- Setup MCP Server for Claude Code ---
MCP_DIR="${SCRIPT_DIR}/mcp-server"

if [[ -d "$MCP_DIR" ]]; then
    log_info "Setting up MCP server for Claude Code..."

    # Create venv and install dependencies
    cd "$MCP_DIR"
    python3 -m venv venv
    source venv/bin/activate
    pip install -q -r requirements.txt
    deactivate

    # Check if claude CLI is available and register MCP server
    if command -v claude &>/dev/null; then
        log_info "Registering MCP server with Claude Code..."
        sudo -u "$CLAUDE_USER" claude mcp add --transport stdio valheim -- "${MCP_DIR}/venv/bin/python" "${MCP_DIR}/valheim_server.py" 2>/dev/null || true
        log_info "Claude Code MCP server registered for user ${CLAUDE_USER}"
    else
        log_warn "Claude Code CLI not found. To manually register the MCP server, run:"
        log_warn "  claude mcp add --transport stdio valheim -- ${MCP_DIR}/venv/bin/python ${MCP_DIR}/valheim_server.py"
    fi
else
    log_warn "MCP server directory not found at ${MCP_DIR}, skipping Claude Code setup"
fi

# --- Print summary ---
echo ""
echo "=============================================="
echo -e "${GREEN}    Installation Complete!${NC}"
echo "=============================================="
echo ""
echo "Server Details:"
echo "  Server Name:     ${SERVER_NAME}"
echo "  World Name:      ${WORLD_NAME}"
echo "  Ports:           2456-2458 UDP"
echo ""
echo "File Locations:"
echo "  Server Files:    ${VALHEIM_DIR}"
echo "  World Saves:     ${VALHEIM_DATA_DIR}"
echo "  Start Script:    ${VALHEIM_DIR}/start_server.sh"
echo "  Update Script:   ${STEAM_HOME}/update-valheim.sh"
echo ""
echo "Mod Management (vmm):"
echo "  Config:          ${VMM_CONFIG}"
echo "  Add mod:         sudo -u steam bash -c 'source ~/.cargo/env && vmm search <name>'"
echo "  Update mods:     sudo -u steam bash -c 'source ~/.cargo/env && vmm update manifest && vmm update mods'"
echo ""
echo "Valheim Plus Configuration:"
echo -e "  ${YELLOW}${VALHEIM_DIR}/BepInEx/config/valheim_plus.cfg${NC}"
echo "  Edit this file to customize Valheim Plus settings"
echo ""
echo "Server Management Commands:"
echo "  Start:           sudo systemctl start valheim"
echo "  Stop:            sudo systemctl stop valheim"
echo "  Restart:         sudo systemctl restart valheim"
echo "  Status:          sudo systemctl status valheim"
echo "  View Logs:       sudo journalctl -u valheim -f"
echo ""
echo "Auto-Updates:"
echo "  Schedule:        Daily at 5:00 AM Eastern Time"
echo "  Update Log:      /var/log/valheim-update.log"
echo "  Manual Update:   sudo ${STEAM_HOME}/update-valheim.sh"
echo ""
if [[ -d "$MCP_DIR" ]]; then
echo "Claude Code MCP Server:"
echo "  Status:          Configured for user ${CLAUDE_USER}"
echo "  Note:            Restart Claude Code to enable MCP tools"
echo ""
fi
echo "=============================================="
echo ""
if [[ "$AUTO_START" == true ]]; then
    START_NOW="y"
elif [[ "$AUTO_CONFIRM" == true ]]; then
    START_NOW="n"
else
    read -p "Start the server now? (y/n): " START_NOW
fi

if [[ "$START_NOW" =~ ^[Yy]$ ]]; then
    log_info "Starting Valheim server..."
    systemctl start valheim.service
    sleep 3
    systemctl status valheim.service --no-pager
    echo ""
    log_info "Server is starting. Use 'sudo journalctl -u valheim -f' to monitor logs"
else
    log_info "You can start the server later with: sudo systemctl start valheim"
fi
