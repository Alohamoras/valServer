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
STEAM_USER="steam"
STEAM_HOME="/home/${STEAM_USER}"
STEAMCMD_DIR="${STEAM_HOME}/steamcmd"
VALHEIM_DIR="${STEAM_HOME}/valheim-server"
VALHEIM_DATA_DIR="${STEAM_HOME}/.config/unity3d/IronGate/Valheim"
VALHEIM_PLUS_URL="https://github.com/Grantapher/ValheimPlus/releases/latest/download/UnixServer.tar.gz"

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
apt-get install -y lib32gcc-s1 lib32stdc++6 libsdl2-2.0-0 libsdl2-2.0-0:i386 curl wget tar jq python3.12-venv

# --- Create steam user ---
if ! id "$STEAM_USER" &>/dev/null; then
    log_info "Creating ${STEAM_USER} user..."
    useradd -m -s /bin/bash "$STEAM_USER"
else
    log_info "User ${STEAM_USER} already exists"
fi

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

# --- Install Valheim Plus ---
log_info "Installing Valheim Plus..."
cd "$VALHEIM_DIR"

# Backup original files
sudo -u "$STEAM_USER" mkdir -p "${VALHEIM_DIR}/backup_original"
for file in valheim_server.x86_64 UnityPlayer.so; do
    if [[ -f "$file" ]] && [[ ! -f "${VALHEIM_DIR}/backup_original/$file" ]]; then
        sudo -u "$STEAM_USER" cp "$file" "${VALHEIM_DIR}/backup_original/"
    fi
done

# Download and extract Valheim Plus
TEMP_DIR=$(mktemp -d)
wget -q -O "${TEMP_DIR}/valheimplus.tar.gz" "$VALHEIM_PLUS_URL"
tar -xzf "${TEMP_DIR}/valheimplus.tar.gz" -C "$VALHEIM_DIR"
rm -rf "$TEMP_DIR"

# Download Valheim Plus config file (not included in tarball, and in-game download fails)
VALHEIM_PLUS_VERSION=$(basename "$(curl -Ls -o /dev/null -w %{url_effective} https://github.com/Grantapher/ValheimPlus/releases/latest)")
VALHEIM_PLUS_CONFIG_URL="https://github.com/Grantapher/ValheimPlus/releases/download/${VALHEIM_PLUS_VERSION}/valheim_plus.cfg"
wget -q -O "${VALHEIM_DIR}/BepInEx/config/valheim_plus.cfg" "$VALHEIM_PLUS_CONFIG_URL"

chown -R "${STEAM_USER}:${STEAM_USER}" "$VALHEIM_DIR"

# --- Create server start script ---
log_info "Creating server start script..."
cat > "${VALHEIM_DIR}/start_server.sh" << 'STARTSCRIPT'
#!/bin/bash
export templdpath=$LD_LIBRARY_PATH
export LD_LIBRARY_PATH=./doorstop_libs:./linux64:$LD_LIBRARY_PATH
export LD_PRELOAD="libdoorstop_x64.so:$LD_PRELOAD"
export SteamAppId=892970

# Enable Valheim Plus (BepInEx/Doorstop)
export DOORSTOP_ENABLE=TRUE
export DOORSTOP_INVOKE_DLL_PATH=./BepInEx/core/BepInEx.Preloader.dll
export DOORSTOP_CORLIB_OVERRIDE_PATH=./unstripped_corlib

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
# Updates both Valheim Dedicated Server and Valheim Plus
#

STEAMCMD_DIR="STEAMCMD_DIR_PLACEHOLDER"
VALHEIM_DIR="VALHEIM_DIR_PLACEHOLDER"
VALHEIM_PLUS_URL="VALHEIM_PLUS_URL_PLACEHOLDER"
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

# Update Valheim Dedicated Server
log "Updating Valheim Dedicated Server..."
"${STEAMCMD_DIR}/steamcmd.sh" \
    +force_install_dir "$VALHEIM_DIR" \
    +login anonymous \
    +app_update 896660 validate \
    +quit >> "$LOG_FILE" 2>&1

# Update Valheim Plus
log "Updating Valheim Plus..."
TEMP_DIR=$(mktemp -d)
if wget -q -O "${TEMP_DIR}/valheimplus.tar.gz" "$VALHEIM_PLUS_URL"; then
    tar -xzf "${TEMP_DIR}/valheimplus.tar.gz" -C "$VALHEIM_DIR"
    log "Valheim Plus updated successfully"
else
    log "WARNING: Failed to download Valheim Plus update"
fi
rm -rf "$TEMP_DIR"

# Restart server if it was running
if [ "$SERVER_WAS_RUNNING" = true ]; then
    log "Starting Valheim server..."
    systemctl start valheim.service
fi

log "=== Update complete ==="
UPDATESCRIPT

sed -i "s|STEAMCMD_DIR_PLACEHOLDER|${STEAMCMD_DIR}|g" "${STEAM_HOME}/update-valheim.sh"
sed -i "s|VALHEIM_DIR_PLACEHOLDER|${VALHEIM_DIR}|g" "${STEAM_HOME}/update-valheim.sh"
sed -i "s|VALHEIM_PLUS_URL_PLACEHOLDER|${VALHEIM_PLUS_URL}|g" "${STEAM_HOME}/update-valheim.sh"

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

# --- Setup MCP Server for Claude Code ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MCP_DIR="${SCRIPT_DIR}/mcp-server"

if [[ -d "$MCP_DIR" ]]; then
    log_info "Setting up MCP server for Claude Code..."

    # Create venv and install dependencies
    cd "$MCP_DIR"
    python3 -m venv venv
    source venv/bin/activate
    pip install -q -r requirements.txt
    deactivate

    # Configure Claude Code MCP server for the user who ran sudo
    if [[ -n "$SUDO_USER" ]]; then
        CLAUDE_USER="$SUDO_USER"
    else
        CLAUDE_USER="$USER"
    fi

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
