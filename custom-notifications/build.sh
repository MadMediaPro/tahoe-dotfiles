#!/usr/bin/env bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILD_DIR="$DIR/build"
USER_PLUGIN_DIR="$HOME/.local/lib/qt6/plugins/plasma/applets"

echo "==> Configuring with CMake..."
cmake -S "$DIR" -B "$BUILD_DIR" -G Ninja

echo "==> Building custom notifications..."
ninja -C "$BUILD_DIR"

echo "==> Installing to $USER_PLUGIN_DIR..."
mkdir -p "$USER_PLUGIN_DIR"
cp "$BUILD_DIR/bin/plasma/applets/org.kde.plasma.notifications.so" "$USER_PLUGIN_DIR/"

echo "==> Restarting plasmashell..."
systemctl --user restart plasma-plasmashell.service

echo "==> Done! Testing notification..."
notify-send "Custom Notifications" "Plugin berhasil di-rebuild dan di-reload!"
