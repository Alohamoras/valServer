#!/bin/bash
#
# Valheim Dedicated Server Uninstaller
# Removes all components installed by install.sh
#

set -e

# --- Usage ---
usage() {
    echo "Usage: $0 [-y] [-k]"
    echo ""
    echo "Options:"
    echo "  -y    Skip all confirmation prompts (delete everything)"
    echo "  -k    Keep world saves and backups"
    echo "  -h    Show this help message"
    echo ""
    echo "Examples:"
    echo "  Interactive:     sudo $0"
    echo "  Full cleanup:    sudo $0 -y"
    echo "  Keep saves:      sudo $0 -y -k"
    exit 0
}

# --- Parse arguments ---
AUTO_CONFIRM=false
KEEP_SAVES=false

while getopts "ykh" opt; do
    case $opt in
        y) AUTO_CONFIRM=true ;;
        k) KEEP_SAVES=true ;;
        h) usage ;;
        *) usage ;;
    esac
done

# --- Configuration ---
STEAM_USER="steam"
STEAM_HOME="/home/${STEAM_USER}"
VALHEIM_DIR="${STEAM_HOME}/valheim-server"
VALHEIM_DATA_DIR="${STEAM_HOME}/.config/unity3d/IronGate/Valheim"
BACKUP_DIR="${STEAM_HOME}/valheim-backups"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# --- Pre-flight checks ---
if [[ $EUID -ne 0 ]]; then
    log_error "This script must be run as root (use sudo)"
    exit 1
fi

echo ""
echo "=============================================="
echo -e "${RED}    Valheim Server Uninstaller${NC}"
echo "=============================================="
echo ""

if [[ "$KEEP_SAVES" == true ]]; then
    log_info "World saves and backups will be KEPT"
else
    log_warn "This will DELETE world saves and backups!"
fi
echo ""

if [[ "$AUTO_CONFIRM" != true ]]; then
    read -p "Proceed with uninstallation? (y/n): " CONFIRM
    if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then
        log_info "Uninstallation cancelled"
        exit 0
    fi
fi

# --- Stop and disable service ---
log_info "Stopping Valheim service..."
if systemctl is-active --quiet valheim.service 2>/dev/null; then
    systemctl stop valheim.service
    log_info "Service stopped"
else
    log_info "Service not running"
fi

if systemctl is-enabled --quiet valheim.service 2>/dev/null; then
    systemctl disable valheim.service
    log_info "Service disabled"
fi

# --- Remove systemd service ---
log_info "Removing systemd service..."
if [[ -f /etc/systemd/system/valheim.service ]]; then
    rm -f /etc/systemd/system/valheim.service
    systemctl daemon-reload
    log_info "Systemd service removed"
else
    log_info "Systemd service not found"
fi

# --- Remove cron job ---
log_info "Removing cron job..."
if [[ -f /etc/cron.d/valheim-update ]]; then
    rm -f /etc/cron.d/valheim-update
    log_info "Cron job removed"
else
    log_info "Cron job not found"
fi

# --- Remove update log ---
if [[ -f /var/log/valheim-update.log ]]; then
    rm -f /var/log/valheim-update.log
    log_info "Update log removed"
fi

# --- Remove server files ---
log_info "Removing server files..."
if [[ -d "$VALHEIM_DIR" ]]; then
    rm -rf "$VALHEIM_DIR"
    log_info "Server directory removed: $VALHEIM_DIR"
else
    log_info "Server directory not found"
fi

# --- Remove SteamCMD ---
log_info "Removing SteamCMD..."
if [[ -d "${STEAM_HOME}/steamcmd" ]]; then
    rm -rf "${STEAM_HOME}/steamcmd"
    log_info "SteamCMD removed"
else
    log_info "SteamCMD not found"
fi

# --- Remove Steam cache/data ---
if [[ -d "${STEAM_HOME}/.steam" ]]; then
    rm -rf "${STEAM_HOME}/.steam"
    log_info "Steam cache removed"
fi
if [[ -d "${STEAM_HOME}/Steam" ]]; then
    rm -rf "${STEAM_HOME}/Steam"
    log_info "Steam data removed"
fi

# --- Remove Rust and vmm ---
log_info "Removing Rust and vmm..."
if [[ -d "${STEAM_HOME}/.cargo" ]]; then
    rm -rf "${STEAM_HOME}/.cargo"
    log_info "Cargo removed"
fi
if [[ -d "${STEAM_HOME}/.rustup" ]]; then
    rm -rf "${STEAM_HOME}/.rustup"
    log_info "Rustup removed"
fi
if [[ -d "${STEAM_HOME}/valheim-mod-manager" ]]; then
    rm -rf "${STEAM_HOME}/valheim-mod-manager"
    log_info "vmm repository removed"
fi
if [[ -f "${STEAM_HOME}/vmm_config.toml" ]]; then
    rm -f "${STEAM_HOME}/vmm_config.toml"
    log_info "vmm config removed"
fi
if [[ -d "${STEAM_HOME}/.config/vmm" ]]; then
    rm -rf "${STEAM_HOME}/.config/vmm"
    log_info "vmm cache removed"
fi

# --- Remove update script ---
if [[ -f "${STEAM_HOME}/update-valheim.sh" ]]; then
    rm -f "${STEAM_HOME}/update-valheim.sh"
    log_info "Update script removed"
fi

# --- Remove world saves and backups (unless -k) ---
if [[ "$KEEP_SAVES" != true ]]; then
    log_info "Removing world saves..."
    if [[ -d "$VALHEIM_DATA_DIR" ]]; then
        rm -rf "$VALHEIM_DATA_DIR"
        log_info "World saves removed: $VALHEIM_DATA_DIR"
    else
        log_info "World saves not found"
    fi

    log_info "Removing backups..."
    if [[ -d "$BACKUP_DIR" ]]; then
        rm -rf "$BACKUP_DIR"
        log_info "Backups removed: $BACKUP_DIR"
    else
        log_info "Backups not found"
    fi
else
    log_info "Keeping world saves: $VALHEIM_DATA_DIR"
    log_info "Keeping backups: $BACKUP_DIR"
fi

# --- Remove UFW rules (if ufw is active) ---
if command -v ufw &>/dev/null && ufw status | grep -q "Status: active"; then
    if ufw status | grep -q "2456:2458/udp"; then
        log_info "Removing UFW rules..."
        ufw delete allow 2456:2458/udp >/dev/null 2>&1 || true
        log_info "UFW rules removed"
    fi
fi

# --- Remove steam user (optional - commented out for safety) ---
# Uncomment if you want to remove the steam user entirely
# if id "$STEAM_USER" &>/dev/null; then
#     log_info "Removing steam user..."
#     userdel -r "$STEAM_USER" 2>/dev/null || true
#     log_info "Steam user removed"
# fi

# --- Summary ---
echo ""
echo "=============================================="
echo -e "${GREEN}    Uninstallation Complete${NC}"
echo "=============================================="
echo ""
log_info "The following have been removed:"
echo "  - Valheim server files"
echo "  - SteamCMD"
echo "  - Rust/Cargo and vmm"
echo "  - Systemd service"
echo "  - Cron job and update script"
if [[ "$KEEP_SAVES" != true ]]; then
    echo "  - World saves"
    echo "  - Backups"
fi
echo ""
log_info "The steam user account was kept (remove manually if needed)"
echo ""
