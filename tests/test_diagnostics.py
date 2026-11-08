"""Offline diagnostic contracts: no network, provider mutation, or mail delivery."""
from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from contextvars import Context
import importlib.util
import io
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import traceback
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from grocery_flyer_watch import diagnostics
from grocery_flyer_watch.review import ReviewError
from grocery_flyer_watch.runtime_preflight import PreflightError


PRIVATE_VALUES = (
    "synthetic-recipient@example.invalid",
    "/synthetic-private-path/account/credentials.json",
    "synthetic_secret_marker_not_a_real_credential",
    "synthetic private message body",
    "synthetic_private_identifier_shaped_value",
)


class DiagnosticsTests(unittest.TestCase):
    def run(self, result=None):
        # Fault injection must not contaminate later tests if cleanup itself is broken.
        return Context().run(super().run, result)

    def setUp(self):
        self.environment = mock.patch.dict(os.environ, {"FLYER_DIAGNOSTICS": "1"})
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.stderr = io.StringIO()
        self.stdout = io.StringIO()
        self.stderr_redirect = redirect_stderr(self.stderr)
        self.stdout_redirect = redirect_stdout(self.stdout)
        self.stderr_redirect.__enter__()
        self.stdout_redirect.__enter__()
        self.addCleanup(self.stderr_redirect.__exit__, None, None, None)
        self.addCleanup(self.stdout_redirect.__exit__, None, None, None)

    def records(self):
        lines = self.stderr.getvalue().splitlines()
        records = [json.loads(line) for line in lines]
        for record in records:
            self.assertEqual(record["schema"], "flyer-diagnostic-v1")
            self.assertIsInstance(record["run_id"], str)
            self.assertRegex(record["run_id"], r"^[A-Za-z0-9_-]{16,64}$")
            self.assertIs(type(record["sequence"]), int)
            self.assertGreater(record["sequence"], 0)
            self.assertIn(record["outcome"],
                          {"started", "completed", "failed", "interrupted"})
            self.assertIsInstance(record["stage"], str)
            if record["outcome"] != "started":
                self.assertIsInstance(record["duration_ms"], (float, int))
                self.assertTrue(math.isfinite(record["duration_ms"]))
                self.assertGreaterEqual(record["duration_ms"], 0)
            if record["outcome"] in {"failed", "interrupted"}:
                self.assertRegex(record["code"], r"^[a-z][a-z0-9_]{0,100}$")
                self.assertRegex(record["error_type"], r"^[A-Za-z][A-Za-z0-9_]{0,100}$")
            self.assertFalse({"args", "kwargs", "result", "message", "exception",
                              "traceback", "path", "recipient", "body"} & record.keys())
        self.assertEqual(self.stdout.getvalue(), "")
        for value in PRIVATE_VALUES:
            self.assertNotIn(value, self.stderr.getvalue())
        return records

    def test_enabled_emits_json_lines_to_stderr_only(self):
        @diagnostics.traced("quality.check")
        def operation():
            return 42

        self.assertEqual(operation(), 42)
        records = self.records()
        self.assertEqual([r["outcome"] for r in records], ["started", "completed"])
        self.assertEqual([r["stage"] for r in records], ["quality.check"] * 2)
        self.assertEqual(len({r["run_id"] for r in records}), 1)
        self.assertLess(records[0]["sequence"], records[1]["sequence"])

    def test_disabled_is_silent_and_preserves_return(self):
        result = object()

        @diagnostics.traced("quality.check")
        def operation():
            return result

        for value in (None, "", "0", "false", "true", "yes", "2"):
            with self.subTest(value=value):
                if value is None:
                    os.environ.pop("FLYER_DIAGNOSTICS", None)
                else:
                    os.environ["FLYER_DIAGNOSTICS"] = value
                self.assertIs(operation(), result)
                self.assertEqual(self.stderr.getvalue(), "")
                self.assertEqual(self.stdout.getvalue(), "")

    def test_disabled_preserves_original_exception_without_output(self):
        os.environ.pop("FLYER_DIAGNOSTICS", None)
        original = RuntimeError(" ".join(PRIVATE_VALUES))

        @diagnostics.traced("quality.check")
        def operation():
            raise original

        with self.assertRaises(RuntimeError) as caught:
            operation()
        self.assertIs(caught.exception, original)
        self.assertEqual(self.stderr.getvalue(), "")
        self.assertEqual(self.stdout.getvalue(), "")

    def test_environment_is_checked_at_call_time(self):
        @diagnostics.traced("quality.check")
        def operation():
            return "unchanged"

        os.environ["FLYER_DIAGNOSTICS"] = "0"
        self.assertEqual(operation(), "unchanged")
        self.assertEqual(self.stderr.getvalue(), "")
        os.environ["FLYER_DIAGNOSTICS"] = "1"
        self.assertEqual(operation(), "unchanged")
        self.assertEqual(len(self.records()), 2)

    def test_arguments_results_and_function_metadata_are_preserved(self):
        received = []
        result = {"status": "authorized", "private": list(PRIVATE_VALUES)}

        @diagnostics.traced("quality.check")
        def operation(argument, *, option):
            """Original operation documentation."""
            received.append((argument, option))
            return result

        argument = {"email": PRIVATE_VALUES[0], "path": PRIVATE_VALUES[1]}
        self.assertIs(operation(argument, option=PRIVATE_VALUES[2]), result)
        self.assertEqual(len(received), 1)
        self.assertIs(received[0][0], argument)
        self.assertEqual(received[0][1], PRIVATE_VALUES[2])
        self.assertEqual(operation.__name__, "operation")
        self.assertEqual(operation.__doc__, "Original operation documentation.")
        self.assertTrue(callable(operation.__wrapped__))
        self.assertEqual(self.records()[-1]["outcome"], "completed")

    def test_arguments_and_results_are_never_stringified(self):
        class PrivateObject:
            def __repr__(self):
                raise AssertionError("Diagnostics must not inspect returned objects")

            def __str__(self):
                raise AssertionError("Diagnostics must not inspect passed objects")

        private = PrivateObject()

        @diagnostics.traced("quality.check")
        def operation(argument, *, option):
            self.assertIs(argument, private)
            self.assertIs(option, private)
            return private

        self.assertIs(operation(private, option=private), private)
        self.assertEqual(self.records()[-1]["outcome"], "completed")

    def test_returned_status_never_becomes_a_delivery_claim(self):
        @diagnostics.traced("quality.check")
        def operation(value):
            return value

        for status in ("sent", "authorized", "accepted", "delivered", "failed",
                       "skipped", "unchanged", PRIVATE_VALUES[4]):
            with self.subTest(status=status):
                self.stderr.seek(0)
                self.stderr.truncate(0)
                result = {"status": status, "recipient": PRIVATE_VALUES[0]}
                self.assertIs(operation(result), result)
                records = self.records()
                self.assertEqual([r["outcome"] for r in records],
                                 ["started", "completed"])
                self.assertNotIn("status", records[-1])
                self.assertNotIn("delivery_authorized", records[-1])
                self.assertNotIn("delivered", records[-1])

    def test_nested_calls_share_correlation_and_order(self):
        @diagnostics.traced("snapshot.validate")
        def inner():
            return 9

        @diagnostics.traced("quality.check")
        def outer():
            return inner()

        self.assertEqual(outer(), 9)
        records = self.records()
        self.assertEqual([(r["stage"], r["outcome"]) for r in records], [
            ("quality.check", "started"),
            ("snapshot.validate", "started"),
            ("snapshot.validate", "completed"),
            ("quality.check", "completed"),
        ])
        self.assertEqual(len({r["run_id"] for r in records}), 1)
        sequences = [r["sequence"] for r in records]
        self.assertEqual(sequences, sorted(set(sequences)))

    def test_independent_calls_receive_distinct_random_ids(self):
        @diagnostics.traced("quality.check")
        def operation():
            return None

        for _ in range(3):
            operation()
        records = self.records()
        self.assertEqual(len(records), 6)
        self.assertEqual(len({r["run_id"] for r in records}), 3)
        for first, last in zip(records[::2], records[1::2]):
            self.assertEqual(first["run_id"], last["run_id"])

    def test_failure_preserves_exception_identity_message_and_traceback(self):
        message = " | ".join(PRIVATE_VALUES)
        original = RuntimeError(message)

        @diagnostics.traced("quality.check")
        def failing_operation():
            raise original

        try:
            failing_operation()
        except RuntimeError as caught:
            self.assertIs(caught, original)
            self.assertEqual(str(caught), message)
            self.assertIn("failing_operation",
                          [frame.name for frame in traceback.extract_tb(caught.__traceback__)])
        else:
            self.fail("The decorated operation must still raise its original exception")
        records = self.records()
        self.assertEqual([r["outcome"] for r in records], ["started", "failed"])
        self.assertEqual(records[-1]["error_type"], "RuntimeError")

    def test_nested_failures_keep_correlation_and_reset_context(self):
        original = ReviewError("invalid_cash_price")

        @diagnostics.traced("snapshot.validate")
        def inner():
            raise original

        @diagnostics.traced("quality.check")
        def outer():
            return inner()

        @diagnostics.traced("state.read")
        def later():
            return None

        with self.assertRaises(ReviewError) as caught:
            outer()
        self.assertIs(caught.exception, original)
        later()
        records = self.records()
        self.assertEqual([r["outcome"] for r in records],
                         ["started", "started", "failed", "failed", "started", "completed"])
        self.assertEqual(len({r["run_id"] for r in records[:4]}), 1)
        self.assertNotEqual(records[0]["run_id"], records[4]["run_id"])
        self.assertEqual(records[2]["code"], "invalid_cash_price")
        self.assertEqual(records[3]["code"], "invalid_cash_price")

    def test_interruptions_are_reported_and_original_exceptions_reraised(self):
        @diagnostics.traced("quality.check")
        def operation(exception):
            raise exception

        for original in (KeyboardInterrupt(PRIVATE_VALUES[0]), SystemExit(PRIVATE_VALUES[2])):
            with self.subTest(exception_type=type(original).__name__):
                self.stderr.seek(0)
                self.stderr.truncate(0)
                with self.assertRaises(type(original)) as caught:
                    operation(original)
                self.assertIs(caught.exception, original)
                records = self.records()
                self.assertEqual([r["outcome"] for r in records], ["started", "interrupted"])

    def test_interruptions_do_not_leak_run_context_to_next_call(self):
        @diagnostics.traced("quality.check")
        def operation(interrupt=False):
            if interrupt:
                raise KeyboardInterrupt

        with self.assertRaises(KeyboardInterrupt):
            operation(True)
        operation()
        records = self.records()
        self.assertEqual(len(records), 4)
        self.assertNotEqual(records[0]["run_id"], records[2]["run_id"])
        self.assertEqual(records[-1]["outcome"], "completed")

    def test_source_controlled_validation_codes_are_preserved(self):
        for exception in (ReviewError("invalid_cash_price"),
                          ReviewError("publication_not_verified"),
                          PreflightError("invalid_observation_time")):
            with self.subTest(exception=exception.args[0]):
                self.assertEqual(diagnostics.safe_code(exception), exception.args[0])

    def test_unknown_identifier_shaped_messages_do_not_become_codes(self):
        for error_class in (ValueError, RuntimeError, ReviewError, PreflightError):
            for message in PRIVATE_VALUES:
                with self.subTest(error_class=error_class.__name__, message=message):
                    code = diagnostics.safe_code(error_class(message))
                    self.assertIsInstance(code, str)
                    self.assertRegex(code, r"^[a-z][a-z0-9_]{0,100}$")
                    self.assertNotEqual(code, message)
                    self.assertNotIn(message, code)

    def test_known_code_with_private_suffix_is_not_a_safe_code(self):
        for message in ("invalid_cash_price: " + PRIVATE_VALUES[0],
                        "invalid_cash_price_" + PRIVATE_VALUES[4],
                        "invalid_cash_price\n" + PRIVATE_VALUES[2]):
            with self.subTest(message=message):
                code = diagnostics.safe_code(ReviewError(message))
                self.assertNotIn(message, code)
                self.assertNotIn(PRIVATE_VALUES[0], code)
                self.assertNotIn(PRIVATE_VALUES[2], code)
                self.assertNotIn(PRIVATE_VALUES[4], code)
                self.assertNotEqual(code, "invalid_cash_price")

    def test_exception_strings_are_not_evaluated(self):
        class HostileError(Exception):
            def __str__(self):
                raise AssertionError("Diagnostics must not stringify exceptions")

            def __repr__(self):
                raise AssertionError("Diagnostics must not format exceptions")

        original = HostileError(PRIVATE_VALUES[0])

        @diagnostics.traced("quality.check")
        def operation():
            raise original

        code = diagnostics.safe_code(original)
        self.assertIsInstance(code, str)
        self.assertNotIn(PRIVATE_VALUES[0], code)
        with self.assertRaises(HostileError) as caught:
            operation()
        self.assertIs(caught.exception, original)
        self.assertEqual(self.records()[-1]["outcome"], "failed")

    def test_untrusted_exception_class_names_are_not_logged(self):
        for name in (PRIVATE_VALUES[0], PRIVATE_VALUES[4]):
            with self.subTest(name=name):
                self.stderr.seek(0)
                self.stderr.truncate(0)
                error_type = type(name, (Exception,), {})
                original = error_type(PRIVATE_VALUES[3])

                @diagnostics.traced("quality.check")
                def operation():
                    raise original

                with self.assertRaises(error_type) as caught:
                    operation()
                self.assertIs(caught.exception, original)
                records = self.records()
                self.assertNotEqual(records[-1]["error_type"], name)

    def test_untrusted_stage_names_use_a_static_fallback(self):
        for stage in PRIVATE_VALUES:
            with self.subTest(stage=stage):
                self.stderr.seek(0)
                self.stderr.truncate(0)

                @diagnostics.traced(stage)
                def operation():
                    return 7

                self.assertEqual(operation(), 7)
                self.assertEqual([r["stage"] for r in self.records()], ["operation"] * 2)

    def test_provider_and_filesystem_errors_do_not_log_their_payloads(self):
        exceptions = (
            (subprocess.TimeoutExpired(PRIVATE_VALUES[1], 5,
                                       output=PRIVATE_VALUES[2], stderr=PRIVATE_VALUES[0]),
             "subprocess_timeout"),
            (subprocess.CalledProcessError(2, PRIVATE_VALUES[1],
                                          output=PRIVATE_VALUES[2], stderr=PRIVATE_VALUES[0]),
             "subprocess_nonzero_exit"),
            (FileNotFoundError(2, PRIVATE_VALUES[3], PRIVATE_VALUES[1]),
             "input_or_executable_missing"),
            (PermissionError(13, PRIVATE_VALUES[3], PRIVATE_VALUES[1]),
             "filesystem_permission_denied"),
            (json.JSONDecodeError(PRIVATE_VALUES[3], PRIVATE_VALUES[2], 1), "invalid_json"),
        )

        @diagnostics.traced("collector.read")
        def operation(exception):
            raise exception

        for original, expected_code in exceptions:
            with self.subTest(exception_type=type(original).__name__):
                self.stderr.seek(0)
                self.stderr.truncate(0)
                self.assertEqual(diagnostics.safe_code(original), expected_code)
                with self.assertRaises(type(original)) as caught:
                    operation(original)
                self.assertIs(caught.exception, original)
                self.assertEqual(self.records()[-1]["code"], expected_code)

    def test_run_id_generation_failure_does_not_skip_operation(self):
        result = object()
        calls = []

        @diagnostics.traced("quality.check")
        def operation():
            calls.append(True)
            return result

        with mock.patch.object(diagnostics, "uuid4", side_effect=OSError(PRIVATE_VALUES[2])):
            self.assertIs(operation(), result)
        self.assertEqual(calls, [True])

    def test_clock_failure_does_not_skip_operation(self):
        calls = []

        @diagnostics.traced("quality.check")
        def operation():
            calls.append(True)
            return 7

        with mock.patch.object(diagnostics, "monotonic", side_effect=RuntimeError(PRIVATE_VALUES[2])):
            self.assertEqual(operation(), 7)
        self.assertEqual(calls, [True])

    def test_initialization_failure_leaves_no_correlation_context(self):
        @diagnostics.traced("quality.check")
        def operation():
            return 7

        for helper in ("uuid4", "monotonic"):
            with self.subTest(helper=helper):
                self.stderr.seek(0)
                self.stderr.truncate(0)
                with mock.patch.object(diagnostics, helper, side_effect=OSError(PRIVATE_VALUES[2])):
                    self.assertEqual(operation(), 7)
                self.stderr.seek(0)
                self.stderr.truncate(0)
                operation()
                operation()
                records = self.records()
                self.assertEqual(len(records), 4)
                self.assertNotEqual(records[0]["run_id"], records[2]["run_id"])

    def test_terminal_clock_failure_does_not_replace_original_exception(self):
        original = ReviewError("invalid_cash_price")

        @diagnostics.traced("quality.check")
        def operation():
            raise original

        with mock.patch.object(diagnostics, "monotonic",
                               side_effect=[0, RuntimeError(PRIVATE_VALUES[2])]):
            with self.assertRaises(ReviewError) as caught:
                operation()
        self.assertIs(caught.exception, original)

    def test_terminal_clock_failure_does_not_retry_or_replace_success(self):
        result = object()
        calls = []

        @diagnostics.traced("quality.check")
        def operation():
            calls.append(True)
            return result

        with mock.patch.object(diagnostics, "monotonic",
                               side_effect=[0, RuntimeError(PRIVATE_VALUES[2])]):
            self.assertIs(operation(), result)
        self.assertEqual(calls, [True])

    def test_stderr_write_failure_does_not_change_operation(self):
        result = object()
        calls = []

        @diagnostics.traced("quality.check")
        def operation():
            calls.append(True)
            return result

        broken_stderr = mock.Mock()
        broken_stderr.write.side_effect = OSError(PRIVATE_VALUES[2])
        with mock.patch.object(sys, "stderr", broken_stderr):
            self.assertIs(operation(), result)
        self.assertEqual(calls, [True])
        self.assertEqual(self.stdout.getvalue(), "")

    def test_stderr_write_failure_does_not_replace_original_exception(self):
        original = ValueError(PRIVATE_VALUES[1])

        @diagnostics.traced("quality.check")
        def operation():
            raise original

        broken_stderr = mock.Mock()
        broken_stderr.write.side_effect = OSError(PRIVATE_VALUES[2])
        with mock.patch.object(sys, "stderr", broken_stderr):
            with self.assertRaises(ValueError) as caught:
                operation()
        self.assertIs(caught.exception, original)

    def test_stderr_flush_failure_does_not_change_operation(self):
        result = object()

        @diagnostics.traced("quality.check")
        def operation():
            return result

        broken_stderr = mock.Mock()
        broken_stderr.flush.side_effect = OSError(PRIVATE_VALUES[2])
        with mock.patch.object(sys, "stderr", broken_stderr):
            self.assertIs(operation(), result)


