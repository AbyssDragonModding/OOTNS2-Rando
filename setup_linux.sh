#!/usr/bin/env bash
# ===========================================================================================
#  OoT Remake Randomizer - first-time setup for Linux
#
#  Run it once from a terminal in this folder:   bash setup_linux.sh
#  It:
#    1. finds Python 3.14 or newer, or offers to install it (your package manager, or uv if the
#       package manager doesn't have 3.14),
#    2. creates a private Python environment in ".venv" inside this folder and installs
#       requirements.txt into it (nothing is installed into the system Python),
#    3. adds an "OoT Remake Randomizer" entry to your application menu and makes .pyw files open
#       with Python, for your user only.
#  It asks before anything that needs sudo. Run it again after downloading a new version.
# ===========================================================================================
set -u
cd "$(dirname "$(readlink -f "$0")")" || exit 1
HERE="$(pwd)"
VENV="$HERE/.venv"

say()  { printf '\n\033[1m%s\033[0m\n' "$*"; }
warn() { printf '\033[33m%s\033[0m\n' "$*"; }
fail() { printf '\n\033[31m%s\033[0m\n' "$*"; exit 1; }
ask()  { local a; read -r -p "$1 [Y/n] " a; [[ -z "$a" || "$a" =~ ^[Yy] ]]; }

is_new_enough() { "$1" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 14) else 1)' >/dev/null 2>&1; }

find_python() {
    PY=""
    local c
    for c in python3.16 python3.15 python3.14 python3 python "$HOME/.local/bin/python3.14"; do
        if command -v "$c" >/dev/null 2>&1 && is_new_enough "$(command -v "$c")"; then
            PY="$(command -v "$c")"; return 0
        fi
    done
    return 1
}

install_with_uv() {
    say "Installing Python 3.14 with uv (from astral.sh, installed into your home folder)..."
    if ! command -v uv >/dev/null 2>&1 && [ ! -x "$HOME/.local/bin/uv" ]; then
        command -v curl >/dev/null 2>&1 || fail "curl is needed to download uv. Install curl and run this again."
        curl -LsSf https://astral.sh/uv/install.sh | sh || fail "Installing uv failed."
    fi
    local UV; UV="$(command -v uv || echo "$HOME/.local/bin/uv")"
    "$UV" python install 3.14 || fail "uv couldn't install Python 3.14."
    PY="$("$UV" python find 3.14)" || fail "uv installed Python 3.14 but couldn't find it."
}

# ---- 1. Python -------------------------------------------------------------------------------
say "[1/3] Looking for Python 3.14 or newer..."
if find_python; then
    echo "Found: $PY ($("$PY" --version))"
else
    warn "Python 3.14 or newer isn't installed."
    if command -v apt-get >/dev/null 2>&1; then
        PKGS="python3.14 python3.14-venv"
        if ask "Install $PKGS with apt (needs sudo)?"; then
            sudo apt-get update
            if ! sudo apt-get install -y $PKGS; then
                # Ubuntu: Python 3.14 comes from the deadsnakes archive on older releases
                if grep -qi ubuntu /etc/os-release && ask "Not in your apt sources. Add the deadsnakes PPA (Ubuntu) and retry?"; then
                    sudo apt-get install -y software-properties-common
                    sudo add-apt-repository -y ppa:deadsnakes/ppa && sudo apt-get update && sudo apt-get install -y $PKGS
                fi
            fi
        fi
    elif command -v dnf >/dev/null 2>&1; then
        ask "Install python3.14 with dnf (needs sudo)?" && sudo dnf install -y python3.14
    elif command -v pacman >/dev/null 2>&1; then
        ask "Update python with pacman (needs sudo)?" && sudo pacman -S --needed --noconfirm python
    elif command -v zypper >/dev/null 2>&1; then
        ask "Install python314 with zypper (needs sudo)?" && sudo zypper install -y python314
    fi
    if ! find_python; then
        warn "Your package manager didn't provide Python 3.14."
        ask "Install it with uv instead (no sudo needed)?" || fail "Install Python 3.14 or newer, then run this again."
        install_with_uv
    fi
    echo "Using: $PY ($("$PY" --version))"
fi

# ---- 2. Private environment + packages -------------------------------------------------------
say "[2/3] Installing the randomizer's packages into .venv ..."
if [ ! -x "$VENV/bin/python" ] || ! is_new_enough "$VENV/bin/python"; then
    rm -rf "$VENV"
    if ! "$PY" -m venv "$VENV"; then
        fail "Creating the environment failed. On Debian/Ubuntu install the venv package
(for example: sudo apt-get install python3.14-venv) and run this again."
    fi
fi
"$VENV/bin/python" -m pip install --upgrade pip >/dev/null 2>&1
"$VENV/bin/python" -m pip install --upgrade -r requirements.txt || fail "Installing the packages failed. The messages above say why."

if ! command -v vulkaninfo >/dev/null 2>&1; then
    warn "Note: 'vulkaninfo' wasn't found. The randomizer's window needs a Vulkan driver
(Mesa: package mesa-vulkan-drivers / vulkan-radeon / vulkan-intel; NVIDIA: the proprietary driver)."
fi

# ---- 3. Menu entry and .pyw association ------------------------------------------------------
say "[3/3] Adding the menu entry and the .pyw file association..."
chmod +x "$HERE/run_linux.sh" "$HERE/setup_linux.sh" 2>/dev/null
APPS="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
MIME="${XDG_DATA_HOME:-$HOME/.local/share}/mime"
mkdir -p "$APPS" "$MIME/packages"

cat > "$APPS/ootr-remake-randomizer.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=OoT Remake Randomizer
Comment=Generate a randomizer mod for the Ocarina of Time remake
Exec="$HERE/run_linux.sh"
Path=$HERE
Terminal=false
Categories=Game;Utility;
EOF

# .pyw has no standard file type on Linux: register one and open it with this Python
cat > "$MIME/packages/x-python-pyw.xml" <<'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<mime-info xmlns="http://www.freedesktop.org/standards/shared-mime-info">
  <mime-type type="text/x-python-pyw">
    <comment>Python GUI script</comment>
    <glob pattern="*.pyw"/>
  </mime-type>
</mime-info>
EOF
cat > "$APPS/python-pyw-launcher.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Python (run script)
Exec="$VENV/bin/python" %f
MimeType=text/x-python-pyw;
NoDisplay=true
Terminal=false
EOF
command -v update-mime-database >/dev/null 2>&1 && update-mime-database "$MIME" >/dev/null 2>&1
command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database "$APPS" >/dev/null 2>&1
command -v xdg-mime >/dev/null 2>&1 && xdg-mime default python-pyw-launcher.desktop text/x-python-pyw
# .py files are left to open in your text editor: running any .py on double-click is risky.

say "Setup finished."
echo "Start the randomizer from your application menu (OoT Remake Randomizer), by double-clicking"
echo "ootr_remake.pyw, or with:   ./run_linux.sh"
