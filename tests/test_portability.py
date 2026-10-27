"""Offline tests: no real mail, web requests or public repository writes."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from grocery_flyer_watch.core import fingerprint, render_report, validate_snapshot
from grocery_flyer_watch.runner import (check_scope, collect, event_key, load_config,
    read_state, run, seed, send_smtp)


def snapshot():
    today = datetime.now(ZoneInfo("America/Toronto")).date()
    return {"flyer": {"id": "demo-1", "retailer": "Metro", "market": "Toronto, Ontario",
        "starts_on": today.isoformat(), "ends_on": (today + timedelta(days=6)).isoformat(),
        "url": "https://www.metro.ca/en/flyer"}, "offers": [{"name": "Example rice", "price_cad": "9.99",
        "pricing": "package", "size_g": 4540, "priority": 5, "why": "Synthetic test fixture, not an advertised price."}]}


class PortableTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.c = {"market": "Toronto, Ontario", "retailer": "Metro", "timezone": "America/Toronto",
            "sources": ["https://www.metro.ca/en/flyer", "https://flipp.com/en-ca/toronto-on"],
            "collector": [], "state_file": self.root / "private" / "state.json", "output_dir": self.root / "public",
            "publication": "local", "notification": "smtp"}
        self.s = snapshot()
        self.input = self.root / "input.json"
        self.save(self.s)

    def save(self, value):
        self.input.write_text(json.dumps(value), encoding="utf-8")

    def test_another_city_and_official_source(self):
        validate_snapshot(self.s)
        self.assertIn("Toronto, Ontario", render_report(self.s))
        self.assertNotIn("Kingston", render_report(self.s))

    def test_another_retailer(self):
        self.s["flyer"]["retailer"] = "Example Grocery"
        self.s["flyer"]["url"] = "https://grocer.example/flyer"
        validate_snapshot(self.s)

    def test_market_in_fingerprint(self):
        other = copy.deepcopy(self.s)
        other["flyer"]["market"] = "Ottawa, Ontario"
        self.assertNotEqual(fingerprint(other), fingerprint(self.s))

    def test_source_ids_do_not_duplicate_delivery(self):
        other = copy.deepcopy(self.s)
        other["flyer"]["id"] = "different-mirror-id"
        other["flyer"]["url"] = "https://flipp.com/en-ca/toronto-on"
        self.assertEqual(event_key(other), event_key(self.s))

    def test_restrictions_are_material(self):
        other = copy.deepcopy(self.s)
        other["offers"][0]["restrictions"] = "Member price; limit 2"
        self.assertNotEqual(event_key(other), event_key(self.s))

    def test_reversed_dates_rejected(self):
        self.s["flyer"]["starts_on"] = "2099-01-01"
        with self.assertRaises(ValueError):
            validate_snapshot(self.s)

    def test_real_calendar_date_required(self):
        self.s["flyer"]["ends_on"] = "2026-02-30"
        with self.assertRaises(ValueError):
            validate_snapshot(self.s)

    def test_wrong_region_rejected(self):
        self.s["flyer"]["market"] = "Montreal, Quebec"
        with self.assertRaises(ValueError):
            check_scope(self.c, self.s)

    def test_unconfigured_source_rejected(self):
        self.s["flyer"]["url"] = "https://unconfigured.example/flyer"
        with self.assertRaises(ValueError):
            check_scope(self.c, self.s)

    def test_preview_needs_two_hosts(self):
        self.s["flyer"]["starts_on"] = self.s["flyer"]["ends_on"]
        with self.assertRaises(ValueError):
            check_scope(self.c, self.s)
        self.s["flyer"]["sources"] = ["https://flipp.com/en-ca/toronto-on"]
        check_scope(self.c, self.s)

    def test_dry_run_has_no_side_effects(self):
        pub, mail = Mock(), Mock()
        self.assertTrue(run(self.c, self.input, True, pub, mail))
        pub.assert_not_called()
        mail.assert_not_called()
        self.assertFalse(self.c["state_file"].exists())
        self.assertFalse(self.c["output_dir"].exists())

    def test_repeat_silent_and_no_duplicate(self):
        pub, mail = Mock(), Mock()
        self.assertEqual(len(run(self.c, self.input, publisher=pub, notifier=mail)), 1)
        self.assertEqual(run(self.c, self.input, publisher=pub, notifier=mail), [])
        pub.assert_called_once()
        mail.assert_called_once()

    def test_delivery_retries_after_publication(self):
        pub, mail = Mock(), Mock(side_effect=[RuntimeError("temporary failure"), None])
        with self.assertRaises(RuntimeError):
            run(self.c, self.input, publisher=pub, notifier=mail)
        self.save({"status": "ok", "snapshots": []})
        run(self.c, self.input, publisher=pub, notifier=mail)
        pub.assert_called_once()
        self.assertEqual(mail.call_count, 2)
        self.assertTrue(next(iter(read_state(self.c["state_file"])["events"].values()))["notified"])

    def test_pending_delivery_retries_even_when_collector_unavailable(self):
        pub, mail = Mock(), Mock(side_effect=[RuntimeError("temporary failure"), None])
        with self.assertRaises(RuntimeError):
            run(self.c, self.input, publisher=pub, notifier=mail)
        self.save({"status": "unavailable", "snapshots": []})
        with self.assertRaises(ValueError):
            run(self.c, self.input, publisher=pub, notifier=mail)
        self.assertEqual(mail.call_count, 2)
        pub.assert_called_once()

    def test_seed_suppresses_historical_delivery(self):
        seed(self.c, self.s)
        pub, mail = Mock(), Mock()
        self.assertEqual(run(self.c, self.input, publisher=pub, notifier=mail), [])
        pub.assert_not_called()
        mail.assert_not_called()

    def test_local_archive_contains_no_delivery_info(self):
        self.c["notification"] = "none"
        run(self.c, self.input)
        files = list(self.c["output_dir"].rglob("*.json"))
        self.assertEqual(len(files), 1)
        self.assertEqual(set(json.loads(files[0].read_text())), {"flyer", "offers"})

    def test_command_adapter_and_secret_isolation(self):
        self.c["collector"] = ["example-collector", "--json"]
        result = subprocess.CompletedProcess(self.c["collector"], 0, json.dumps({"status": "ok", "snapshots": [self.s]}), "")
        with patch.dict(os.environ, {"FLYER_SMTP_PASSWORD": "private", "GH_TOKEN": "private"}):
            with patch("grocery_flyer_watch.runner.subprocess.run", return_value=result) as process:
                self.assertEqual(len(collect(self.c)), 1)
                kwargs = process.call_args.kwargs
                self.assertNotIn("FLYER_SMTP_PASSWORD", kwargs["env"])
                self.assertNotIn("GH_TOKEN", kwargs["env"])
                self.assertFalse(kwargs.get("shell", False))

    def test_config_relative_paths(self):
        path = self.root / "watch.toml"
        path.write_text('market="Toronto, Ontario"\nretailer="Metro"\ntimezone="America/Toronto"\nsources=["https://www.metro.ca/en/flyer", "https://flipp.com/en-ca/toronto-on"]\nstate_file="private/state.json"\noutput_dir="public"\n')
        c = load_config(path)
        self.assertEqual(c["state_file"], self.root / "private" / "state.json")

    def test_private_state_cannot_be_in_public_output(self):
        path = self.root / "watch.toml"
        path.write_text('market="Toronto, Ontario"\nretailer="Metro"\ntimezone="America/Toronto"\nsources=["https://www.metro.ca/en/flyer", "https://flipp.com/en-ca/toronto-on"]\nstate_file="public/state.json"\noutput_dir="public"\n')
        with self.assertRaises(ValueError):
            load_config(path)

    def test_smtp_uses_tls_and_stable_message_id(self):
        env = {"FLYER_SMTP_HOST": "smtp.example.invalid", "FLYER_SMTP_MODE": "ssl",
               "FLYER_MAIL_FROM": "sender" + chr(64) + "example.invalid", "FLYER_MAIL_TO": "recipient" + chr(64) + "example.invalid"}
        with patch.dict(os.environ, env, clear=True):
            with patch("grocery_flyer_watch.runner.smtplib.SMTP_SSL") as smtp:
                smtp.return_value.__enter__.return_value.send_message.return_value = {}
                send_smtp(self.s, event_key(self.s))
                message = smtp.return_value.__enter__.return_value.send_message.call_args.args[0]
                self.assertIn(event_key(self.s), message["Message-ID"])
                self.assertIsNotNone(smtp.call_args.kwargs["context"])

    def test_git_publication_pushes_only_public_artifacts(self):
        repo, remote = self.root / "checkout", self.root / "remote.git"
        def git(*args):
            return subprocess.run(["git", *args], capture_output=True, text=True, check=True)
        git("init", "--bare", str(remote))
        git("init", str(repo))
        git("-C", str(repo), "config", "user.name", "Test Bot")
        git("-C", str(repo), "config", "user.email", "bot" + chr(64) + "example.invalid")
        git("-C", str(repo), "commit", "--allow-empty", "-m", "Initialize test")
        git("-C", str(repo), "remote", "add", "origin", str(remote))
        git("-C", str(repo), "push", "-u", "origin", "HEAD")
        self.c.update(output_dir=repo / "public", publication="git", notification="none")
        run(self.c, self.input)
        tracked = git("-C", str(repo), "ls-files").stdout.splitlines()
        self.assertEqual(len(tracked), 2)
        self.assertTrue(all(p.startswith("public/") for p in tracked))
        self.assertEqual(git("-C", str(repo), "rev-parse", "HEAD").stdout,
                         git("--git-dir", str(remote), "rev-parse", "HEAD").stdout)

    def test_existing_lock_blocks_parallel_run(self):
        self.c["state_file"].parent.mkdir()
        self.c["state_file"].with_name("state.json.lock").mkdir()
        with self.assertRaises(RuntimeError):
            run(self.c, self.input, publisher=Mock(), notifier=Mock())

    def test_failure_does_not_leak_private_exception(self):
        from grocery_flyer_watch.__main__ import main
        with patch.object(sys, "argv", ["grocery-flyer-watch", "run", "--config", "missing"]):
            with patch("sys.stderr") as stderr:
                self.assertEqual(main(), 2)
                self.assertNotIn("Traceback", "".join(str(c) for c in stderr.write.call_args_list))


if __name__ == "__main__":
    unittest.main()
