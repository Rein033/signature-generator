"""Reads serial number / IMEI from a connected Android (adb) or iOS (libimobiledevice) phone.

Both platforms lock IMEI behind privileged permissions on modern OS versions, so every
lookup here is best-effort: whatever can't be read automatically is left blank and the
GUI lets the user type it in by hand (e.g. by dialing *#06# on the phone).
"""
import re
import subprocess


class DeviceReadError(Exception):
    pass


def _run(cmd, timeout=15):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError as exc:
        raise DeviceReadError(f"Command not found: {cmd[0]} (check the path in config.json)") from exc
    except subprocess.TimeoutExpired as exc:
        raise DeviceReadError(f"Timed out running: {' '.join(cmd)}") from exc


# ---------------------------------------------------------------- Android --

def list_android_devices(adb_path="adb"):
    result = _run([adb_path, "devices", "-l"])
    if result.returncode != 0:
        raise DeviceReadError(result.stderr.strip() or "adb devices failed")

    devices = []
    for line in result.stdout.splitlines()[1:]:
        line = line.strip()
        parts = line.split()
        if len(parts) >= 2 and parts[1] == "device":
            devices.append(parts[0])
    return devices


def read_android_info(serial, adb_path="adb"):
    info = {"platform": "android", "id": serial, "serial": serial, "imei": None, "model": None}

    model = _run([adb_path, "-s", serial, "shell", "getprop", "ro.product.model"])
    if model.returncode == 0 and model.stdout.strip():
        info["model"] = model.stdout.strip()

    prop = _run([adb_path, "-s", serial, "shell", "getprop", "ro.serialno"])
    if prop.returncode == 0 and prop.stdout.strip():
        info["serial"] = prop.stdout.strip()

    imei = _try_imei_service_call(serial, adb_path) or _try_imei_dumpsys(serial, adb_path)
    if imei:
        info["imei"] = imei
    return info


def _try_imei_service_call(serial, adb_path):
    """Works on some pre-Android 10 / OEM builds where iphonesubinfo isn't locked down."""
    result = _run([adb_path, "-s", serial, "shell", "service", "call", "iphonesubinfo", "1"])
    if result.returncode != 0:
        return None

    hex_pairs = re.findall(r"'([0-9a-fA-F.]{8})'", result.stdout)
    if not hex_pairs:
        return None

    chars = []
    for pair in hex_pairs:
        for i in range(0, len(pair), 4):
            code = pair[i:i + 4].replace(".", "")
            if code:
                try:
                    chars.append(chr(int(code, 16)))
                except ValueError:
                    pass
    imei = re.sub(r"\D", "", "".join(chars))
    return imei if 14 <= len(imei) <= 17 else None


def _try_imei_dumpsys(serial, adb_path):
    result = _run([adb_path, "-s", serial, "shell", "dumpsys", "iphonesubinfo"])
    if result.returncode != 0:
        return None
    match = re.search(r"Device ID\s*=\s*(\d{14,17})", result.stdout)
    return match.group(1) if match else None


# -------------------------------------------------------------------- iOS --

def list_ios_devices(idevice_id_path="idevice_id"):
    result = _run([idevice_id_path, "-l"])
    if result.returncode != 0:
        raise DeviceReadError(result.stderr.strip() or "idevice_id failed")
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def read_ios_info(udid, ideviceinfo_path="ideviceinfo"):
    info = {"platform": "ios", "id": udid, "serial": None, "imei": None, "model": None}
    keys = {
        "SerialNumber": "serial",
        "InternationalMobileEquipmentIdentity": "imei",
        "ProductType": "model",
    }
    for key, field in keys.items():
        result = _run([ideviceinfo_path, "-u", udid, "-k", key])
        if result.returncode == 0 and result.stdout.strip():
            info[field] = result.stdout.strip()
    return info


# --------------------------------------------------------------- combined --

def detect_devices(cfg):
    """Returns a list of info dicts for every phone currently reachable over USB."""
    devices = []

    try:
        for serial in list_android_devices(cfg["adb_path"]):
            try:
                devices.append(read_android_info(serial, cfg["adb_path"]))
            except DeviceReadError:
                devices.append({"platform": "android", "id": serial, "serial": serial,
                                 "imei": None, "model": None})
    except DeviceReadError:
        pass  # adb not installed / not on PATH — iOS branch below still runs

    try:
        for udid in list_ios_devices(cfg["idevice_id_path"]):
            try:
                devices.append(read_ios_info(udid, cfg["ideviceinfo_path"]))
            except DeviceReadError:
                devices.append({"platform": "ios", "id": udid, "serial": None,
                                 "imei": None, "model": None})
    except DeviceReadError:
        pass  # libimobiledevice not installed / no iOS device attached

    return devices
