# Phone ID -> Dymo Printer

A small local Windows app: plug in a phone, read its serial number / IMEI,
then print that value (with a barcode) on a DYMO label printer. Everything
runs on your own machine — the only network calls are to `127.0.0.1`
(the DYMO Connect web service). No data is sent anywhere else.

## How it works

- **Android** devices are read over USB using `adb` (Android Platform Tools).
- **iOS** devices are read over USB using `libimobiledevice` (`ideviceinfo` /
  `idevice_id`).
- IMEI is locked down by both platforms for non-privileged apps on modern OS
  versions, so it can't always be read automatically. When that happens the
  app leaves the IMEI field blank and you can type it in by hand (dial
  `*#06#` on the phone to see it), or use the serial number instead — both
  are always readable and both can be printed.
- Printing goes through the **DYMO Connect** local web service
  (`https://127.0.0.1:41951`), the same local API DYMO's own web print
  add-on / SDK samples use.

## Prerequisites (install once, on the Windows PC)

1. **Python 3.10+** — https://www.python.org/downloads/windows/ (or skip
   this and use the pre-built `.exe`, see below).
2. **DYMO Connect** software — https://www.dymo.com/support — install it,
   plug in your DYMO printer, and make sure DYMO Connect is running (it
   installs a background service that this app talks to).
3. For Android phones: **Platform Tools (adb)** —
   https://developer.android.com/tools/releases/platform-tools . Unzip it
   somewhere and either add that folder to your `PATH`, or set the full path
   to `adb.exe` in `config.json` (see below). On the phone, enable
   **Developer Options -> USB debugging** and accept the "Allow USB
   debugging" prompt when you plug it in.
4. For iPhones: **libimobiledevice for Windows** (e.g. the builds from
   https://github.com/libimobiledevice-win32 ) for `ideviceinfo.exe` /
   `idevice_id.exe`, plus **Apple Mobile Device Support** (installed with
   iTunes, or the standalone "Apple Devices" app from the Microsoft Store)
   so Windows has the USB driver. On the phone, tap **Trust This Computer**
   when prompted after plugging in.

## Setup

```
cd phone-id-dymo-printer
pip install -r requirements.txt
copy config.example.json config.json
```

Edit `config.json` if `adb`/`ideviceinfo`/`idevice_id` aren't on your
`PATH`, or to set a default printer name.

## Run

```
python app.py
```

1. Plug in the phone, click **Scan for devices**, pick it from the dropdown
   — serial number (and IMEI, if readable) fill in automatically. You can
   always edit these fields or type a value in directly instead of scanning.
2. Choose whether to print the **IMEI** or the **serial number**, and
   whether to include a barcode.
3. Click **Refresh printers**, pick your DYMO printer.
4. Click **Print label**.

Click **Save settings** to remember your header text / barcode toggle /
default printer for next time.

## Building a standalone .exe

If you'd rather not require Python on the target machine, build a single
`.exe`:

```
build_exe.bat
```

This produces `dist\PhoneID-DymoPrinter.exe`. Copy `config.example.json`
next to it as `config.json` if you need non-default paths or a default
printer.

## Troubleshooting

- **"No DYMO printers found"** — make sure DYMO Connect is installed,
  running, and the printer shows up inside the DYMO Connect app itself
  first.
- **"Could not reach the DYMO Connect web service"** — DYMO Connect's
  background service isn't running, or a firewall is blocking
  `127.0.0.1:41951`. Restart DYMO Connect and try again.
- **No Android device found** — check `adb devices` works from a normal
  Command Prompt; if not, reinstall the USB driver / re-enable USB
  debugging.
- **No iPhone found** — check `ideviceinfo -l` / `idevice_id -l` from a
  Command Prompt; if it hangs or fails, reinstall Apple Mobile Device
  Support and re-trust the computer on the phone.
- **IMEI is blank** — expected on Android 10+/modern iOS without extra
  privileges. Use the serial number, or type the IMEI in by hand from
  `*#06#` or the phone's Settings -> About screen.

## Label layout

Labels are generated as DYMO Label XML on the fly (`label_builder.py`),
sized for a standard DYMO address-style label (30252, 54x25mm): a small
header line, the IMEI/serial as text, and an optional Code128 barcode
underneath. Adjust the layout constants in `label_builder.py` if you use a
different label size.
