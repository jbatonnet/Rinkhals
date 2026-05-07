#!/usr/bin/env python3
"""Minimal mDNS responder for advertising a custom hostname.local on a network.

Usage: python3 mdns_responder.py <hostname>

Listens on UDP port 5353 for mDNS queries and responds to A-record lookups
for <hostname>.local with the machine's local IP address.

Dependencies: Python 3 standard library only (socket, struct, signal, logging).
"""

import logging
import re
import signal
import socket
import struct
import sys
import time
from types import FrameType

MDNS_ADDR: str = "224.0.0.251"
MDNS_PORT: int = 5353
DNS_TYPE_A: int = 1
DNS_CLASS_IN: int = 1
DNS_CLASS_IN_FLUSH: int = 0x8001  # IN class with cache-flush bit
TTL: int = 120
REANNOUNCE_INTERVAL: int = 90  # Re-announce before TTL expires (RFC 6762)
RETRY_INTERVAL: int = 5  # Seconds between socket setup retries
MAX_RETRIES: int = 60  # Give up after 5 minutes (60 * 5s)
VALID_HOSTNAME_RE: re.Pattern[str] = re.compile(r"^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log: logging.Logger = logging.getLogger("mdns")


def get_local_ip() -> str:
    """Get the local IP address by connecting a UDP socket to
    a remote address."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("224.0.0.251", 5353))
        ip: str = s.getsockname()[0]
        s.close()
        return ip
    except OSError:
        return "127.0.0.1"


def validate_hostname(hostname: str) -> None:
    """Validate that a hostname is a valid DNS label.

    Raises ValueError if the hostname contains invalid characters
    or doesn't conform to DNS naming rules.
    """
    if not VALID_HOSTNAME_RE.match(hostname):
        raise ValueError(
            f"Invalid hostname '{hostname}': must be 1-63 characters, "
            "lowercase alphanumeric and hyphens, cannot start/end with hyphen"
        )


def encode_dns_name(name: str) -> bytes:
    """Encode a domain name into DNS wire format (label encoding).

    Example: "myhost.local" -> b'\\x06myhost\\x05local\\x00'
    """
    parts: list[bytes] = name.encode("ascii").split(b".")
    for part in parts:
        if len(part) > 63:
            raise ValueError(f"DNS label too long: {part!r} ({len(part)} > 63)")
    result = b""
    for part in parts:
        result += struct.pack("B", len(part)) + part
    result += b"\x00"
    return result


def parse_dns_name(data: bytes, offset: int) -> tuple[str, int]:
    """Parse a DNS name from wire format, handling label encoding and pointers.

    Returns (name_string, new_offset).
    """
    labels: list[str] = []
    original_offset: int | None = None

    while offset < len(data):
        length: int = data[offset]

        if length == 0:
            offset += 1
            break

        # Pointer (compression): top 2 bits are 11
        if (length & 0xC0) == 0xC0:
            if original_offset is None:
                original_offset = offset + 2
            pointer: int = struct.unpack("!H", data[offset : offset + 2])[0] & 0x3FFF
            offset = pointer
            continue

        offset += 1
        if offset + length > len(data):
            break
        labels.append(data[offset : offset + length].decode("ascii", errors="replace"))
        offset += length

    name: str = ".".join(labels)
    return name, original_offset if original_offset is not None else offset


def build_response(query_id: int, name_encoded: bytes, ip_addr: str) -> bytes:
    """Build a complete mDNS response packet for an A record.

    Args:
        query_id: Transaction ID from the query.
        name_encoded: DNS wire-format encoded name.
        ip_addr: IP address string (e.g., "192.168.1.10").

    Returns:
        The complete DNS response packet.
    """
    # Header: ID, flags=0x8400 (response, authoritative), 0 questions, 1 answer
    header: bytes = struct.pack(
        "!HHHHHH",
        query_id,
        0x8400,  # QR=1, AA=1
        0,  # QDCOUNT
        1,  # ANCOUNT
        0,  # NSCOUNT
        0,  # ARCOUNT
    )

    # Answer section:
    # name, type A, class IN with cache-flush, TTL, RDLENGTH=4, RDATA=IP
    ip_bytes: bytes = socket.inet_aton(ip_addr)
    answer: bytes = name_encoded
    answer += struct.pack("!HHI", DNS_TYPE_A, DNS_CLASS_IN_FLUSH, TTL)
    answer += struct.pack("!H", 4)
    answer += ip_bytes

    return header + answer


def handle_query(
    data: bytes,
    target_name: str,
    target_encoded: bytes,
    sock: socket.socket,
) -> None:
    """Parse an incoming DNS packet and respond if it queries our hostname.

    Args:
        data: Raw packet bytes.
        target_name: The hostname.local we respond to (lowercase).
        target_encoded: Pre-encoded DNS wire format of target_name.
        sock: The UDP socket to send responses on.
    """
    if len(data) < 12:
        return

    query_id: int
    flags: int
    qdcount: int
    query_id, flags, qdcount = struct.unpack("!HHH", data[:6])

    # Only process queries (QR bit = 0)
    if flags & 0x8000:
        return

    offset: int = 12  # Skip header

    for _ in range(qdcount):
        if offset >= len(data):
            break

        name: str
        name, offset = parse_dns_name(data, offset)
        if offset + 4 > len(data):
            break

        qtype: int
        qclass: int
        qtype, qclass = struct.unpack("!HH", data[offset : offset + 4])
        offset += 4

        # Check if this is an A record query for our hostname
        # qclass may have the unicast-response bit (0x8000) set
        if (
            name.lower() == target_name
            and qtype == DNS_TYPE_A
            and (qclass & 0x7FFF) == DNS_CLASS_IN
        ):
            ip: str = get_local_ip()
            if ip == "127.0.0.1":
                continue

            response: bytes = build_response(query_id, target_encoded, ip)
            sock.sendto(response, (MDNS_ADDR, MDNS_PORT))
            log.info("Responded to query for %s -> %s", target_name, ip)


def create_socket(mreq: bytes) -> socket.socket:
    """Create and configure the mDNS UDP socket.

    Raises OSError if the network interface is not ready.
    """
    sock: socket.socket = socket.socket(
        socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP
    )
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    except AttributeError:
        pass  # SO_REUSEPORT not available on older kernels
    sock.bind(("", MDNS_PORT))
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 255)
    sock.settimeout(1.0)
    return sock


def close_socket(sock: socket.socket, mreq: bytes) -> None:
    """Leave multicast group and close the socket."""
    try:
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_DROP_MEMBERSHIP, mreq)
    except OSError:
        pass
    sock.close()


def announce(sock: socket.socket, target_name: str, target_encoded: bytes) -> None:
    """Send an unsolicited mDNS announcement (gratuitous response).

    This helps other devices on the network discover the hostname immediately.
    """
    ip: str = get_local_ip()
    if ip == "127.0.0.1":
        return

    response: bytes = build_response(0, target_encoded, ip)
    sock.sendto(response, (MDNS_ADDR, MDNS_PORT))
    log.info("Announced %s -> %s", target_name, ip)


def main() -> None:
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <hostname>", file=sys.stderr)
        sys.exit(1)

    hostname: str = sys.argv[1]
    validate_hostname(hostname.lower())
    target_name: str = f"{hostname}.local".lower()
    target_encoded: bytes = encode_dns_name(target_name)

    log.info("Starting mDNS responder for %s", target_name)

    running: bool = True

    def shutdown(_signum: int, _frame: FrameType | None) -> None:
        nonlocal running
        log.info("Shutting down mDNS responder")
        running = False

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    sock: socket.socket | None = None
    mreq: bytes = struct.pack(
        "4s4s", socket.inet_aton(MDNS_ADDR), socket.inet_aton("0.0.0.0")
    )

    retries: int = 0
    last_announce: float = 0.0
    while running:
        # Set up socket if needed (initial start or after error)
        if sock is None:
            try:
                sock = create_socket(mreq)
                retries = 0
                log.info("Socket ready, listening on port %d", MDNS_PORT)
                announce(sock, target_name, target_encoded)
                last_announce = time.monotonic()
            except OSError as e:
                retries += 1
                if retries > MAX_RETRIES:
                    log.error("Giving up after %d retries: %s", retries, e)
                    break
                log.warning(
                    "Socket setup failed (retry %d/%d): %s",
                    retries,
                    MAX_RETRIES,
                    e,
                )
                time.sleep(RETRY_INTERVAL)
                continue

        # Main receive loop
        try:
            data: bytes
            data, _ = sock.recvfrom(1500)
            handle_query(data, target_name, target_encoded, sock)
        except socket.timeout:
            pass
        except OSError:
            if running:
                log.exception("Socket error, will retry")
                close_socket(sock, mreq)
                sock = None
            continue

        # Periodically re-announce before TTL expires (RFC 6762)
        now: float = time.monotonic()
        if now - last_announce >= REANNOUNCE_INTERVAL:
            announce(sock, target_name, target_encoded)
            last_announce = now

    if sock is not None:
        close_socket(sock, mreq)
    log.info("mDNS responder stopped")


if __name__ == "__main__":
    main()
