#!/usr/bin/env bash
# Remove HF Propagation. Your saved settings in ~/.cache/hfprop are left alone.
set -euo pipefail
PREFIX="${HFPROP_PREFIX:-$HOME/.local}"
rm -rf "$PREFIX/share/hfprop"
rm -f "$PREFIX/bin/hfprop-app" "$PREFIX/bin/hfprop" "$PREFIX/share/applications/hfprop.desktop" \
      "$PREFIX/share/icons/hicolor/scalable/apps/hfprop.svg"
echo "Removed."
