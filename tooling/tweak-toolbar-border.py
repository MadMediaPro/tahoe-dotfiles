#!/usr/bin/env python3
"""
Script untuk mengatur border & background toolbar button tema Kvantum (mac-tahoe-liquid-kdeDark).
Cukup ubah parameter di bawah, simpan, lalu jalankan:
    python3 ~/tweak-toolbar-border.py
"""

import os
import re
import shutil
import subprocess
import time
import xml.etree.ElementTree as ET

# ==============================================================================
# 🎨 PENGATURAN WARNA & BORDER (UBAH SESUAI KEINGINAN KAMU)
# ==============================================================================

# 1. BORDER KONDISI NORMAL (SAAT DIAM)
# Gunakan warna hex (misal: "#484848" abu-abu netral, "#333333" lebih gelap, "#000000" hitam, "#ffffff" putih)
NORMAL_BORDER_COLOR = "#696969"
NORMAL_BORDER_OPACITY = 1.0  # 1.0 = solid (flat/matte), 0.5 = 50%, 0.0 = tanpa border

# 2. BORDER KONDISI HOVER (SAAT DISENTUH MOUSE)
HOVER_BORDER_COLOR = "#696969"
HOVER_BORDER_OPACITY = 1.0  # 1.0 = solid, bisa diset lebih terang

# 3. LATAR BELAKANG / FILL KAPSUL TOMBOL
# Normal fill: default bawaan tema adalah putih transparan 8% (0.08)
NORMAL_FILL_COLOR = "#ffffff"
NORMAL_FILL_OPACITY = (
    0.08  # Ubah ke 0.0 jika ingin kapsul transparan total tanpa background
)

HOVER_FILL_COLOR = "#ffffff"
HOVER_FILL_OPACITY = 0.15  # Saat disentuh mouse

# 4. KELOMPOKKAN TOMBOL JADI SATU KAPSUL (True = gaya macOS pill gabung, False = terpisah)
GROUP_TOOLBAR_BUTTONS = True

# ==============================================================================
# LOKASI FILE TEMA
# ==============================================================================
THEME_NAME = "mac-tahoe-liquid-kdeDark"
THEME_DIR = os.path.expanduser(f"~/.config/Kvantum/{THEME_NAME}")
SVG_PATH = os.path.join(THEME_DIR, f"{THEME_NAME}.svg")
KVCONFIG_PATH = os.path.join(THEME_DIR, f"{THEME_NAME}.kvconfig")

# Namespace standar yang biasa dipakai SVG hasil export Inkscape.
# Didaftarkan dulu SEBELUM parsing supaya ElementTree tidak mengganti
# prefix asli (misal "svg:", "sodipodi:") jadi "ns0:", "ns1:", dst saat ditulis ulang.
SVG_NAMESPACES = {
    "": "http://www.w3.org/2000/svg",
    "xlink": "http://www.w3.org/1999/xlink",
    "sodipodi": "http://sodipodi.sourceforge.net/DTD/sodipodi-0.0.dtd",
    "inkscape": "http://www.inkscape.org/namespaces/inkscape",
    "dc": "http://purl.org/dc/elements/1.1/",
    "cc": "http://creativecommons.org/ns#",
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
}

HEX_COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")


def validate_inputs():
    """Cegah SVG/kvconfig korup akibat typo warna atau opacity di luar range."""
    colors = {
        "NORMAL_BORDER_COLOR": NORMAL_BORDER_COLOR,
        "HOVER_BORDER_COLOR": HOVER_BORDER_COLOR,
        "NORMAL_FILL_COLOR": NORMAL_FILL_COLOR,
        "HOVER_FILL_COLOR": HOVER_FILL_COLOR,
    }
    for name, value in colors.items():
        if not HEX_COLOR_RE.match(value):
            raise ValueError(
                f"{name} = '{value}' bukan format hex warna yang valid (contoh: #484848)"
            )

    opacities = {
        "NORMAL_BORDER_OPACITY": NORMAL_BORDER_OPACITY,
        "HOVER_BORDER_OPACITY": HOVER_BORDER_OPACITY,
        "NORMAL_FILL_OPACITY": NORMAL_FILL_OPACITY,
        "HOVER_FILL_OPACITY": HOVER_FILL_OPACITY,
    }
    for name, value in opacities.items():
        if not (0.0 <= value <= 1.0):
            raise ValueError(f"{name} = {value} harus di antara 0.0 dan 1.0")


def merge_style(existing_style: str, updates: dict) -> str:
    """
    Gabungkan properti baru ke style yang sudah ada, alih-alih menimpa total.
    Ini mencegah properti lain (misal stroke:none) ikut hilang.
    """
    props = {}
    if existing_style:
        for part in existing_style.split(";"):
            part = part.strip()
            if not part or ":" not in part:
                continue
            key, value = part.split(":", 1)
            props[key.strip()] = value.strip()
    props.update(updates)
    return ";".join(f"{k}:{v}" for k, v in props.items())


def set_kvconfig_value(content: str, key: str, value: str, section: str = "Toolbar"):
    """
    Set key=value di kvconfig. Kalau key sudah ada, timpa nilainya.
    Kalau belum ada, tambahkan di bawah [section] (atau buat section-nya
    kalau belum ada sama sekali), supaya perubahan tidak diam-diam gagal.
    """
    pattern = rf"^{re.escape(key)}=.*$"
    if re.search(pattern, content, flags=re.MULTILINE | re.IGNORECASE):
        return (
            re.sub(
                pattern, f"{key}={value}", content, flags=re.MULTILINE | re.IGNORECASE
            ),
            "updated",
        )

    section_header = f"[{section}]"
    if section_header in content:
        content = content.replace(section_header, f"{section_header}\n{key}={value}", 1)
        return content, "appended-to-section"

    content = content.rstrip("\n") + f"\n\n{section_header}\n{key}={value}\n"
    return content, "section-created"


