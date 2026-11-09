#!/usr/bin/env python3
"""Build a merged MikroTik address-list of Iranian IPv4 ranges.

Sources (union, then collapsed):
  1. Ramtiiin/iran-ip   (current list used by the router; includes some hand-picked ranges)
  2. RIPE NCC stat       (official registry: every IPv4 resource registered to country=IR)
  3. extra-ranges.txt    (optional, your own additions, one CIDR per line, # for comments)
  4. Private/CGNAT ranges, so LAN/ISP-local traffic never goes into the tunnel

Usage:  python3 build_iran_list.py [output.rsc]
"""
import hashlib
import ipaddress
import json
import re
import sys
import urllib.request
from pathlib import Path

LIST_NAME = "IRAN"
RAMTIIIN_URL = "https://raw.githubusercontent.com/Ramtiiin/iran-ip/refs/heads/main/ip-list.rsc"
RIPE_URL = "https://stat.ripe.net/data/country-resource-list/data.json?resource=IR&v4_format=prefix"
LOCAL_RANGES = ["10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "100.64.0.0/10"]
EXTRA_FILE = Path(__file__).with_name("extra-ranges.txt")


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "iran-list-builder"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode()


def parse_ramtiiin(text: str):
    nets = []
    for m in re.finditer(r"address=([0-9./]+)", text):
        nets.append(ipaddress.ip_network(m.group(1), strict=False))
    return nets


def parse_ripe(text: str):
    nets = []
    for item in json.loads(text)["data"]["resources"]["ipv4"]:
        if "-" in item:
            a, b = item.split("-")
            nets += ipaddress.summarize_address_range(ipaddress.ip_address(a), ipaddress.ip_address(b))
        else:
            nets.append(ipaddress.ip_network(item, strict=False))
    return nets


def parse_extra(path: Path):
    if not path.exists():
        return []
    nets = []
    for line in path.read_text().splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            nets.append(ipaddress.ip_network(line, strict=False))
    return nets


def main():
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "iran-ip-merged.rsc")
    ram = parse_ramtiiin(fetch(RAMTIIIN_URL))
    ripe = parse_ripe(fetch(RIPE_URL))
    extra = parse_extra(EXTRA_FILE)
    local = [ipaddress.ip_network(n) for n in LOCAL_RANGES]

    if len(ram) < 500 or len(ripe) < 1000:
        sys.exit(f"Source looks broken (ramtiiin={len(ram)}, ripe={len(ripe)}); not writing output.")

    def sane(n):
        # Guard against a bad/hostile upstream entry (e.g. 0.0.0.0/1) that would
        # silently route most traffic outside the tunnel.
        return n.version == 4 and n.prefixlen >= 8 and not (
            n.is_multicast or n.is_reserved or n.is_loopback or n.is_link_local or n.is_unspecified
        )

    rejected = [n for n in ram + ripe + extra if not sane(n)]
    if rejected:
        print(f"WARNING: dropped {len(rejected)} suspicious entries: {rejected[:10]}", file=sys.stderr)
    merged = list(ipaddress.collapse_addresses([n for n in ram + ripe + extra if sane(n)] + local))

    # Fail if coverage grows sharply compared with the previous build.
    if out.exists():
        prev = [ipaddress.ip_network(x) for x in re.findall(r"address=([0-9./]+)", out.read_text())]
        prev_total = sum(n.num_addresses for n in prev)
        new_total = sum(n.num_addresses for n in merged)
        if prev_total and new_total > prev_total * 1.2:
            sys.exit(f"Address count jumped {prev_total} -> {new_total} (>20%); refusing to write. Review sources.")

    lines = ["/ip firewall address-list"]
    lines += [f"add address={n} list={LIST_NAME}" for n in merged]
    content = "\n".join(lines) + "\n"
    out.write_text(content)
    # Small hash file so routers can skip re-importing when nothing changed.
    out.with_suffix(".sha256").write_text(hashlib.sha256(content.encode()).hexdigest())
    print(f"ramtiiin={len(ram)} ripe={len(ripe)} extra={len(extra)} -> {len(merged)} entries -> {out}")


if __name__ == "__main__":
    main()
