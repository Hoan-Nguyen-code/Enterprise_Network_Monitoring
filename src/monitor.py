
import re
import time
from netmiko import ConnectHandler


def extract_number(pattern, text, default=None):
    match = re.search(pattern, text, re.IGNORECASE)
    return int(match.group(1)) if match else default


def parse_cpu(output):
    match = re.search(
        r"CPU utilization for five seconds:\s*(\d+)%"
        r"(?:/\d+%)?;\s*one minute:\s*(\d+)%;"
        r"\s*five minutes:\s*(\d+)%",
        output,
        re.IGNORECASE
    )

    if not match:
        return {
            "cpu_5s": None,
            "cpu_1m": None,
            "cpu_5m": None
        }

    return {
        "cpu_5s": int(match.group(1)),
        "cpu_1m": int(match.group(2)),
        "cpu_5m": int(match.group(3))
    }


def parse_memory(output):
    match = re.search(
        r"^\s*Processor\s+\S+\s+(\d+)\s+(\d+)\s+(\d+)",
        output,
        re.MULTILINE
    )

    if not match:
        return {
            "ram_total": None,
            "ram_used": None,
            "ram_free": None,
            "ram_percent": None
        }

    total = int(match.group(1))
    used = int(match.group(2))
    free = int(match.group(3))

    return {
        "ram_total": total,
        "ram_used": used,
        "ram_free": free,
        "ram_percent": round(used / total * 100, 2)
        if total else None
    }


def parse_interface_status(output):
    result = {}

    for line in output.splitlines():
        match = re.match(
            r"^(\S+)\s+"
            r"(\S+)\s+"
            r"(?:YES|NO)\s+"
            r"\S+\s+"
            r"(administratively down|up|down)\s+"
            r"(up|down)",
            line,
            re.IGNORECASE
        )

        if match:
            result[match.group(1)] = {
                "ip": match.group(2),
                "status": match.group(3).lower(),
                "protocol": match.group(4).lower()
            }

    return result


def parse_interface_counters(output):
    return {
        "input_bytes": extract_number(
            r"\d+\s+packets input,\s*(\d+)\s+bytes",
            output
        ),
        "output_bytes": extract_number(
            r"\d+\s+packets output,\s*(\d+)\s+bytes",
            output
        ),
        "input_packets": extract_number(
            r"(\d+)\s+packets input,",
            output
        ),
        "output_packets": extract_number(
            r"(\d+)\s+packets output,",
            output
        ),
        "input_errors": extract_number(
            r"(\d+)\s+input errors",
            output
        ),
        "output_errors": extract_number(
            r"(\d+)\s+output errors",
            output
        ),
        "crc_errors": extract_number(
            r"(\d+)\s+CRC",
            output
        ),
        "input_rate_5m_bps": extract_number(
            r"5 minute input rate\s+(\d+)\s+bits/sec",
            output
        ),
        "output_rate_5m_bps": extract_number(
            r"5 minute output rate\s+(\d+)\s+bits/sec",
            output
        )
    }


class NetworkMonitor:
    def __init__(self, password):
        self.password = password
        self.previous_counters = {}

    def collect(self, device):
        connection_params = {
            "device_type": device.get(
                "device_type", "cisco_ios"
            ),
            "host": device["host"],
            "username": device["username"],
            "password": self.password,
            "port": 22,
            "conn_timeout": 20,
            "auth_timeout": 20,
            "banner_timeout": 20,
            "fast_cli": False
        }

        result = {
            "device": device["name"],
            "host": device["host"],
            "timestamp": time.strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
            "reachable": False,
            "cpu_5s": None,
            "cpu_1m": None,
            "cpu_5m": None,
            "ram_percent": None,
            "interfaces": [],
            "error": ""
        }

        try:
            with ConnectHandler(**connection_params) as conn:
                result["reachable"] = True

                cpu_output = conn.send_command(
                    "show processes cpu | include CPU utilization",
                    read_timeout=30
                )

                memory_output = conn.send_command(
                    "show memory statistics",
                    read_timeout=30
                )

                status_output = conn.send_command(
                    "show ip interface brief",
                    read_timeout=30
                )

                result.update(parse_cpu(cpu_output))
                result.update(parse_memory(memory_output))

                statuses = parse_interface_status(
                    status_output
                )

                for interface_name in device["interfaces"]:
                    raw = conn.send_command(
                        f"show interfaces {interface_name}",
                        read_timeout=30
                    )

                    counters = parse_interface_counters(raw)

                    interface_status = statuses.get(
                        interface_name, {}
                    )

                    now = time.monotonic()

                    key = (
                        device["host"],
                        interface_name
                    )

                    previous = self.previous_counters.get(key)

                    rx_bps = None
                    tx_bps = None

                    current_rx = counters["input_bytes"]
                    current_tx = counters["output_bytes"]

                    if previous:
                        elapsed = now - previous["time"]

                        if elapsed > 0:
                            if (
                                current_rx is not None
                                and current_rx >= previous["rx"]
                            ):
                                rx_bps = (
                                    (current_rx - previous["rx"])
                                    * 8 / elapsed
                                )

                            if (
                                current_tx is not None
                                and current_tx >= previous["tx"]
                            ):
                                tx_bps = (
                                    (current_tx - previous["tx"])
                                    * 8 / elapsed
                                )

                    if (
                        current_rx is not None
                        and current_tx is not None
                    ):
                        self.previous_counters[key] = {
                            "rx": current_rx,
                            "tx": current_tx,
                            "time": now
                        }

                    interface_data = {
                        "name": interface_name,
                        "ip": interface_status.get(
                            "ip", "unknown"
                        ),
                        "status": interface_status.get(
                            "status", "unknown"
                        ),
                        "protocol": interface_status.get(
                            "protocol", "unknown"
                        ),
                        **counters,
                        "rx_bps": round(rx_bps, 2)
                        if rx_bps is not None else None,
                        "tx_bps": round(tx_bps, 2)
                        if tx_bps is not None else None
                    }

                    result["interfaces"].append(
                        interface_data
                    )

        except Exception as exc:
            result["error"] = str(exc)

        return result
