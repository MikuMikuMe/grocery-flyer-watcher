"""One-shot runtime. Collectors supply verified snapshots; schedulers just call run."""
import hashlib
import json
import os
import smtplib
import ssl
import subprocess
import tempfile
import tomllib
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from email.message import EmailMessage
from pathlib import Path
from zoneinfo import ZoneInfo
from urllib.parse import urlsplit
from .core import fingerprint, public_text, public_url, render_report, validate_snapshot


def load_config(path):
    path = Path(path).resolve()
    with path.open("rb") as stream:
        c = tomllib.load(stream)
    allowed = {"market", "retailer", "timezone", "sources", "collector", "state_file", "output_dir", "publication", "notification"}
    if set(c) - allowed:
        raise ValueError("Unknown config fields; credentials belong in environment variables")
    for field in ("market", "retailer", "timezone"):
        public_text(c[field])
    ZoneInfo(c["timezone"])
    if not isinstance(c["sources"], list) or len(c["sources"]) < 2:
        raise ValueError("Configure at least two source URLs")
    for source in c["sources"]:
        public_url(source)
    if len({urlsplit(s).hostname for s in c["sources"]}) < 2:
        raise ValueError("Configure multiple source hosts")
    command = c.get("collector", [])
    if not isinstance(command, list) or any(not isinstance(s, str) or not s for s in command):
        raise ValueError("collector must be an argv array, not a shell string")
    for field, default in (("state_file", "../private/state.json"), ("output_dir", "../public")):
        c[field] = (path.parent / c.get(field, default)).resolve()
    if c["state_file"].is_relative_to(c["output_dir"]):
        raise ValueError("Private state must be outside the public output directory")
    c.setdefault("publication", "local")
    c.setdefault("notification", "none")
    if c["publication"] not in {"local", "git"} or c["notification"] not in {"none", "smtp"}:
        raise ValueError("Unsupported publication or notification adapter")
    return c


def collect(c, input_path=None):
    if input_path:
        raw = Path(input_path).read_text(encoding="utf-8")
    else:
        if not c.get("collector"):
            raise ValueError("No live collector configured; use --input for verified JSON")
        request = {k: c[k] for k in ("market", "retailer", "timezone", "sources")}
        request["protocol_version"] = 1
        env = {k: v for k, v in os.environ.items()
               if not k.startswith(("FLYER_SMTP_", "FLYER_MAIL_")) and k not in {"GH_TOKEN", "GITHUB_TOKEN"}}
        result = subprocess.run(c["collector"], input=json.dumps(request), text=True,
                                capture_output=True, timeout=300, check=False, env=env)
        if result.returncode:
            raise RuntimeError("Collector failed; its private output was not logged")
        raw = result.stdout
    if len(raw.encode()) > 4_000_000:
        raise ValueError("Collector output too large")
    data = json.loads(raw)
    if isinstance(data, dict) and set(data) == {"flyer", "offers"}:
        return [validate_snapshot(data)]
    if not isinstance(data, dict) or set(data) != {"status", "snapshots"} or data["status"] != "ok":
        raise ValueError("Collector could not verify current sources")
    if not isinstance(data["snapshots"], list) or len(data["snapshots"]) > 20:
        raise ValueError("Expected a bounded snapshot list")
    return [validate_snapshot(s) for s in data["snapshots"]]


def check_scope(c, snapshot, today=None):
    validate_snapshot(snapshot)
    f = snapshot["flyer"]
    for key in ("retailer", "market"):
        if f[key].strip().casefold() != c[key].strip().casefold():
            raise ValueError("Collector returned a different market or retailer")
    today = today or datetime.now(ZoneInfo(c["timezone"])).date()
    if date.fromisoformat(f["ends_on"]) < today:
        raise ValueError("Expired flyer; refusing to send it as a new offer")
    if date.fromisoformat(f["starts_on"]) > today + timedelta(days=14):
        raise ValueError("Preview is outside the 14-day horizon")
    allowed = {urlsplit(s).hostname for s in c["sources"]}
    sources = [f["url"], *f.get("sources", [])]
    if any(urlsplit(s).hostname not in allowed for s in sources):
        raise ValueError("Unconfigured source host")
    if date.fromisoformat(f["starts_on"]) > today and len({urlsplit(s).hostname for s in sources}) < 2:
        raise ValueError("Preview needs corroborating sources")


def event_key(snapshot):
    # A provider-specific edition ID must not cause a mirror-site duplicate alert.
    canonical = {"flyer": dict(snapshot["flyer"], id="canonical-edition"), "offers": snapshot["offers"]}
    return fingerprint(canonical)


