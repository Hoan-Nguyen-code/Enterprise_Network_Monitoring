
import csv
import html
from datetime import datetime
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
REPORT_DIR = BASE_DIR / "reports"
LOG_DIR = BASE_DIR / "logs"

for folder in (DATA_DIR, REPORT_DIR, LOG_DIR):
    folder.mkdir(parents=True, exist_ok=True)


DEVICE_FIELDS = [
    "timestamp",
    "device",
    "host",
    "reachable",
    "cpu_5s",
    "cpu_1m",
    "cpu_5m",
    "ram_percent",
    "error"
]

INTERFACE_FIELDS = [
    "timestamp",
    "device",
    "host",
    "name",
    "ip",
    "status",
    "protocol",
    "input_bytes",
    "output_bytes",
    "input_packets",
    "output_packets",
    "input_errors",
    "output_errors",
    "crc_errors",
    "input_rate_5m_bps",
    "output_rate_5m_bps",
    "rx_bps",
    "tx_bps"
]

ALERT_FIELDS = [
    "timestamp",
    "device",
    "level",
    "message"
]


def append_csv(path, fields, rows):
    if not rows:
        return

    file_exists = path.exists() and path.stat().st_size > 0

    with path.open(
        "a", newline="", encoding="utf-8"
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=fields,
            extrasaction="ignore"
        )

        if not file_exists:
            writer.writeheader()

        writer.writerows(rows)


def save_results(results, alerts):
    append_csv(
        DATA_DIR / "devices.csv",
        DEVICE_FIELDS,
        results
    )

    interface_rows = []

    for result in results:
        for interface in result["interfaces"]:
            interface_rows.append({
                "timestamp": result["timestamp"],
                "device": result["device"],
                "host": result["host"],
                **interface
            })

    append_csv(
        DATA_DIR / "interfaces.csv",
        INTERFACE_FIELDS,
        interface_rows
    )

    append_csv(
        LOG_DIR / "alerts.csv",
        ALERT_FIELDS,
        alerts
    )


def generate_html_report(results, alerts):
    generated_at = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    def safe(value):
        if value is None:
            return "N/A"
        return html.escape(str(value))

    device_rows = ""
    interface_rows = ""
    alert_rows = ""

    for device in results:
        status = (
            "ONLINE" if device["reachable"]
            else "OFFLINE"
        )

        device_rows += (
            "<tr>"
            f"<td>{safe(device['device'])}</td>"
            f"<td>{safe(device['host'])}</td>"
            f"<td>{safe(status)}</td>"
            f"<td>{safe(device['cpu_5s'])}</td>"
            f"<td>{safe(device['ram_percent'])}</td>"
            "</tr>"
        )

        for interface in device["interfaces"]:
            device_name = safe(device["device"])
            interface_name = safe(interface["name"])

            interface_rows += (
                "<tr>"
                f"<td>{device_name}</td>"
                f"<td>{interface_name}</td>"
                f"<td>{safe(interface['status'])}/"
                f"{safe(interface['protocol'])}</td>"
                f"<td>{safe(interface['rx_bps'])}</td>"
                f"<td>{safe(interface['tx_bps'])}</td>"
                f"<td>{safe(interface['input_errors'])}</td>"
                f"<td>{safe(interface['output_errors'])}</td>"
                "</tr>"
            )

    for alert in alerts:
        alert_rows += (
            "<tr>"
            f"<td>{safe(alert['timestamp'])}</td>"
            f"<td>{safe(alert['device'])}</td>"
            f"<td>{safe(alert['level'])}</td>"
            f"<td>{safe(alert['message'])}</td>"
            "</tr>"
        )

    if not alert_rows:
        alert_rows = (
            '<tr><td colspan="4">'
            "No active alerts in this cycle"
            "</td></tr>"
        )

    content = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Enterprise Network Monitoring</title>
<style>
body {{
    font-family: Arial, sans-serif;
    background: #f3f6fa;
    color: #1e293b;
    margin: 0;
    padding: 32px;
}}
main {{
    max-width: 1200px;
    margin: auto;
}}
h1 {{ color: #17365d; }}
section {{
    background: white;
    border-radius: 12px;
    padding: 20px;
    margin: 20px 0;
    box-shadow: 0 2px 10px #00000010;
    overflow-x: auto;
}}
table {{
    width: 100%;
    border-collapse: collapse;
}}
th, td {{
    border-bottom: 1px solid #e2e8f0;
    padding: 12px;
    text-align: left;
}}
th {{
    background: #eaf0f8;
}}
small {{ color: #64748b; }}
</style>
</head>
<body>
<main>
<h1>Enterprise Network Monitoring</h1>
<p>Generated: {safe(generated_at)}</p>
<small>Latest monitoring cycle snapshot</small>

<section>
<h2>Device Performance</h2>
<table>
<tr>
<th>Device</th><th>IP</th><th>Status</th>
<th>CPU (%)</th><th>RAM (%)</th>
</tr>
{device_rows}
</table>
</section>

<section>
<h2>Interface Monitoring</h2>
<table>
<tr>
<th>Device</th><th>Interface</th><th>Status</th>
<th>RX (bps)</th><th>TX (bps)</th>
<th>Input Errors</th><th>Output Errors</th>
</tr>
{interface_rows}
</table>
</section>

<section>
<h2>Alerts</h2>
<table>
<tr>
<th>Time</th><th>Device</th>
<th>Level</th><th>Message</th>
</tr>
{alert_rows}
</table>
</section>
</main>
</body>
</html>"""

    report_path = REPORT_DIR / "latest_report.html"

    report_path.write_text(
        content, encoding="utf-8"
    )

    return report_path