class DiagnosticsRecoveryTests(unittest.TestCase):
    """Exercise pinned-byte recovery and a read-only CLI, never a provider action."""

    @staticmethod
    def bootstrap():
        spec = importlib.util.spec_from_file_location(
            "diagnostics_runtime_bootstrap_test", ROOT / "automation" / "runtime_bootstrap.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_diagnostics_is_required_in_recovery_manifest(self):
        bootstrap = self.bootstrap()
        diagnostic_path = "src/grocery_flyer_watch/diagnostics.py"
        self.assertIn(diagnostic_path, bootstrap.MODULES)
        manifest = {
            "repository_id": 1,
            "commit": "a" * 40,
            "git_blobs": {path: "b" * 40 for path in bootstrap.MODULES - {diagnostic_path}},
        }
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary) / "runtime"
            with self.assertRaisesRegex(bootstrap.RecoveryError, "incomplete_runtime_manifest"):
                bootstrap.prepare(destination, manifest)
            self.assertFalse(destination.exists())

    def test_recovered_runtime_validates_offline_with_clean_stdout(self):
        bootstrap = self.bootstrap()
        with tempfile.TemporaryDirectory() as temporary:
            temporary = Path(temporary)
            cache = temporary / "cache"
            destination = temporary / "runtime"
            blobs = {}
            for relative in bootstrap.MODULES:
                raw = (ROOT / relative).read_bytes()
                target = cache / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(raw)
                blobs[relative] = bootstrap.blob_id(raw)
            # Synthetic local manifest verifies recovery only, not publication evidence.
            manifest = {"repository_id": 1, "commit": "a" * 40, "git_blobs": blobs}
            result = bootstrap.prepare(destination, manifest, cache)
            self.assertEqual(result["restored_modules"], len(bootstrap.MODULES))
            self.assertFalse(result["delivery_authorized"])
            command = [sys.executable, "-m", "grocery_flyer_watch", "validate",
                       str(ROOT / "data" / "latest.json")]
            environment = dict(os.environ, PYTHONPATH=str(destination / "src"),
                               FLYER_DIAGNOSTICS="1")
            process = subprocess.run(command, cwd=destination, env=environment,
                                     capture_output=True, text=True, timeout=20, check=False)
            self.assertEqual(process.returncode, 0, process.stderr)
            self.assertEqual(process.stdout, "Valid public snapshot\n")
            records = [json.loads(line) for line in process.stderr.splitlines()]
            self.assertTrue(records)
            self.assertTrue(all(record["schema"] == "flyer-diagnostic-v1" for record in records))
            self.assertIn("snapshot.validate", {record["stage"] for record in records})
            self.assertNotIn(str(ROOT), process.stderr)
            self.assertNotIn(str(temporary), process.stderr)


if __name__ == "__main__":
    unittest.main()