def main():
    validate_inputs()

    if not os.path.exists(SVG_PATH) or not os.path.exists(KVCONFIG_PATH):
        print(f"[!] Error: File tema tidak ditemukan di {THEME_DIR}")
        return

    # 1. Backup otomatis sebelum modifikasi (SVG *dan* kvconfig)
    timestamp = int(time.time())
    shutil.copy2(SVG_PATH, f"{SVG_PATH}.bak.{timestamp}")
    shutil.copy2(KVCONFIG_PATH, f"{KVCONFIG_PATH}.bak.{timestamp}")
    print(f"[✓] Backup dibuat: {os.path.basename(SVG_PATH)}.bak.{timestamp}")
    print(f"[✓] Backup dibuat: {os.path.basename(KVCONFIG_PATH)}.bak.{timestamp}")

    # 2. Daftarkan namespace SEBELUM parse supaya prefix asli tidak berubah jadi ns0/ns1
    for prefix, uri in SVG_NAMESPACES.items():
        ET.register_namespace(prefix, uri)

    tree = ET.parse(SVG_PATH)
    root = tree.getroot()

    normal_border_ids = [
        "tbutton-normal-top-border",
        "tbutton-normal-topright-border",
        "tbutton-normal-right-border",
        "tbutton-normal-bottom-border",
        "tbutton-normal-bottomright-border",
    ]

    hover_border_ids = [
        "tbutton-focused-top-border",
        "tbutton-focused-topright-border",
        "tbutton-focused-right-border",
        "tbutton-focused-bottom-border",
        "tbutton-focused-bottomright-border",
    ]

    normal_fill_ids = [
        "tbutton-normal",
        "path483",
        "path492",
        "path467",
        "path472",
        "path478",
    ]

    hover_fill_ids = [
        "tbutton-focused",
        "path792",
        "path801",
        "path776",
        "path781",
        "path787",
    ]

    count_mods = 0
    for el in root.iter():
        eid = el.attrib.get("id", "")
        existing_style = el.attrib.get("style", "")

        if eid in normal_border_ids:
            updates = {
                "opacity": NORMAL_BORDER_OPACITY,
                "fill": NORMAL_BORDER_COLOR,
                "fill-rule": "evenodd",
            }
        elif eid in hover_border_ids:
            updates = {
                "opacity": HOVER_BORDER_OPACITY,
                "fill": HOVER_BORDER_COLOR,
                "fill-rule": "evenodd",
            }
        elif eid in normal_fill_ids:
            updates = {
                "opacity": NORMAL_FILL_OPACITY,
                "fill": NORMAL_FILL_COLOR,
                "fill-opacity": 1,
                "fill-rule": "evenodd",
            }
        elif eid in hover_fill_ids:
            updates = {
                "opacity": HOVER_FILL_OPACITY,
                "fill": HOVER_FILL_COLOR,
                "fill-opacity": 1,
                "fill-rule": "evenodd",
            }
        else:
            continue

        el.attrib["style"] = merge_style(existing_style, updates)
        count_mods += 1

    if count_mods == 0:
        print(
            "[!] Peringatan: tidak ada elemen yang cocok ditemukan di SVG — "
            "kemungkinan ID sudah berubah di versi tema ini. Tidak ada yang diubah."
        )
    else:
        tree.write(SVG_PATH, encoding="utf-8", xml_declaration=True)
        print(f"[✓] SVG berhasil diperbarui ({count_mods} elemen disesuaikan)")

    # 3. Modifikasi KVCONFIG (group_toolbar_buttons)
    with open(KVCONFIG_PATH, "r", encoding="utf-8") as f:
        kv_content = f.read()

    target_value = "true" if GROUP_TOOLBAR_BUTTONS else "false"
    kv_content, status = set_kvconfig_value(
        kv_content, "group_toolbar_buttons", target_value
    )

    with open(KVCONFIG_PATH, "w", encoding="utf-8") as f:
        f.write(kv_content)

    if status == "updated":
        print(f"[✓] kvconfig diset: group_toolbar_buttons={target_value}")
    else:
        print(
            f"[✓] kvconfig: key belum ada, sudah ditambahkan (group_toolbar_buttons={target_value})"
        )

    # 4. Reload tema Kvantum langsung
    print("[*] Me-reload tema di Kvantum Manager...")
    try:
        subprocess.run(
            ["kvantummanager", "--set", THEME_NAME],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        print("[✓] SUKSES! Tema berhasil di-apply.")
    except FileNotFoundError:
        print(
            "[!] 'kvantummanager' tidak ditemukan di PATH. Reload manual via aplikasi Kvantum Manager."
        )
    except subprocess.CalledProcessError as e:
        print(f"[!] Gagal auto-reload via kvantummanager (exit code {e.returncode}).")
        print("    Silakan reload manual via aplikasi Kvantum Manager.")

    print(
        "\nTip: Restart aplikasi seperti Dolphin / Kate untuk melihat efeknya secara utuh."
    )


if __name__ == "__main__":
    main()
