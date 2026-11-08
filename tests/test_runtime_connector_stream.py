"""Offline synthetic regression tests for connector-streamed runtime recovery.

No production source fixtures, provider mutations, credentials or mail.
"""
from __future__ import annotations

import base64
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    'runtime_bootstrap', ROOT / 'automation/runtime_bootstrap.py')
bootstrap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bootstrap)


class ConnectorStreamRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.module_bytes = {rel: b'# Synthetic source; not production\n'
                             for rel in bootstrap.MODULES}
        main_path = 'src/grocery_flyer_watch/__main__.py'
        self.module_bytes[main_path] = (
            b'import sys\n'
            b'raise SystemExit(0 if sys.argv[1:] == ["quality", "--help"] else 1)\n')
        self.manifest = {
            'repository_id': 1, 'commit': 'a' * 40,
            'git_blobs': {rel: bootstrap.blob_id(raw)
                          for rel, raw in self.module_bytes.items()},
        }
        self.bundle = {
            'format': 'pinned-connector-module-cache-v1',
            'repository_id': 1, 'commit': 'a' * 40,
            'modules': {rel: base64.encodebytes(raw).decode('ascii')
                        for rel, raw in self.module_bytes.items()},
        }

    def decode(self):
        return bootstrap.decode_connector_bundle(
            json.dumps(self.bundle).encode('utf-8'), self.manifest)

    def test_complete_stream_repairs_without_cache_directory(self):
        output = bootstrap.prepare(
            self.root / 'runtime', self.manifest,
            connector_modules=self.decode())
        self.assertEqual(output['restored_modules'], len(bootstrap.MODULES))
        self.assertFalse(output['delivery_authorized'])
        for rel, raw in self.module_bytes.items():
            self.assertEqual((self.root / 'runtime' / rel).read_bytes(), raw)

    def test_cli_reads_stdin_bundle_and_probes_runtime(self):
        manifest_path = self.root / 'manifest.json'
        manifest_path.write_text(json.dumps(self.manifest), encoding='utf-8')
        result = subprocess.run([
            sys.executable, str(ROOT / 'automation/runtime_bootstrap.py'),
            '--root', str(self.root / 'runtime'),
            '--manifest', str(manifest_path), '--cache-stdin',
        ], input=json.dumps(self.bundle).encode('utf-8'),
            capture_output=True, timeout=15, check=False)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        self.assertEqual(json.loads(result.stdout)['status'], 'runtime_ready')

    def test_tampered_file_fails_before_any_module_written(self):
        rel = next(iter(self.bundle['modules']))
        self.bundle['modules'][rel] = base64.b64encode(b'tampered').decode()
        with self.assertRaisesRegex(bootstrap.RecoveryError, 'cache_integrity_mismatch'):
            bootstrap.prepare(self.root / 'runtime', self.manifest,
                              connector_modules=self.decode())
        self.assertFalse((self.root / 'runtime').exists())

    def test_missing_streamed_module_fails_without_writes(self):
        self.bundle['modules'].pop(next(iter(self.bundle['modules'])))
        with self.assertRaisesRegex(bootstrap.RecoveryError, 'connector_module_missing'):
            bootstrap.prepare(self.root / 'runtime', self.manifest,
                              connector_modules=self.decode())
        self.assertFalse((self.root / 'runtime').exists())

    def test_wrong_repo_or_commit_pin_rejected(self):
        for field, new in [('repository_id', 2), ('commit', 'b' * 40)]:
            with self.subTest(field=field):
                original = self.bundle[field]
                self.bundle[field] = new
                with self.assertRaisesRegex(bootstrap.RecoveryError,
                                            'connector_bundle_pin_mismatch'):
                    self.decode()
                self.bundle[field] = original

    def test_unexpected_module_rejected(self):
        self.bundle['modules']['src/grocery_flyer_watch/unknown.py'] = 'YQ=='
        with self.assertRaisesRegex(bootstrap.RecoveryError,
                                    'connector_bundle_unexpected_module'):
            self.decode()

    def test_bad_base64_rejected(self):
        self.bundle['modules'][next(iter(self.bundle['modules']))] = '***'
        with self.assertRaisesRegex(bootstrap.RecoveryError, 'invalid_connector_base64'):
            self.decode()

    def test_bundle_size_is_bounded(self):
        with self.assertRaisesRegex(bootstrap.RecoveryError, 'connector_bundle_too_large'):
            bootstrap.decode_connector_bundle(
                b'x' * (bootstrap.MAX_CONNECTOR_BUNDLE_BYTES + 1), self.manifest)

    def test_existing_runtime_edit_never_overwritten(self):
        target = self.root / 'runtime'
        bootstrap.prepare(target, self.manifest, connector_modules=self.decode())
        rel = next(iter(bootstrap.MODULES))
        (target / rel).write_text('unexpected edit')
        with self.assertRaisesRegex(bootstrap.RecoveryError, 'runtime_integrity_mismatch'):
            bootstrap.prepare(target, self.manifest, connector_modules=self.decode())
        self.assertEqual((target / rel).read_text(), 'unexpected edit')


if __name__ == '__main__':
    unittest.main()
