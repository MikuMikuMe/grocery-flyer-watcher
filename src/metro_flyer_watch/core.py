"""Private-data-safe flyer snapshot checks and value comparisons."""
import hashlib
import json
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import urlsplit

EMAIL = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
SECRET = re.compile(r"(github_pat_|ghp_[A-Za-z0-9]+|/api/webhooks/|(?:api[_-]?key|secret|password|bearer|token)\s*[:=]\s*\S+)", re.I)
FLYER_KEYS = {"id", "retailer", "market", "starts_on", "ends_on", "url"}
OFFER_REQUIRED = {"name", "price_cad", "pricing", "priority", "why"}
OFFER_ALLOWED = OFFER_REQUIRED | {"size_g", "count"}


def _positive(value):
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("Invalid numeric value") from exc
    if not number.is_finite() or number <= 0:
        raise ValueError("Number must be positive and finite")
    return number


def _public(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Missing public text")
    if EMAIL.search(value) or SECRET.search(value):
        raise ValueError("Potential private information")
    return value.strip()


def validate_snapshot(snapshot):
    """Fail closed on unknown fields, secrets, emails and tracking URLs."""
    if not isinstance(snapshot, dict) or set(snapshot) != {"flyer", "offers"}:
        raise ValueError("Expected only flyer and offers")
    flyer = snapshot["flyer"]
    if not isinstance(flyer, dict) or set(flyer) != FLYER_KEYS:
        raise ValueError("Unexpected flyer fields")
    for value in flyer.values():
        _public(value)
    if flyer["retailer"].casefold() != "metro" or "kingston" not in flyer["market"].casefold():
        raise ValueError("Expected a Metro Kingston flyer")
    url = urlsplit(flyer["url"])
    if (url.scheme != "https" or url.hostname != "flipp.com"
            or url.username or url.password or url.query or url.fragment or "/flyer/" not in url.path):
        raise ValueError("Expected clean public Flipp link")
    for field in ("starts_on", "ends_on"):
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", flyer[field]):
            raise ValueError("Expected YYYY-MM-DD")
    offers = snapshot["offers"]
    if not isinstance(offers, list) or not offers:
        raise ValueError("Expected offers")
    seen = set()
    for o in offers:
        if not isinstance(o, dict) or not OFFER_REQUIRED <= set(o) or set(o) - OFFER_ALLOWED:
            raise ValueError("Unexpected offer fields")
        name = _public(o["name"]).casefold()
        _public(o["why"])
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
    """Flyer and offers change; editorial commentary/order do not."""
    validate_snapshot(snapshot)
    f = snapshot["flyer"]
    payload = {
        "flyer": {k: f[k] for k in ("id", "starts_on", "ends_on")},
        "offers": sorted([
            {"name": o["name"].casefold(), "price": str(_positive(o["price_cad"]).normalize()),
             "pricing": o["pricing"], "size_g": str(o.get("size_g", "")), "count": o.get("count", "")}
            for o in snapshot["offers"]
        ], key=lambda o: (o["name"], o["price"])),
    }
    data = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


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
    header = (f"# Metro Kingston flyer — {f['starts_on']} to {f['ends_on']}\n\n"
              f"Source: {f['url']}\n\nFlyer ID: {f['id']}. Prices in CAD.\n\n"
              "## Best-value picks\n\n")
    rows = [
        f"- **{'★' * o['priority']} {o['name']}** — ${_positive(o['price_cad']):.2f} "
        f"({unit_price(o)}). {o['why']}"
        for o in sorted(snapshot["offers"], key=lambda o: (-o["priority"], o["name"].casefold()))
    ]
    return header + "\n".join(rows) + (
        "\n\nEditorial shortlist, not a complete flyer. Check availability, "
        "exact sizes/cuts, limitations and nearby alternatives.\n")
