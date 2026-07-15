"""Phone ID -> Dymo Printer

Small local Windows GUI app: scan a connected Android/iOS phone for its serial
number or IMEI (or type one in by hand), then print it on a DYMO label printer
through the local DYMO Connect web service. Nothing here leaves the machine.
"""
import threading
import tkinter as tk
from tkinter import ttk, messagebox

import config
import device_reader
import dymo_printer
import label_builder


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Phone ID -> Dymo Printer")
        self.geometry("560x520")
        self.resizable(False, False)

        self.cfg = config.load_config()
        self.devices = []

        self._build_ui()
        self._refresh_printers(silent=True)

    # ------------------------------------------------------------- layout --

    def _build_ui(self):
        pad = {"padx": 10, "pady": 6}

        device_frame = ttk.LabelFrame(self, text="1. Connect phone via USB")
        device_frame.pack(fill="x", **pad)

        ttk.Button(device_frame, text="Scan for devices", command=self._scan_devices).pack(
            side="left", padx=8, pady=8
        )
        self.device_combo = ttk.Combobox(device_frame, state="readonly", width=48)
        self.device_combo.pack(side="left", padx=8, pady=8, fill="x", expand=True)
        self.device_combo.bind("<<ComboboxSelected>>", self._on_device_selected)

        value_frame = ttk.LabelFrame(self, text="2. Value to print (edit or type manually)")
        value_frame.pack(fill="x", **pad)

        ttk.Label(value_frame, text="Serial number:").grid(row=0, column=0, sticky="w", padx=8, pady=4)
        self.serial_var = tk.StringVar()
        ttk.Entry(value_frame, textvariable=self.serial_var, width=40).grid(
            row=0, column=1, sticky="we", padx=8, pady=4
        )

        ttk.Label(value_frame, text="IMEI:").grid(row=1, column=0, sticky="w", padx=8, pady=4)
        self.imei_var = tk.StringVar()
        ttk.Entry(value_frame, textvariable=self.imei_var, width=40).grid(
            row=1, column=1, sticky="we", padx=8, pady=4
        )
        value_frame.columnconfigure(1, weight=1)

        ttk.Label(value_frame, text="Print which value:").grid(row=2, column=0, sticky="w", padx=8, pady=4)
        self.print_choice = tk.StringVar(value=self.cfg.get("label_value", "imei"))
        choice_row = ttk.Frame(value_frame)
        choice_row.grid(row=2, column=1, sticky="w", padx=8, pady=4)
        ttk.Radiobutton(choice_row, text="IMEI", variable=self.print_choice, value="imei").pack(side="left")
        ttk.Radiobutton(choice_row, text="Serial number", variable=self.print_choice, value="serial").pack(
            side="left", padx=10
        )

        ttk.Label(value_frame, text="Label header text:").grid(row=3, column=0, sticky="w", padx=8, pady=4)
        self.header_var = tk.StringVar(value=self.cfg.get("header_text", ""))
        ttk.Entry(value_frame, textvariable=self.header_var, width=40).grid(
            row=3, column=1, sticky="we", padx=8, pady=4
        )

        self.barcode_var = tk.BooleanVar(value=self.cfg.get("include_barcode", True))
        ttk.Checkbutton(value_frame, text="Include barcode", variable=self.barcode_var).grid(
            row=4, column=1, sticky="w", padx=8, pady=4
        )

        printer_frame = ttk.LabelFrame(self, text="3. Printer")
        printer_frame.pack(fill="x", **pad)

        ttk.Button(printer_frame, text="Refresh printers", command=self._refresh_printers).pack(
            side="left", padx=8, pady=8
        )
        self.printer_combo = ttk.Combobox(printer_frame, state="readonly", width=38)
        self.printer_combo.pack(side="left", padx=8, pady=8, fill="x", expand=True)

        ttk.Label(printer_frame, text="Copies:").pack(side="left")
        self.copies_var = tk.IntVar(value=1)
        ttk.Spinbox(printer_frame, from_=1, to=50, textvariable=self.copies_var, width=4).pack(
            side="left", padx=(4, 10)
        )

        action_frame = ttk.Frame(self)
        action_frame.pack(fill="x", **pad)
        ttk.Button(action_frame, text="Print label", command=self._print_label).pack(
            side="left", padx=8, pady=4
        )
        ttk.Button(action_frame, text="Save settings", command=self._save_settings).pack(
            side="left", padx=8, pady=4
        )

        log_frame = ttk.LabelFrame(self, text="Status")
        log_frame.pack(fill="both", expand=True, **pad)
        self.log_text = tk.Text(log_frame, height=10, state="disabled", wrap="word")
        self.log_text.pack(fill="both", expand=True, padx=8, pady=8)

        self._log("Ready. Connect a phone and click 'Scan for devices', or type a value manually.")

    # -------------------------------------------------------------- logic --

    def _log(self, message):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", message + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _scan_devices(self):
        self._log("Scanning for connected phones...")
        threading.Thread(target=self._scan_devices_worker, daemon=True).start()

    def _scan_devices_worker(self):
        try:
            devices = device_reader.detect_devices(self.cfg)
        except Exception as exc:  # noqa: BLE001 - surface any failure to the log, don't crash the app
            self.after(0, self._log, f"Scan failed: {exc}")
            return
        self.after(0, self._on_scan_complete, devices)

    def _on_scan_complete(self, devices):
        self.devices = devices
        if not devices:
            self._log(
                "No devices found. Check USB debugging (Android) / Trust This Computer (iOS) "
                "is enabled, or enter the value manually below."
            )
            self.device_combo["values"] = []
            return

        labels = []
        for d in devices:
            model = d.get("model") or d["platform"].upper()
            labels.append(f"{model} ({d['platform']}) - {d['id']}")
        self.device_combo["values"] = labels
        self.device_combo.current(0)
        self._log(f"Found {len(devices)} device(s).")
        self._on_device_selected()

    def _on_device_selected(self, _event=None):
        idx = self.device_combo.current()
        if idx < 0 or idx >= len(self.devices):
            return
        device = self.devices[idx]
        self.serial_var.set(device.get("serial") or "")
        self.imei_var.set(device.get("imei") or "")
        if not device.get("imei"):
            self._log(
                "IMEI could not be read automatically (locked down by the OS on most modern "
                "phones). Dial *#06# on the phone and type it in manually if you need it."
            )

    def _refresh_printers(self, silent=False):
        threading.Thread(target=self._refresh_printers_worker, args=(silent,), daemon=True).start()

    def _refresh_printers_worker(self, silent):
        try:
            printers = dymo_printer.get_printers()
        except dymo_printer.DymoError as exc:
            if not silent:
                self.after(0, self._log, str(exc))
            return
        self.after(0, self._on_printers_loaded, printers)

    def _on_printers_loaded(self, printers):
        names = [p["name"] for p in printers]
        self.printer_combo["values"] = names
        if names:
            default = self.cfg.get("default_printer")
            if default in names:
                self.printer_combo.set(default)
            else:
                self.printer_combo.current(0)
            self._log(f"Found {len(names)} DYMO printer(s).")
        else:
            self._log("No DYMO printers found. Is a printer plugged in and DYMO Connect running?")

    def _print_label(self):
        value = self.imei_var.get().strip() if self.print_choice.get() == "imei" else self.serial_var.get().strip()
        if not value:
            messagebox.showwarning("Nothing to print", "Enter or scan an IMEI / serial number first.")
            return

        printer_name = self.printer_combo.get()
        if not printer_name:
            messagebox.showwarning("No printer", "Select a DYMO printer first (click 'Refresh printers').")
            return

        header = self.header_var.get().strip() or self.print_choice.get().upper()
        include_barcode = self.barcode_var.get()
        copies = self.copies_var.get()

        try:
            label_xml = label_builder.build_label_xml(value, header=header, include_barcode=include_barcode)
        except ValueError as exc:
            messagebox.showerror("Label error", str(exc))
            return

        self._log(f"Printing '{value}' on {printer_name} ({copies} copy/copies)...")
        threading.Thread(
            target=self._print_worker, args=(printer_name, label_xml, copies), daemon=True
        ).start()

    def _print_worker(self, printer_name, label_xml, copies):
        try:
            dymo_printer.print_label(printer_name, label_xml, copies=copies)
        except dymo_printer.DymoError as exc:
            self.after(0, self._log, f"Print failed: {exc}")
            self.after(0, lambda: messagebox.showerror("Print failed", str(exc)))
            return
        self.after(0, self._log, "Sent to printer.")

    def _save_settings(self):
        self.cfg["label_value"] = self.print_choice.get()
        self.cfg["header_text"] = self.header_var.get().strip()
        self.cfg["include_barcode"] = self.barcode_var.get()
        self.cfg["default_printer"] = self.printer_combo.get()
        config.save_config(self.cfg)
        self._log("Settings saved to config.json.")


if __name__ == "__main__":
    App().mainloop()
