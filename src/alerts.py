
from datetime import datetime


def check_alerts(result, settings):
    alerts = []

    device = result["device"]

    def add_alert(level, message):
        alerts.append({
            "timestamp": datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
            "device": device,
            "level": level,
            "message": message
        })

    if not result["reachable"]:
        add_alert(
            "CRITICAL",
            f"Device unreachable: {result['error']}"
        )
        return alerts

    cpu = result.get("cpu_5s")
    ram = result.get("ram_percent")

    if cpu is None:
        add_alert("WARNING", "CPU data unavailable")
    elif cpu >= settings["cpu_threshold"]:
        add_alert(
            "WARNING",
            f"High CPU usage: {cpu}%"
        )

    if ram is None:
        add_alert("WARNING", "RAM data unavailable")
    elif ram >= settings["ram_threshold"]:
        add_alert(
            "WARNING",
            f"High RAM usage: {ram}%"
        )

    for interface in result["interfaces"]:
        name = interface["name"]

        if (
            interface["status"] != "up"
            or interface["protocol"] != "up"
        ):
            add_alert(
                "CRITICAL",
                f"{name} is "
                f"{interface['status']}/"
                f"{interface['protocol']}"
            )

        for direction in ("rx_bps", "tx_bps"):
            speed = interface.get(direction)

            if speed is not None:
                speed_mbps = speed / 1_000_000

                if speed_mbps >= settings[
                    "traffic_threshold_mbps"
                ]:
                    add_alert(
                        "WARNING",
                        f"{name} {direction} high: "
                        f"{speed_mbps:.2f} Mbps"
                    )

        errors = [
            interface.get("input_errors"),
            interface.get("output_errors")
        ]

        if any(
            value is not None
            and value >= settings["error_threshold"]
            for value in errors
        ):
            add_alert(
                "WARNING",
                f"{name} interface errors: "
                f"input={interface['input_errors']}, "
                f"output={interface['output_errors']}"
            )

        if interface.get("crc_errors") is None:
            add_alert(
                "WARNING",
                f"{name} CRC data unavailable"
            )

    return alerts
