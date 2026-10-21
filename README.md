# 🍎 macOS Tahoe Dotfiles for KDE Plasma 6

A clean, modern, and consistent macOS Tahoe rice for **KDE Plasma 6 (Wayland)** on **CachyOS / Arch Linux**.

---

## 🖥️ Overview & Specifications

| Component | Choice |
| :--- | :--- |
| **OS** | CachyOS x86_64 (Arch Linux) |
| **Desktop Environment** | KDE Plasma 6 (Wayland) |
| **Application Style** | [Darkly](https://github.com/Bali1058/Darkly) (Translucent, Rounded, Blur) |
| **GTK Theme** | [MacTahoe-gtk-theme](https://github.com/vinceliuice/MacTahoe-gtk-theme) (Dark variant) |
| **Window Decoration** | [Klassy](https://github.com/paulmcauley/klassy) (macOS Left-aligned buttons) |
| **Global Theme / Colors** | MacTahoeDark |
| **Icon Theme** | MacTahoe + **MacTahoe-Frosted** *(Clear style: white glyphs on frosted glass)* |
| **Cursor Theme** | MacTahoe-dark |
| **System Font** | SF Pro Display (10pt) |
| **Monospace Font** | SF Mono (10pt) |
| **Launcher / Spotlight** | [Albert](https://albertlauncher.github.io/) (Meta+Space, MacTahoe Glass theme) |
| **Top Panel** | Apple Menu (`kMenu`), Global Menu (`Quickbar`), Active Window Title, System Tray, Digital Clock |
| **Dock** | Floating Plasma Panel (`icontasks`), Trash Can widget (`mac-tahoe-liquid-kde.trashcan`) |
| **Shell & Prompt** | Zsh + [Starship](https://starship.rs/) (Gruvbox Dark preset) |
| **Terminals** | Konsole & Alacritty |

---

## 📂 Repository Structure

```text
dotfiles/
├── .config/
│   ├── darklyrc                                  # Darkly widget style settings (blur, corner radius, opacity)
│   ├── kdeglobals                                # Global KDE fonts (SF Pro), widget style, colors
│   ├── kwinrc                                    # KWin rules, Klassy decor, multi-monitor EdgeBarrier
│   ├── klassy/                                   # Klassy window decoration presets
│   ├── plasmashellrc                             # Panel dimensions (Top bar: 32px, Floating dock: 54px)
│   ├── plasma-org.kde.plasma.desktop-appletsrc   # Applet/widget layout for Top Bar & Dock
│   ├── starship.toml                             # Starship prompt configuration
│   ├── alacritty/                                # Alacritty terminal config
│   ├── cava/                                     # CAVA audio visualizer config
│   └── konsolerc                                 # Konsole settings
├── .local/share/
│   ├── color-schemes/                            # MacTahoe Dark & Light color schemes
│   ├── konsole/                                  # Konsole profiles
│   └── plasma/plasmoids/                         # Custom plasmoids (kMenu, Titlebar, Trashcan)
├── patches/
│   └── MacTahoe-wifi-icons/                      # Patched Wi-Fi SVGs for status/24 and status/32
├── shell/
│   ├── .zshrc                                    # Zsh configuration
│   └── .p10k.zsh                                 # Powerlevel10k config (optional)
├── icons/                                        # Custom Clear Finder icon patch
├── packages.txt                                  # List of essential packages
├── frostify.py                                   # MacTahoe frosted-glass icon generator
├── install.py                                    # Python installer & restore script
├── sync.py                                       # Python script to sync active system configs to repo
└── README.md
```

---

## 📦 Prerequisites & Dependencies

Install required packages via `yay` (or your preferred AUR helper):

```bash
yay -S - < packages.txt
```

### Essential Themes & Fonts:
1. **Fonts (Automatic):** `install.py` will automatically detect and download **Apple SF Pro Display** fonts to `~/.local/share/fonts/` if missing.
2. **Icon Theme:** Install **MacTahoe** icon theme to `~/.local/share/icons/MacTahoe/`. The installer applies the Wi-Fi/Finder patches and generates **MacTahoe-Frosted** (Clear style: white monochrome glyphs on a translucent frosted tile) via `frostify.py`.

---

## 🚀 Installation & Setup

Clone the repository and run the Python installer:

```bash
git clone https://github.com/<your-username>/dotfiles.git ~/dotfiles
cd ~/dotfiles
python3 install.py
```

### Installer Options:
- **Default (Copy mode + Automatic Backup):**
  ```bash
  python3 install.py
  ```
  *Automatically creates a backup of existing configs in `~/.dotfiles_backup_<timestamp>/` before installing.*

- **Symlink mode (Recommended for dotfile maintenance):**
  ```bash
  python3 install.py --symlink
  ```

- **Dry-run mode (Preview changes without touching anything):**
  ```bash
  python3 install.py --dry-run
  ```

- **Skip the frosted icon theme generation:**
  ```bash
  python3 install.py --frosted none
  ```

- **Regenerate frosted icons only:**
  ```bash
  python3 frostify.py --mode clear
  ```

---

## 🔄 Syncing Changes Back to Repo

Whenever you customize themes, widgets, or desktop panels in KDE and want to update this repository:

```bash
cd ~/dotfiles
python3 sync.py
git add .
git commit -m "Update desktop configurations"
git push
```

---

## 🔒 Security Notice
This dotfiles repository is configured to exclude sensitive files:
- No browser profiles or cookies (`zen`, `brave`, `chrome`)
- No SSH keys or GPG keys
- No command histories (`.zsh_history`, `.bash_history`)
- No credentials or KDE Wallet data

---

## 📜 License
MIT License. Feel free to use and customize for your own rice!
