#!/usr/bin/env bash
# Install HF Propagation for the current user (no root needed).
#   packaging/install.sh            -> ~/.local
#   HFPROP_PREFIX=/opt/x packaging/install.sh
#   PYTHON=/path/to/python3.12 packaging/install.sh      # use a specific Python (needs 3.10 or newer)
set -euo pipefail
PY="${PYTHON:-python3}"
PREFIX="${HFPROP_PREFIX:-$HOME/.local}"
SRC="$(cd "$(dirname "$0")/.." && pwd)"
VENV="$PREFIX/share/hfprop/venv"

# Friendly checks before installing (the window toolkit needs Python 3.10+ and, on ARM, a 64-bit system)
if ! "$PY" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null; then
  echo "This needs Python 3.10 or newer; found: $($PY --version 2>&1)."
  echo "On Raspberry Pi OS that means Debian 12 'Bookworm' or newer, or see docs/Getting-Started.md for a newer Python on an older system."
  exit 1
fi
if [ "$(getconf LONG_BIT 2>/dev/null)" = "32" ]; then
  echo "This is a 32-bit system (even if 'uname -m' says aarch64, the programs installed are 32-bit)."
  echo "The window toolkit has no 32-bit Linux build. On a Raspberry Pi, install the 64-bit Raspberry Pi OS."
  exit 1
fi

echo "Installing into $PREFIX ..."
"$PY" -m venv "$VENV"
"$VENV/bin/pip" install --quiet --upgrade pip
rm -rf "$SRC/build"
"$VENV/bin/pip" install --quiet "$SRC"                                   # dependencies
"$VENV/bin/pip" install --quiet --force-reinstall --no-deps "$SRC"       # always replace our own code

mkdir -p "$PREFIX/bin" "$PREFIX/share/applications" "$PREFIX/share/icons/hicolor/scalable/apps"
ln -sf "$VENV/bin/hfprop-app" "$PREFIX/bin/hfprop-app"
ln -sf "$VENV/bin/hfprop" "$PREFIX/bin/hfprop"
cp "$SRC/packaging/hfprop.svg" "$PREFIX/share/icons/hicolor/scalable/apps/hfprop.svg"
sed "s#@EXEC@#$PREFIX/bin/hfprop-app#" "$SRC/packaging/hfprop.desktop.in" > "$PREFIX/share/applications/hfprop.desktop"
command -v update-desktop-database >/dev/null && update-desktop-database "$PREFIX/share/applications" 2>/dev/null || true
command -v gtk-update-icon-cache >/dev/null && gtk-update-icon-cache -q "$PREFIX/share/icons/hicolor" 2>/dev/null || true

echo
echo "Done.  Start it from your application menu ('HF Propagation') or run:  $PREFIX/bin/hfprop-app"
echo "Command line version:  $PREFIX/bin/hfprop FN31"
echo "(The first launch downloads the Flet window runtime, so it needs internet once.)"
