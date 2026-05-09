"""Source identification: extract domain & publisher from a URL."""

from __future__ import annotations

from urllib.parse import urlparse


def _normalize(host: str) -> str:
    host = host.lower().strip()
    if host.startswith("www."):
        host = host[4:]
    if ":" in host:
        host = host.split(":", 1)[0]
    return host


def extract_domain(url: str) -> str:
    """Return the lowercased registrable host (no scheme, no www, no port)."""
    if not url or not url.strip():
        raise ValueError("URL is empty")

    candidate = url.strip()
    if "://" not in candidate:
        candidate = "https://" + candidate

    parsed = urlparse(candidate)
    host = parsed.netloc or parsed.path
    if not host:
        raise ValueError(f"Could not extract a host from URL: {url!r}")

    return _normalize(host)


def domain_variants(domain: str) -> list[str]:
    """Return the domain plus its parent (drops one leftmost subdomain).

    Lets us match e.g. ``news.adaderana.lk`` against ``adaderana.lk`` in the KB.
    """
    variants = [domain]
    parts = domain.split(".")
    if len(parts) > 2:
        variants.append(".".join(parts[1:]))
    return variants


def is_sri_lankan_domain(domain: str) -> bool:
    """Heuristic: any ``.lk`` domain is considered Sri Lankan."""
    return domain.endswith(".lk")


def derive_publisher(domain: str) -> str:
    """Best-effort publisher name derived from the domain stem."""
    stem = domain.split(".")[0]
    return stem.replace("-", " ").replace("_", " ").title()
