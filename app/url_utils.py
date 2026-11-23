from urllib.parse import urlsplit, urlunsplit


def build_short_url(public_base, alias):
    """Join a configured public base URL and alias without duplicating its host."""
    parts = urlsplit(public_base.strip())
    hostname = (parts.hostname or "").lower()
    # Collapse empty path segments (extra slashes), and remove a hostname
    # accidentally pasted into the path, e.g. https://host/host/.
    path_parts = [part for part in parts.path.split("/") if part]
    while path_parts and path_parts[0].lower() == hostname:
        path_parts.pop(0)
    path = "/" + "/".join([*path_parts, alias])
    return urlunsplit((parts.scheme, parts.netloc, path, "", ""))