def atomic_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(dir=path.parent, prefix=".flyer-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(data, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


@contextmanager
def state_lock(path):
    """Single-host lock. Remove a stale directory only after checking no run is active."""
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    lock = path.with_name(path.name + ".lock")
    try:
        lock.mkdir(mode=0o700)
    except FileExistsError as exc:
        raise RuntimeError("Another run or stale lock exists") from exc
    try:
        yield
    finally:
        lock.rmdir()


def read_state(path):
    if not path.exists():
        return {"version": 1, "events": {}}
    state = json.loads(path.read_text(encoding="utf-8"))
    if state.get("version") != 1 or not isinstance(state.get("events"), dict):
        raise ValueError("Unsupported private state")
    return state


def publish(c, snapshot, key):
    root = c["output_dir"].resolve()
    scope = hashlib.sha256((snapshot["flyer"]["retailer"] + "|" + snapshot["flyer"]["market"]).encode()).hexdigest()[:12]
    stem = root / scope / (snapshot["flyer"]["starts_on"] + "-" + key)
    paths = [stem.with_suffix(".json"), stem.with_suffix(".md")]
    if any(not p.resolve().is_relative_to(root) for p in paths):
        raise ValueError("Unsafe archive path")
    repo = None
    if c["publication"] == "git":
        # Keep private state outside the entire checkout, not merely public/.
        repo = root.parent
        actual = subprocess.run(["git", "-C", str(repo), "rev-parse", "--show-toplevel"],
                                capture_output=True, text=True, check=True).stdout.strip()
        if Path(actual).resolve() != repo or c["state_file"].is_relative_to(repo):
            raise ValueError("Git output must be <repo>/public and state must be outside repo")
        if subprocess.run(["git", "-C", str(repo), "diff", "--cached", "--quiet"], capture_output=True).returncode:
            raise RuntimeError("Refusing to commit an existing staged change")
    atomic_json(paths[0], snapshot)
    paths[1].write_text(render_report(snapshot), encoding="utf-8")
    if repo:
        def git(*args):
            return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=True)
        git("add", "--", *[str(p.relative_to(repo)) for p in paths])
        diff = git("diff", "--cached", "--name-only").stdout.strip()
        if diff:
            git("-c", "user.name=Grocery Flyer Watch", "-c", "user.email=automation@users.noreply.github.com",
                "commit", "-m", f"Archive verified flyer {key[:16]}")
        git("push")  # Also retries a prior commit whose push failed.


def send_smtp(snapshot, key):
    """Secrets are read only here; never included in archive, logs or collector input."""
    e = os.environ
    host = e["FLYER_SMTP_HOST"]
    mode = e.get("FLYER_SMTP_MODE", "ssl")
    if mode not in {"ssl", "starttls"}:
        raise ValueError("SMTP must use TLS")
    port = int(e.get("FLYER_SMTP_PORT", "465" if mode == "ssl" else "587"))
    message = EmailMessage()
    message["From"] = e["FLYER_MAIL_FROM"]
    message["To"] = e["FLYER_MAIL_TO"]
    f = snapshot["flyer"]
    message["Subject"] = f"Grocery Flyer Watch | {f['retailer']} | {f['starts_on']} | {key[:16]}"
    message["Message-ID"] = "<flyer-" + key + "@grocery-flyer-watch.invalid>"
    message.set_content(render_report(snapshot))
    context = ssl.create_default_context()
    client = smtplib.SMTP_SSL(host, port, timeout=30, context=context) if mode == "ssl" else smtplib.SMTP(host, port, timeout=30)
    with client as smtp:
        if mode == "starttls":
            smtp.ehlo()
            smtp.starttls(context=context)
            smtp.ehlo()
        if e.get("FLYER_SMTP_USER"):
            smtp.login(e["FLYER_SMTP_USER"], e["FLYER_SMTP_PASSWORD"])
        if smtp.send_message(message):
            raise RuntimeError("Some recipients were refused")


def run(c, input_path=None, dry_run=False, publisher=publish, notifier=send_smtp):
    failure = None
    try:
        snapshots = collect(c, input_path)
        for snapshot in snapshots:
            check_scope(c, snapshot)
    except Exception as exc:
        snapshots, failure = [], exc
    if dry_run and failure:
        raise failure
    if dry_run:
        return [render_report(s) for s in snapshots]  # No state, publication or mail.
    with state_lock(c["state_file"]):
        state = read_state(c["state_file"])
        for snapshot in snapshots:
            key = event_key(snapshot)
            state["events"].setdefault(key, {"snapshot": snapshot, "published": False, "notified": False})
        atomic_json(c["state_file"], state)  # Persist pending work before external side effects.
        reports = []
        for key, event in state["events"].items():
            if event["published"] and (event["notified"] or c["notification"] == "none"):
                continue
            snapshot = event["snapshot"]
            # A later profile change must not deliver the old city's pending work.
            f = snapshot["flyer"]
            if any(f[k].casefold() != c[k].casefold() for k in ("market", "retailer")) or date.fromisoformat(f["ends_on"]) < datetime.now(ZoneInfo(c["timezone"])).date():
                continue
            check_scope(c, snapshot)
            if not event["published"]:
                publisher(c, snapshot, key)
                event["published"] = True
                atomic_json(c["state_file"], state)
            if c["notification"] == "smtp" and not event["notified"]:
                notifier(snapshot, key)
                event["notified"] = True
                atomic_json(c["state_file"], state)
            reports.append(render_report(snapshot))
        if failure:
            raise failure
        return reports


def seed(c, snapshot):
    """Explicit migration of an already published/delivered baseline; never send mail."""
    validate_snapshot(snapshot)
    if any(snapshot["flyer"][k].casefold() != c[k].casefold() for k in ("market", "retailer")):
        raise ValueError("Seed does not match profile")
    with state_lock(c["state_file"]):
        state = read_state(c["state_file"])
        state["events"][event_key(snapshot)] = {"snapshot": snapshot, "published": True, "notified": True}
        atomic_json(c["state_file"], state)
