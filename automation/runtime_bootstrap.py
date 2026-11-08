#!/usr/bin/env python3
"""Run the verified production CLI offline; repair missing modules, not user changes.

The operator/connector must obtain the manifest from the actual pinned repository
revision. This helper cannot authenticate an invented manifest or a claimed tool read.
It never installs dependencies, changes a schedule, creates private state or sends mail
unless the caller explicitly asks the existing quality CLI to perform an authorized send.
"""
from __future__ import annotations
import argparse
import base64
import binascii
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys

MODULES = frozenset('src/grocery_flyer_watch/' + name + '.py' for name in (
    '__init__', '__main__', 'core', 'review', 'runner', 'quality_cli',
    'quality_gate', 'reviewed_delivery', 'diagnostics'))
OPTIONAL_MODULES = frozenset({'src/grocery_flyer_watch/repository_delivery.py',
                              'src/grocery_flyer_watch/runtime_preflight.py',
                              'src/grocery_flyer_watch/continuation.py'})

MAX_CONNECTOR_BUNDLE_BYTES = 8 * 1024 * 1024

class RecoveryError(ValueError):
    pass

def fail(condition: bool, code: str) -> None:
    if not condition:
        raise RecoveryError(code)

def blob_id(raw: bytes) -> str:
    return hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()

def safe_file(root: Path, relative: str) -> Path:
    parts = PurePosixPath(relative).parts
    fail(not PurePosixPath(relative).is_absolute() and '..' not in parts, 'unsafe_runtime_path')
    target = root.joinpath(*parts)
    fail(not any(p.is_symlink() for p in [target, *target.parents] if p != root.parent),
         'runtime_symlink_not_allowed')
    fail(target.resolve().is_relative_to(root.resolve()), 'unsafe_runtime_path')
    return target

def decode_connector_bundle(raw: bytes, manifest: dict) -> dict[str, bytes]:
    """Decode GitHub connector base64 source without a populated file cache.

    Pinned Git blob checks in prepare() remain mandatory. This adapter only
    transports source bytes; it does not independently prove connector origin.
    """
    fail(len(raw) <= MAX_CONNECTOR_BUNDLE_BYTES, 'connector_bundle_too_large')
    try:
        bundle = json.loads(raw)
    except (UnicodeDecodeError, ValueError):
        raise RecoveryError('invalid_connector_bundle') from None
    fail(isinstance(bundle, dict) and set(bundle) ==
         {'format', 'repository_id', 'commit', 'modules'}, 'invalid_connector_bundle')
    fail(bundle['format'] == 'pinned-connector-module-cache-v1' and
         type(bundle['repository_id']) is int and
         bundle['repository_id'] == manifest['repository_id'] and
         bundle['commit'] == manifest['commit'], 'connector_bundle_pin_mismatch')
    modules = bundle['modules']
    fail(isinstance(modules, dict) and set(modules) <= set(manifest['git_blobs']),
         'connector_bundle_unexpected_module')
    result = {}
    for rel, encoded in modules.items():
        fail(isinstance(encoded, str), 'invalid_connector_bundle')
        try:
            # GitHub's Contents API may insert line breaks into base64.
            result[rel] = base64.b64decode(
                encoded.replace('\n', '').replace('\r', ''), validate=True)
        except (ValueError, binascii.Error):
            raise RecoveryError('invalid_connector_base64') from None
    return result

def prepare(root: Path, manifest: dict, cache: Path | None = None,
            connector_modules: dict[str, bytes] | None = None) -> dict:
    fail(sys.version_info >= (3, 11), 'python_3_11_required')
    fail(isinstance(manifest, dict) and set(manifest) == {'repository_id','commit','git_blobs'},
         'invalid_runtime_manifest')
    fail(type(manifest['repository_id']) is int and manifest['repository_id'] > 0,
         'invalid_repository_id')
    fail(isinstance(manifest['commit'], str) and re.fullmatch('[0-9a-f]{40}', manifest['commit']),
         'pinned_commit_required')
    fail(isinstance(manifest['git_blobs'], dict) and MODULES <= set(manifest['git_blobs']) <= MODULES | OPTIONAL_MODULES,
         'incomplete_runtime_manifest')
    fail(not root.is_symlink(), 'runtime_symlink_not_allowed')
    root = root.absolute()
    repairs = []
    # Validate every module before writing any missing file; never overwrite a mismatch.
    for rel, expected in manifest['git_blobs'].items():
        fail(isinstance(expected, str) and re.fullmatch('[0-9a-f]{40}', expected), 'invalid_blob_id')
        target = safe_file(root, rel)
        if target.exists():
            fail(target.is_file() and blob_id(target.read_bytes()) == expected,
                 'runtime_integrity_mismatch')
        else:
            if connector_modules is not None:
                fail(rel in connector_modules, 'connector_module_missing')
                raw = connector_modules[rel]
            else:
                fail(cache is not None, 'runtime_module_missing_use_connector_cache')
                source = safe_file(cache.absolute(), rel)
                fail(source.is_file(), 'cache_module_missing')
                raw = source.read_bytes()
            fail(blob_id(raw) == expected, 'cache_integrity_mismatch')
            repairs.append((target, raw))
    for target, raw in repairs:
        target.parent.mkdir(parents=True, exist_ok=True)
        # Exclusive create cannot overwrite an intervening edit from another worker.
        try:
            with target.open('xb') as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
        except FileExistsError:
            fail(blob_id(target.read_bytes()) == blob_id(raw), 'runtime_changed_during_repair')
    return {'status':'runtime_ready','commit':manifest['commit'],
            'verified_modules':len(manifest['git_blobs']),'restored_modules':len(repairs),
            'delivery_authorized':False}

def main(argv: list[str] | None = None) -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True, type=Path)
    parser.add_argument('--manifest', required=True, type=Path)
    cache_group=parser.add_mutually_exclusive_group()
    cache_group.add_argument('--cache', type=Path, help='Already connector-fetched source files; never credentials')
    cache_group.add_argument('--cache-stdin', action='store_true',
                             help='Read pinned connector-fetched base64 GitHub modules as JSON from stdin')
    parser.add_argument('command', nargs=argparse.REMAINDER)
    a=parser.parse_args(argv)
    try:
        manifest=json.loads(a.manifest.read_text(encoding='utf-8'))
        connector_modules=(decode_connector_bundle(
            sys.stdin.buffer.read(MAX_CONNECTOR_BUNDLE_BYTES + 1), manifest)
            if a.cache_stdin else None)
        status=prepare(a.root, manifest, a.cache, connector_modules)
        env=dict(os.environ, PYTHONPATH=str(a.root.resolve()/'src'))
        # This is a harmless executable probe, not an email test or a live flyer check.
        probe=subprocess.run([sys.executable,'-m','grocery_flyer_watch','quality','--help'],
            cwd=a.root, env=env, capture_output=True, timeout=20, check=False)
        fail(probe.returncode == 0, 'runtime_probe_failed')
        args=a.command[1:] if a.command[:1] == ['--'] else a.command
        if not args:
            print(json.dumps(status))
            return 0
        # All pre-send validation remains inside the unchanged production CLI.
        return subprocess.run([sys.executable,'-m','grocery_flyer_watch',*args],
            cwd=a.root, env=env, check=False).returncode
    except Exception as exc:
        code=str(exc) if isinstance(exc,RecoveryError) else type(exc).__name__
        print(json.dumps({'status':'runtime_blocked','code':code,'delivery_authorized':False}),file=sys.stderr)
        return 2

if __name__ == '__main__':
    raise SystemExit(main())
