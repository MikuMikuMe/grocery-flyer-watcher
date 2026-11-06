#!/usr/bin/env python3
"""Run the verified production CLI offline; repair missing modules, not user changes.

The operator/connector must obtain the manifest from the actual pinned repository
revision. This helper cannot authenticate an invented manifest or a claimed tool read.
It never installs dependencies, changes a schedule, creates private state or sends mail
unless the caller explicitly asks the existing quality CLI to perform an authorized send.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import tempfile

MODULES = frozenset('src/grocery_flyer_watch/' + name + '.py' for name in (
    '__init__', '__main__', 'core', 'review', 'runner', 'quality_cli',
    'quality_gate', 'reviewed_delivery'))

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

def prepare(root: Path, manifest: dict, cache: Path | None = None) -> dict:
    fail(sys.version_info >= (3, 11), 'python_3_11_required')
    fail(isinstance(manifest, dict) and set(manifest) == {'repository_id','commit','git_blobs'},
         'invalid_runtime_manifest')
    fail(type(manifest['repository_id']) is int and manifest['repository_id'] > 0,
         'invalid_repository_id')
    fail(isinstance(manifest['commit'], str) and re.fullmatch('[0-9a-f]{40}', manifest['commit']),
         'pinned_commit_required')
    fail(isinstance(manifest['git_blobs'], dict) and set(manifest['git_blobs']) == MODULES,
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
            'verified_modules':len(MODULES),'restored_modules':len(repairs),
            'delivery_authorized':False}

def main(argv: list[str] | None = None) -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True, type=Path)
    parser.add_argument('--manifest', required=True, type=Path)
    parser.add_argument('--cache', type=Path, help='Already connector-fetched source files; never credentials')
    parser.add_argument('command', nargs=argparse.REMAINDER)
    a=parser.parse_args(argv)
    try:
        manifest=json.loads(a.manifest.read_text(encoding='utf-8'))
        status=prepare(a.root, manifest, a.cache)
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
