"""Talks to the local DYMO Connect web service (installed alongside DYMO Connect software)
to list printers and print labels. No cloud calls — everything goes to 127.0.0.1.
"""
import xml.etree.ElementTree as ET

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

_BASE_URLS = [
    "https://127.0.0.1:41951/DYMO/DLS/Printing",
    "http://127.0.0.1:41951/DYMO/DLS/Printing",
]


class DymoError(Exception):
    pass


def _post(path, data=None, timeout=10):
    last_error = None
    for base in _BASE_URLS:
        try:
            resp = requests.post(f"{base}/{path}", data=data or {}, timeout=timeout, verify=False)
            resp.raise_for_status()
            return resp.text
        except requests.RequestException as exc:
            last_error = exc
    raise DymoError(
        "Could not reach the DYMO Connect web service on 127.0.0.1:41951. "
        "Make sure DYMO Connect (or DYMO Label Software) is installed and running."
    ) from last_error


def is_service_running():
    try:
        _post("StatusConnected")
        return True
    except DymoError:
        return False


def get_printers():
    """Returns a list of dicts: {name, model, is_connected}."""
    xml_text = _post("GetPrinters")
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        raise DymoError(f"Unexpected response from DYMO service: {xml_text[:200]}") from exc

    printers = []
    for node in root:
        name = node.findtext("Name")
        model = node.findtext("ModelName")
        connected = (node.findtext("IsConnected") or "").lower() == "true"
        if name:
            printers.append({"name": name, "model": model or "", "is_connected": connected})
    return printers


def print_label(printer_name, label_xml, copies=1):
    if not printer_name:
        raise DymoError("No printer selected")
    if copies < 1:
        copies = 1

    print_params_xml = (
        "<LabelWriterPrintParams>"
        f"<Copies>{copies}</Copies>"
        "<JobTitle>Phone ID Label</JobTitle>"
        "</LabelWriterPrintParams>"
    )
    data = {
        "printerName": printer_name,
        "printParamsXml": print_params_xml,
        "labelXml": label_xml,
        "labelSetXml": "",
    }
    _post("PrintLabel", data=data)
