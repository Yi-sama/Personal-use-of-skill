"""Read v2rayN metadata without exposing credentials or modifying its database."""

import argparse
from contextlib import closing
import json
import sqlite3
from pathlib import Path


def inspect(directory, node_name):
    directory = Path(directory)
    gui = json.loads((directory / "guiConfigs/guiNConfig.json").read_text("utf-8-sig"))
    database = directory / "guiConfigs/guiNDB.db"
    with closing(sqlite3.connect(database.resolve().as_uri() + "?mode=ro", uri=True)) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            "SELECT IndexId, Remarks, ConfigType, Address, Port, Id FROM ProfileItem "
            "WHERE Remarks = ? OR IndexId = ?",
            (node_name, gui.get("IndexId")),
        ).fetchall()
    matches = [row for row in rows if row["Remarks"] == node_name]
    if len(matches) != 1:
        raise ValueError("The requested node name is missing or ambiguous.")
    expected = matches[0]
    if expected["ConfigType"] != 5:
        raise ValueError("The requested profile is not VLESS.")
    active = next((row["Remarks"] for row in rows if row["IndexId"] == gui.get("IndexId")), None)
    core_file = directory / "binConfigs/config.json"
    core = json.loads(core_file.read_text("utf-8-sig")) if core_file.exists() else {}
    matched = False if core_file.exists() else None
    for outbound in core.get("outbounds", []):
        if outbound.get("tag") != "proxy":
            continue
        if outbound.get("protocol") == "vless":
            for server in outbound.get("settings", {}).get("vnext", []):
                matched |= (
                    server.get("address") == expected["Address"]
                    and server.get("port") == expected["Port"]
                    and any(user.get("id") == expected["Id"] for user in server.get("users", []))
                )
        elif outbound.get("type") == "vless":
            matched |= (
                outbound.get("server") == expected["Address"]
                and outbound.get("server_port") == expected["Port"]
                and outbound.get("uuid") == expected["Id"]
            )
    inbounds = [
        item for item in core.get("inbounds", [])
        if item.get("listen") in ("127.0.0.1", "::1")
        and item.get("protocol", item.get("type")) in ("mixed", "http", "socks")
    ]
    inbound = next(
        (item for item in inbounds if item.get("protocol", item.get("type")) == "mixed"),
        next((item for item in inbounds if item.get("protocol", item.get("type")) == "http"), None),
    )
    port = inbound.get("port", inbound.get("listen_port")) if inbound else None
    host = "[::1]" if inbound and inbound["listen"] == "::1" else "127.0.0.1"
    source = "core"
    if not core_file.exists():
        # Generated core files are not guaranteed to remain on disk.
        inbound = next(iter(gui.get("Inbound", [])), None)
        port = inbound.get("LocalPort") if inbound else None
        host = "127.0.0.1"
        source = "gui"
    return {
        "expected_node": node_name,
        "active_node": active,
        "configured_for_expected": gui.get("IndexId") == expected["IndexId"],
        "core_matches_expected": matched,
        "core_config_present": core_file.exists(),
        "inbound_source": source,
        "port": port,
        "listen_host": host.strip("[]") if port else None,
        "http_proxy": f"http://{host}:{port}" if port else None,
        "socks_proxy": (
            f"socks5h://{host}:{port}"
            if port and (
                source == "gui" or inbound.get("protocol", inbound.get("type")) == "mixed"
            ) else None
        ),
        "tun_enabled": bool(gui.get("TunModeItem", {}).get("EnableTun")),
        "system_proxy_type": gui.get("SystemProxyItem", {}).get("SysProxyType"),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory")
    parser.add_argument("--node", default="US-owner-unlimited")
    args = parser.parse_args()
    try:
        print(json.dumps(inspect(args.directory, args.node), ensure_ascii=True))
    except (OSError, ValueError, sqlite3.Error) as error:
        parser.exit(1, f"v2rayN inspection failed: {type(error).__name__}: {error}\n")


if __name__ == "__main__":
    main()
