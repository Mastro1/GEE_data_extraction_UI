"""
Google Maps URL parser — extracts latitude/longitude from Google Maps links.

Supports:
- Full URLs:  https://www.google.com/maps/place/Name/...!3dlat!4dlon/...
- Country-specific domains: google.fr, google.co.uk, etc.
- Short URLs: https://maps.app.goo.gl/xxxxx  (resolved via HTTP redirect)
- Legacy short: https://goo.gl/maps/xxxxx

NOTE: The @lat,lon pattern in Google Maps URLs represents the map viewport
centre, NOT the actual place coordinates.  The !3d/!4d pattern contains the
real pin location and is therefore tried first.
"""
import re
import logging
from urllib.parse import urlparse, parse_qs

import requests

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Regex patterns for extracting coordinates from full Google Maps URLs
# ---------------------------------------------------------------------------

# Pattern 1: !3d lat !4d lon  — actual place coordinates (most reliable)
# e.g. !3d34.0034946!4d-6.8456519
# NOTE: The @lat,lon pattern is deliberately deprioritised because those
#       coordinates represent the map viewport centre, NOT the place itself.
_PATTERN_3D4D = re.compile(r'!3d(-?\d+\.\d+)!4d(-?\d+\.\d+)')

# Pattern 2: @lat,lon  — viewport centre, NOT the pin location.
# Used only as a fallback when !3d/!4d is absent (e.g. dropped-pin URLs).
# e.g. /@34.0041511,-6.8456333,480m/
_PATTERN_AT = re.compile(r'@(-?\d+\.\d+),(-?\d+\.\d+)')

# Pattern 3: ?center=lat,lon (rare — old-style embed/search URLs)
_PATTERN_CENTER = re.compile(r'[?&]center=(-?\d+\.\d+),(-?\d+\.\d+)')

# Domains / patterns that indicate a Google Maps URL.
# Supports country-specific Google domains (google.fr, google.co.uk, etc.)
_MAPS_DOMAINS = ('maps.app.goo.gl', 'goo.gl/maps')
_MAPS_DOMAIN_RE = re.compile(r'google\.[a-z.]+/maps', re.IGNORECASE)


def is_google_maps_url(url: str) -> bool:
    """Quick check whether a URL looks like a Google Maps link."""
    lower = url.lower().strip()
    if any(domain in lower for domain in _MAPS_DOMAINS):
        return True
    return bool(_MAPS_DOMAIN_RE.search(lower))


def _resolve_short_url(url: str, timeout: int = 10) -> str | None:
    """Follow HTTP redirects for a short link to obtain the full URL.

    Returns the final URL after all redirects, or None on failure.
    """
    try:
        resp = requests.get(url, allow_redirects=True, timeout=timeout,
                            headers={'User-Agent': 'Mozilla/5.0'})
        return resp.url
    except requests.RequestException as exc:
        logger.debug("Short-URL resolution failed: %s", exc)
        return None


def _extract_coords_from_query(url: str) -> tuple[float, float] | None:
    """Try to extract coordinates from URL query parameters (ll=, q=).

    Returns (lat, lon) or None.
    """
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)

    # ?ll=lat,lon (older-style Google Maps URLs)
    if 'll' in qs:
        try:
            parts = qs['ll'][0].split(',')
            if len(parts) == 2:
                lat, lon = float(parts[0]), float(parts[1])
                if -90 <= lat <= 90 and -180 <= lon <= 180:
                    return (lat, lon)
        except (ValueError, IndexError):
            pass

    # ?q=lat,lon
    if 'q' in qs:
        q_val = qs['q'][0]
        m = re.match(r'(-?\d+\.\d+)[,\s]+(-?\d+\.\d+)', q_val)
        if m:
            try:
                lat, lon = float(m.group(1)), float(m.group(2))
                if -90 <= lat <= 90 and -180 <= lon <= 180:
                    return (lat, lon)
            except ValueError:
                pass

    return None


def _extract_coords_from_url(url: str) -> tuple[float, float] | None:
    """Try all patterns against a full URL string.

    Returns (lat, lon) or None.
    """
    # Try query parameters first (more precise than path-based patterns)
    result = _extract_coords_from_query(url)
    if result:
        return result

    # Try path-based regex patterns in priority order
    # !3d/!4d first — those are the actual place coordinates.
    # @lat,lon is only a fallback (viewport centre, not the pin).
    for pattern in (_PATTERN_3D4D, _PATTERN_AT, _PATTERN_CENTER):
        matches = pattern.findall(url)
        if matches:
            # Take the LAST match — Google Maps URLs can contain multiple
            # !3d/!4d pairs when the user navigated between places, and
            # the final one corresponds to the currently selected location.
            lat_str, lon_str = matches[-1]
            lat, lon = float(lat_str), float(lon_str)
            if -90 <= lat <= 90 and -180 <= lon <= 180:
                return (lat, lon)
    return None


def parse_google_maps_url(url: str) -> tuple[float, float] | None:
    """Extract (latitude, longitude) from a Google Maps URL.

    Handles both full URLs and short share links (maps.app.goo.gl / goo.gl/maps).
    Short links are resolved via an HTTP redirect before parsing.

    Args:
        url: A Google Maps URL string (full or short).

    Returns:
        A (lat, lon) tuple on success, or None if coordinates could not
        be extracted.
    """
    url = url.strip()
    if not url:
        return None

    # Step 1: If it's a short link, resolve to the full URL first
    is_short = 'maps.app.goo.gl' in url or 'goo.gl/maps' in url
    if is_short:
        full_url = _resolve_short_url(url)
        if full_url is None:
            logger.warning("Could not resolve short URL: %s", url)
            return None
        url = full_url

    # Step 2: Extract coordinates from the (possibly resolved) full URL
    return _extract_coords_from_url(url)
