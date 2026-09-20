# Gold-set families

`gold/<family>/` holds reviewed characterizations (ADR 0003). **0 packages are qualified.**

The loop is [docs/characterization-loop.md](../docs/characterization-loop.md). Passing a public oracle is `oracle_bound`, not `qualified`.

Two groups share this tree:

1. **Intended qualification set** (ADR 0001) — held-out oracles exist for the Python families that Phase 3 attempted. Dual independent generation did not happen ([ADR 0005](../docs/decisions/0005-characterization-is-the-product.md)).
2. **Characterization cohort** — high-feasibility Layer 2 specs taken through the same authority + ledger + live-probe loop. No held-out oracle. Not qualification targets. Grew in Phase 11 and the 2026-09-20 characterization pass.

## Intended qualification set

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

## Characterization cohort

| Family | Public oracle | Notes |
|---|---|---|
| `bisect` | `zspecs/bisect.zspec.zsdl` | insertion points; `key=` deferred |
| `operator` | `zspecs/operator.zspec.zsdl` | including documented `itemgetter` |
| `pprint` | `zspecs/pprint.zspec.zsdl` | `sort_dicts` True vs False |
| `html` | `zspecs/html.zspec.zsdl` | escape / HTML 5 unescape |
| `msgpack` | `zspecs/msgpack.zspec.zsdl` | MessagePack spec `packb`/`unpackb` |
| `ntpath` | `zspecs/ntpath.zspec.zsdl` | Windows path strings; `isabs('\\')` changes in 3.13 |
| `posixpath` | `zspecs/posixpath.zspec.zsdl` | POSIX path strings |
| `ipaddress` | `zspecs/ipaddress.zspec.zsdl` | RFC 791 / 1918 |
| `decimal` | `zspecs/decimal.zspec.zsdl` | IBM decimal arithmetic |
| `keyword` | `zspecs/keyword.zspec.zsdl` | hard keywords; soft keywords 3.12+ |
| `string` | `zspecs/string.zspec.zsdl` | ASCII constants + `capwords` |
| `calendar` | `zspecs/calendar.zspec.zsdl` | Gregorian helpers |
| `fractions` | `zspecs/fractions.zspec.zsdl` | rationals in lowest terms |
| `csv` | `zspecs/csv.zspec.zsdl` | RFC 4180 reader / excel dialect |
| `elementtree` | `zspecs/elementtree.zspec.zsdl` | `xml.etree.ElementTree` |
| `copy` | `zspecs/copy.zspec.zsdl` | shallow/deep copy of JSON-serializable values |
| `heapq` | `zspecs/heapq.zspec.zsdl` | nlargest / nsmallest |
| `reprlib` | `zspecs/reprlib.zspec.zsdl` | size-limited repr |
| `statistics` | `zspecs/statistics.zspec.zsdl` | mean / median / StatisticsError |
| `enum` | `zspecs/enum.zspec.zsdl` | functional API; StrEnum 3.11+ |
| `textwrap` | `zspecs/textwrap.zspec.zsdl` | wrap / fill / dedent |
| `weakref` | `zspecs/weakref.zspec.zsdl` | getweakrefcount / empty Weak* maps |
| `html_entities` | `zspecs/html_entities.zspec.zsdl` | `html.entities` name tables |
| `html_parser` | `zspecs/html_parser.zspec.zsdl` | `html.parser.HTMLParser` |
| `idna` | `zspecs/idna.zspec.zsdl` | IDNA 2008 encode/decode |
| `tomlkit` | `zspecs/tomlkit.zspec.zsdl` | TOML 1.0 loads |
| `colorsys` | `zspecs/colorsys.zspec.zsdl` | RGB/HSV/HLS/YIQ |
| `copyreg` | `zspecs/copyreg.zspec.zsdl` | pickle support registry |
| `genericpath` | `zspecs/genericpath.zspec.zsdl` | os.path.commonprefix helpers |
| `glob` | `zspecs/glob.zspec.zsdl` | pathname expansion + escape |
| `pathspec` | `zspecs/pathspec.zspec.zsdl` | gitignore-style matching |
| `quopri` | `zspecs/quopri.zspec.zsdl` | RFC 2045 quoted-printable |
| `uu` | `zspecs/uu.zspec.zsdl` | uuencode; skipped on 3.13+ |
| `ulid` | `zspecs/ulid.zspec.zsdl` | Crockford base32 time+entropy IDs |

Required files: `package.md`, `uncertainty.yaml`. Optional: `probes.yaml`, `held_out.zspec.zsdl`.

```bash
make characterize-gold
```
