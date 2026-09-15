"""Refuse URLs that would make the engine fetch from a non-public network.

The audit crawler fetches whatever URL it is given, so without this check a
caller could point it at the engine's own host, the LAN, or a cloud metadata
endpoint (SSRF). Every address the hostname resolves to must be globally
routable.

Residual risk: the hostname is resolved here and again by the HTTP client, so a
DNS record that changes between the two lookups (DNS rebinding) is not covered.
"""
from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlsplit


class UnsafeURLError(ValueError):
    """The URL is not http(s), has no host, or resolves to a non-public address."""


def ensure_public_url(url: str) -> None:
    try:
        parts = urlsplit(url)
    except ValueError as exc:  # e.g. an unbalanced IPv6 bracket
        raise UnsafeURLError("The URL is malformed.") from exc
    if parts.scheme not in ("http", "https"):
        raise UnsafeURLError("Only http and https URLs can be audited.")
    host = parts.hostname
    if not host:
        raise UnsafeURLError("The URL has no host.")
    try:
        port = parts.port
    except ValueError as exc:
        raise UnsafeURLError("The URL has an invalid port.") from exc
    try:
        infos = socket.getaddrinfo(host, port or None, proto=socket.IPPROTO_TCP)
    except (socket.gaierror, UnicodeError) as exc:
        raise UnsafeURLError(f"Could not resolve {host}.") from exc
    for info in infos:
        host_ip = str(info[4][0]).split("%", 1)[0]  # drop an IPv6 zone id
        address = ipaddress.ip_address(host_ip)
        if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped:
            address = address.ipv4_mapped
        if not address.is_global or address.is_multicast:
            raise UnsafeURLError(
                f"{host} resolves to a private, loopback or reserved address; "
                "only public sites can be audited."
            )
