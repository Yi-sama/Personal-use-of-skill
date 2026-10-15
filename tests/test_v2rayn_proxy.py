"""Offline behavioral checks; no live proxy configuration is modified."""

import hashlib
from contextlib import closing
import importlib.util
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / ".agents/skills/v2rayn-proxy/scripts/inspect_v2rayn.py"
)
spec = importlib.util.spec_from_file_location("v2rayn_inspector", SCRIPT)
inspector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(inspector)


class ProxyInspectionTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="v2rayn-proxy-test-")
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        (self.directory / "guiConfigs").mkdir()
        (self.directory / "binConfigs").mkdir()
        self.gui_file = self.directory / "guiConfigs/guiNConfig.json"
        self.core_file = self.directory / "binConfigs/config.json"
        self.db_file = self.directory / "guiConfigs/guiNDB.db"
        self.gui = {
            "IndexId": "target",
            "Inbound": [{"LocalPort": 32123, "Protocol": "socks", "AllowLANConn": False}],
            "TunModeItem": {"EnableTun": False},
            "SystemProxyItem": {"SysProxyType": 0},
        }
        self.core = {
            "inbounds": [{"protocol": "mixed", "listen": "127.0.0.1", "port": 32123}],
            "outbounds": [{
                "tag": "proxy", "protocol": "vless",
                "settings": {"vnext": [{
                    "address": "proxy.invalid", "port": 443,
                    "users": [{"id": "fixture-secret-not-for-output"}],
                }]},
            }],
        }
        self.write_json()
        with closing(sqlite3.connect(self.db_file)) as connection, connection:
            connection.execute(
                "CREATE TABLE ProfileItem "
                "(IndexId TEXT, Remarks TEXT, ConfigType INTEGER, Address TEXT, Port INTEGER, Id TEXT)"
            )
            connection.execute(
                "INSERT INTO ProfileItem VALUES (?,?,?,?,?,?)",
                ("target", "US-owner-unlimited", 5, "proxy.invalid", 443, "fixture-secret-not-for-output"),
            )

    def write_json(self):
        self.gui_file.write_text(json.dumps(self.gui), encoding="utf-8")
        self.core_file.write_text(json.dumps(self.core), encoding="utf-8")

    def inspect(self):
        return inspector.inspect(self.directory, "US-owner-unlimited")

    def test_verified_endpoint_and_no_secrets_or_writes(self):
        before = hashlib.sha256(self.db_file.read_bytes()).hexdigest()
        state = self.inspect()
        self.assertTrue(state["configured_for_expected"])
        self.assertTrue(state["core_matches_expected"])
        self.assertEqual(state["http_proxy"], "http://127.0.0.1:32123")
        self.assertEqual(state["socks_proxy"], "socks5h://127.0.0.1:32123")
        self.assertFalse(state["tun_enabled"])
        self.assertNotIn("fixture-secret", json.dumps(state))
        self.assertNotIn("proxy.invalid", json.dumps(state))
        self.assertEqual(before, hashlib.sha256(self.db_file.read_bytes()).hexdigest())

    def test_saved_node_does_not_prove_running_core_matches(self):
        self.core["outbounds"][0]["settings"]["vnext"][0]["users"][0]["id"] = "stale-core"
        self.write_json()
        state = self.inspect()
        self.assertTrue(state["configured_for_expected"])
        self.assertFalse(state["core_matches_expected"])

    def test_different_active_node(self):
        self.gui["IndexId"] = "other"
        self.write_json()
        self.assertFalse(self.inspect()["configured_for_expected"])

    def test_duplicate_and_missing_names_stop(self):
        with self.assertRaisesRegex(ValueError, "missing or ambiguous"):
            inspector.inspect(self.directory, "not-present")
        with closing(sqlite3.connect(self.db_file)) as connection, connection:
            connection.execute("INSERT INTO ProfileItem SELECT 'duplicate', Remarks, ConfigType, Address, Port, Id FROM ProfileItem")
        with self.assertRaisesRegex(ValueError, "missing or ambiguous"):
            self.inspect()

    def test_lan_only_listener_is_not_used(self):
        self.core["inbounds"][0]["listen"] = "0.0.0.0"
        self.write_json()
        self.assertIsNone(self.inspect()["http_proxy"])

    def test_missing_generated_file_keeps_gui_metadata_evidence_separate(self):
        self.core_file.unlink()
        state = self.inspect()
        self.assertTrue(state["configured_for_expected"])
        self.assertIsNone(state["core_matches_expected"])
        self.assertFalse(state["core_config_present"])
        self.assertEqual(state["inbound_source"], "gui")
        self.assertEqual(state["http_proxy"], "http://127.0.0.1:32123")

    def test_singbox_and_ipv6(self):
        self.core = {
            "inbounds": [{"type": "mixed", "listen": "::1", "listen_port": 32124}],
            "outbounds": [{
                "tag": "proxy", "type": "vless", "server": "proxy.invalid",
                "server_port": 443, "uuid": "fixture-secret-not-for-output",
            }],
        }
        self.write_json()
        state = self.inspect()
        self.assertTrue(state["core_matches_expected"])
        self.assertEqual(state["http_proxy"], "http://[::1]:32124")


if __name__ == "__main__":
    unittest.main()
