# Gold-set families

Working set for regenerative qualification research (ADR 0001). **0 packages are qualified.**

Each subdirectory is one family. The loop is [docs/characterization-loop.md](../docs/characterization-loop.md) (ADR 0003).

| Family | Public oracle | Notes |
|---|---|---|
| `json` | `zspecs/json.zspec.zsdl` | ADR 0002 spike: clean-room + held-out |
| `base64` | `zspecs/base64.zspec.zsdl` | RFC 4648 |
| `hashlib` | `zspecs/hashlib.zspec.zsdl` | FIPS 180-4 / RFC 1321 / FIPS 202 |
| `hmac` | `zspecs/hmac.zspec.zsdl` | RFC 4231 |
| `struct` | `zspecs/struct.zspec.zsdl` | explicit endian prefixes |
| `binascii` | `zspecs/binascii.zspec.zsdl` | ISO 3309 CRC |
| `fnmatch` | `zspecs/fnmatch.zspec.zsdl` | |
| `shlex` | `zspecs/shlex.zspec.zsdl` | |
| `urllib_parse` | `zspecs/urllib_parse.zspec.zsdl` | RFC 3986 |
| `difflib` | `zspecs/difflib.zspec.zsdl` | ratios 0.0 and 1.0 only |
| `tomli` | `zspecs/tomli.zspec.zsdl` | TOML 1.0; probes `tomllib` |
| `tomllib` | `zspecs/tomli.zspec.zsdl` | alias of `tomli` |
| `uuid` | `zspecs/uuid.zspec.zsdl` | npm `uuid`; RFC 9562 |
| `semver` | `zspecs/semver.zspec.zsdl` | SemVer 2.0.0 |
| `libpcap` | `zspecs/libpcap.zspec.zsdl` | offline savefiles |
| `pcap` | `zspecs/libpcap.zspec.zsdl` | alias of `libpcap` |
| `pcapng` | `zspecs/pcapng.zspec.zsdl` | draft-ietf-opsawg-pcapng |

Required files: `package.md`, `uncertainty.yaml`. Optional: `probes.yaml`, `held_out.zspec.zsdl`.

```bash
make characterize-gold
```
