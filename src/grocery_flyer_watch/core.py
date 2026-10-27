"""Portable, CAD-denominated public flyer data; no network or account dependency."""
import hashlib
import json
import re
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import urlsplit

EMAIL = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
SECRET = re.compile(r"(github_pat_|ghp_[A-Za-z0-9]+|/api/webhooks/|(?:api[_-]?key|secret|password|bearer|token)\s*[:=]\s*\S+)", re.I)
FLYER_KEYS = {"id", "retailer", "market", "starts_on", "ends_on", "url"}
OFFER_REQUIRED = {"name", "price_cad", "pricing", "priority", "why"}
OFFER_ALLOWED = OFFER_REQUIRED | {"size_g", "count", "restrictions"}


def _positive(value):
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("Invalid numeric value") from exc
    if not number.is_finite() or number <= 0:
        raise ValueError("Number must be positive and finite")
    return number


def public_text(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Missing public text")
    if any(ord(c) < 32 for c in value) or EMAIL.search(value) or SECRET.search(value):
        raise ValueError("Potential private information or control character")
    return value.strip()


def public_url(value):
    public_text(value)
    u = urlsplit(value)
    if (u.scheme != "https" or not u.hostname or "." not in u.hostname
            or u.username or u.password or u.query or u.fragment or u.port not in (None, 443)):
        raise ValueError("Expected a clean public HTTPS URL without queries")
    return value


def validate_snapshot(snapshot):
    if not isinstance(snapshot, dict) or set(snapshot) != {"flyer", "offers"}:
        raise ValueError("Expected only flyer and offers")
    f = snapshot["flyer"]
    if not isinstance(f, dict) or not FLYER_KEYS <= set(f) or set(f) - FLYER_KEYS - {"sources"}:
        raise ValueError("Unexpected flyer fields")
    for key in FLYER_KEYS:
        public_text(f[key])
    public_url(f["url"])
    sources = f.get("sources", [])
    if not isinstance(sources, list) or len(sources) > 20:
        raise ValueError("Invalid sources")
    for source in sources:
        public_url(source)
    dates = []
    for field in ("starts_on", "ends_on"):
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", f[field]):
            raise ValueError("Expected YYYY-MM-DD")
        dates.append(date.fromisoformat(f[field]))
    if dates[0] > dates[1]:
        raise ValueError("Reversed flyer dates")
    offers = snapshot["offers"]
    if not isinstance(offers, list) or not offers or len(offers) > 1000:
        raise ValueError("Expected 1-1000 offers")
    seen = set()
    for o in offers:
        if not isinstance(o, dict) or not OFFER_REQUIRED <= set(o) or set(o) - OFFER_ALLOWED:
            raise ValueError("Unexpected offer fields")
        name = public_text(o["name"]).casefold()
        public_text(o["why"])
        if "restrictions" in o:
            public_text(o["restrictions"])
        if name in seen:
            raise ValueError("Duplicate offer")
        seen.add(name)
        _positive(o["price_cad"])
        if o["pricing"] not in {"per_lb", "per_kg", "each", "package"}:
            raise ValueError("Unknown pricing")
        if type(o["priority"]) is not int or not 1 <= o["priority"] <= 5:
            raise ValueError("Priority must be 1-5")
        if "size_g" in o:
            _positive(o["size_g"])
        if "count" in o and (type(o["count"]) is not int or o["count"] <= 0):
            raise ValueError("Invalid count")
        if ("size_g" in o or "count" in o) and o["pricing"] != "package":
            raise ValueError("Package details require package pricing")
        if "size_g" in o and "count" in o:
            raise ValueError("Ambiguous package details")
    return snapshot


def read_snapshot(path):
    return validate_snapshot(json.loads(Path(path).read_text(encoding="utf-8")))


def fingerprint(snapshot):
    """Scope by retailer and market; ignore editorial text and source URL order."""
    validate_snapshot(snapshot)
    f = snapshot["flyer"]
    payload = {
        "flyer": {k: f[k].strip().casefold() for k in ("id", "retailer", "market", "starts_on", "ends_on")},
        "offers": sorted([
            {"name": o["name"].strip().casefold(), "price": str(_positive(o["price_cad"]).normalize()),
             "pricing": o["pricing"], "size_g": str(_positive(o["size_g"]).normalize()) if "size_g" in o else "",
             "count": o.get("count", ""), "restrictions": o.get("restrictions", "")}
            for o in snapshot["offers"]
        ], key=lambda o: o["name"]),
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def changed(previous, current):
    return fingerprint(previous) != fingerprint(current)


def unit_price(o):
    p = _positive(o["price_cad"])
    if o["pricing"] == "per_lb":
        return f"${p * Decimal('2.2046226218'):.2f}/kg (${p:.2f}/lb)"
    if o["pricing"] == "per_kg":
        return f"${p:.2f}/kg"
    if o["pricing"] == "each":
        return f"${p:.2f} each"
    if "size_g" in o:
        return f"${p * 1000 / _positive(o['size_g']):.2f}/kg"
    if "count" in o:
        return f"${p / o['count']:.2f} each"
    return f"${p:.2f} per package"


def render_report(snapshot):
    validate_snapshot(snapshot)
    f = snapshot["flyer"]
    header = (f"# {f['retailer']} — {f['market']}\n\n"
              f"Valid {f['starts_on']} to {f['ends_on']}. Future offers start on the stated date.\n\n"
              f"Source: {f['url']}\n\nFlyer ID: {f['id']}. Prices in CAD.\n\n## Best-value picks\n\n")
    rows = [
        f"- **{o['name']}** — ${_positive(o['price_cad']):.2f} ({unit_price(o)}). "
        f"{o['why']}" + (f" Restrictions: {o['restrictions']}" if o.get("restrictions") else "")
        for o in sorted(snapshot["offers"], key=lambda o: (-o["priority"], o["name"].casefold()))
    ]
    sources = "\n".join(f"- {s}" for s in f.get("sources", []))
    return header + "\n".join(rows) + ("\n\n## Other sources\n\n" + sources if sources else "") + (
        "\n\nEditorial shortlist, not a complete flyer. Check availability, exact sizes/cuts, "
        "limitations and nearby alternatives.\n")
