"""Loads and saves app settings from config.json (created on first run)."""
import json
import os

DEFAULT_CONFIG = {
    "adb_path": "adb",
    "ideviceinfo_path": "ideviceinfo",
    "idevice_id_path": "idevice_id",
    "default_printer": "",
    "label_value": "imei",       # "imei" or "serial"
    "include_barcode": True,
    "header_text": ""
}

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")


def load_config():
    cfg = dict(DEFAULT_CONFIG)
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as fh:
                cfg.update(json.load(fh))
        except (json.JSONDecodeError, OSError):
            pass
    return cfg


def save_config(cfg):
    with open(CONFIG_PATH, "w", encoding="utf-8") as fh:
        json.dump(cfg, fh, indent=2)
