#!/usr/bin/env bash
# Install HF Propagation for the current user (no root needed).
#   packaging/install.sh            -> ~/.local
#   HFPROP_PREFIX=/opt/x packaging/install.sh
set -euo pipefail
PREFIX="${HFPROP_PREFIX:-$HOME/.local}"
SRC="$(cd "$(dirname "$0")/.." && pwd)"
VENV="$PREFIX/share/hfprop/venv"

echo "Installing into $PREFIX ..."
python3 -m venv "$VENV"
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
