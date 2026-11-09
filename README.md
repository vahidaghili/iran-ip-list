# Iran IP list for MikroTik split-tunnel

A merged, de-duplicated MikroTik address-list (`list=IRAN`) of Iranian IPv4 ranges. On a MikroTik split-tunnel setup, traffic to Iranian sites goes out directly and everything else goes through the VPN.

## Sources
- [Ramtiiin/iran-ip](https://github.com/Ramtiiin/iran-ip): hand-curated list
- [RIPE NCC country resource list (IR)](https://stat.ripe.net/data/country-resource-list/data.json?resource=IR): official registry data
- `extra-ranges.txt`: manual additions
- Private / CGNAT ranges (`10/8`, `172.16/12`, `192.168/16`, `100.64/10`)

A GitHub Action rebuilds `iran-ip-merged.rsc` daily. It also rebuilds on every change to `extra-ranges.txt`.

## Usage on MikroTik
```
/tool fetch url="https://raw.githubusercontent.com/vahidaghili/iran-ip-list/main/iran-ip-merged.rsc" dst-path=ip-list.rsc
/ip firewall address-list remove [find list=IRAN]
/import file-name=ip-list.rsc
```

## A site still doesn't open?
Find the site's IP and add its range to `extra-ranges.txt`. The Action will regenerate the list.

## Build locally
```
python3 build_iran_list.py iran-ip-merged.rsc
```
