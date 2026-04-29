import os
import socket
import ipaddress
from urllib.parse import urlparse
from typing import Optional

def is_safe_url(url: str, allowed_schemes: Optional[list] = None) -> bool:
    """
    Validates if a URL is safe to request.
    Checks for:
    1. Valid URL scheme (default: http, https)
    2. Resolves to a public, non-internal IP address.
    """
    if allowed_schemes is None:
        allowed_schemes = ["http", "https"]

    try:
        parsed = urlparse(url)
        if parsed.scheme not in allowed_schemes:
            return False

        hostname = parsed.hostname
        if not hostname:
            return False

        # Resolve hostname to IP
        ip_addr_str = socket.gethostbyname(hostname)
        ip_addr = ipaddress.ip_address(ip_addr_str)

        # Check if IP is private/local
        if (ip_addr.is_private or 
            ip_addr.is_loopback or 
            ip_addr.is_link_local or 
            ip_addr.is_multicast or 
            ip_addr.is_reserved or 
            ip_addr.is_unspecified):
            return False

        return True
    except (ValueError, socket.gaierror):
        return False

def is_safe_path(path: str, base_dir: str) -> bool:
    """
    Validates if a path is safe to access (no path traversal).
    Ensures the resolved absolute path is within the base directory.
    """
    try:
        # Standardize paths
        base_dir = os.path.abspath(base_dir)
        requested_path = os.path.abspath(os.path.join(base_dir, path))

        # Check if requested_path starts with base_dir correctly
        # Use commonpath to avoid issues with similar prefixes (e.g., /app vs /app2)
        return os.path.commonpath([base_dir]) == os.path.commonpath([base_dir, requested_path])
    except (ValueError, Exception):
        return False
