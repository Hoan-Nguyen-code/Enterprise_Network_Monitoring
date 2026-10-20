
import csv
from pathlib import Path
from flask import Flask, jsonify, render_template

BASE_DIR = Path(__file__).resolve().parent.parent

app = Flask(
    __name__,
    template_folder=str(BASE_DIR / "templates")
)


def read_csv(filename, limit=1000):
    path = BASE_DIR / filename

    if not path.exists():
        return []

    try:
        with path.open(
            "r", encoding="utf-8", newline=""
        ) as file:
            rows = list(csv.DictReader(file))
            return rows[-limit:]
    except (OSError, csv.Error):
        return []


def number(value):
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


@app.route("/")
def index():
    return render_template("dashboard.html")


@app.route("/api/dashboard")
def dashboard_data():
    devices = read_csv("data/devices.csv")
    interfaces = read_csv("data/interfaces.csv")
    alerts = read_csv("logs/alerts.csv")

    latest_devices = {}

    for row in devices:
        latest_devices[row["device"]] = row

    latest_interfaces = {}

    for row in interfaces:
        key = (row["device"], row["name"])
        latest_interfaces[key] = row

    device_list = []

    for name, row in latest_devices.items():
        device_list.append({
            "name": name,
            "host": row["host"],
            "online": row["reachable"] == "True",
            "cpu": number(row["cpu_5s"]),
            "ram": number(row["ram_percent"]),
            "timestamp": row["timestamp"]
        })

    interface_list = []

    for (device, name), row in latest_interfaces.items():
        interface_list.append({
            "device": device,
            "name": name,
            "status": row["status"],
            "protocol": row["protocol"],
            "rx_bps": number(row["rx_bps"]),
            "tx_bps": number(row["tx_bps"]),
            "input_errors": number(row["input_errors"]),
            "output_errors": number(row["output_errors"])
        })

    history = {}

    for row in devices:
        name = row["device"]

        if name not in history:
            history[name] = []

        history[name].append({
            "timestamp": row["timestamp"],
            "cpu": number(row["cpu_5s"]),
            "ram": number(row["ram_percent"])
        })

    for name in history:
        history[name] = history[name][-30:]

    online = sum(
        1 for device in device_list
        if device["online"]
    )

    active_interfaces = sum(
        1 for interface in interface_list
        if interface["status"] == "up"
        and interface["protocol"] == "up"
    )

    return jsonify({
        "summary": {
            "total_devices": len(device_list),
            "online_devices": online,
            "total_interfaces": len(interface_list),
            "active_interfaces": active_interfaces
        },
        "devices": device_list,
        "interfaces": interface_list,
        "history": history,
        "alerts": alerts[-20:][::-1]
    })


if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=False
    )
