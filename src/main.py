
import json
import time
from getpass import getpass
from pathlib import Path

from monitor import NetworkMonitor
from alerts import check_alerts
from reports import save_results, generate_html_report


BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = BASE_DIR / "config" / "devices.json"


def load_config():
    with CONFIG_PATH.open(
        "r", encoding="utf-8"
    ) as file:
        return json.load(file)


def display_device(result):
    name = result["device"]
    host = result["host"]

    print(f"\n{'=' * 55}")
    print(f"DEVICE: {name} ({host})")
    print(f"{'=' * 55}")

    if not result["reachable"]:
        print(f"STATUS: OFFLINE - {result['error']}")
        return

    print("STATUS: ONLINE")
    print(f"CPU 5s : {result['cpu_5s']}%")
    print(f"CPU 1m : {result['cpu_1m']}%")
    print(f"CPU 5m : {result['cpu_5m']}%")
    print(f"RAM    : {result['ram_percent']}%")

    for interface in result["interfaces"]:
        print(f"\nInterface: {interface['name']}")
        print(
            f"Status: {interface['status']}/"
            f"{interface['protocol']}"
        )
        print(f"IP: {interface['ip']}")
        print(f"RX: {interface['rx_bps']} bps")
        print(f"TX: {interface['tx_bps']} bps")
        print(
            f"Errors: input={interface['input_errors']}, "
            f"output={interface['output_errors']}, "
            f"CRC={interface['crc_errors']}"
        )


def main():
    config = load_config()

    devices = config["devices"]
    settings = config["monitoring"]

    interval = settings["interval_seconds"]

    password = getpass("SSH password: ")

    monitor = NetworkMonitor(password)

    print("\nENTERPRISE NETWORK MONITORING")
    print(f"Devices: {len(devices)}")
    print(f"Interval: {interval} seconds")
    print("Press Ctrl+C to stop.\n")

    try:
        while True:
            cycle_start = time.monotonic()

            results = []
            all_alerts = []

            for device in devices:
                print(
                    f"\nConnecting to {device['name']}..."
                )

                result = monitor.collect(device)

                results.append(result)
                display_device(result)

                alerts = check_alerts(
                    result, settings
                )

                all_alerts.extend(alerts)

            print(f"\n{'=' * 55}")
            print("ALERT SUMMARY")
            print(f"{'=' * 55}")

            if all_alerts:
                for alert in all_alerts:
                    print(
                        f"[{alert['level']}] "
                        f"{alert['device']}: "
                        f"{alert['message']}"
                    )
            else:
                print("No alerts in this cycle.")

            save_results(results, all_alerts)

            report_path = generate_html_report(
                results, all_alerts
            )

            print("\nData saved:")
            print("  data/devices.csv")
            print("  data/interfaces.csv")
            print("  logs/alerts.csv")
            print(f"  {report_path}")

            elapsed = time.monotonic() - cycle_start

            wait_seconds = max(
                0, interval - elapsed
            )

            print(
                f"\nNext cycle in "
                f"{wait_seconds:.1f} seconds..."
            )

            time.sleep(wait_seconds)

    except KeyboardInterrupt:
        print("\nMonitoring stopped by user.")


if __name__ == "__main__":
    main()
