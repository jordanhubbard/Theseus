---
family: logging_handlers
version: "0.1.0"
kind: library
ladder: oracle_bound
qualification: none
exports:
  - MemoryHandler
  - BaseRotatingHandler
public_oracle: zspecs/logging_handlers.zspec.zsdl
docs:
  - "https://docs.python.org/3/library/logging.handlers.html"
rfcs:
  []
---

# logging_handlers

SYSLOG_UDP_PORT=514 and SYSLOG_TCP_PORT=514 are the standard syslog port numbers. DEFAULT_TCP_LOGGING_PORT=9020, DEFAULT_UDP_LOGGING_PORT=9021, DEFAULT_HTTP_LOGGING_PORT=9022, DEFAULT_SOAP_LOGGING_PORT=9023. SysLogHandler priority constants: LOG_EMERG=0, LOG_ALERT=1, LOG_CRIT=2, LOG_ERR=3, LOG_WARNING=4, LOG_NOTICE=5, LOG_INFO=6, LOG_DEBUG=7. This file is the **authority** for a characterization-cohort family. It is not an implementation and it is not an executable oracle. The oracle is `zspecs/logging_handlers.zspec.zsdl`.

## Public surface

Exports listed in the frontmatter are the characterization surface. Layer 2 invariants call those names with arguments against the installed library.

## What is in scope

The live probes in `probes.yaml`, confirmed against the installed library. The rest of the public contract stays in the Layer 2 oracle.

## What is not in scope

I/O, process-global configuration, and error paths that the probes do not call. No held-out oracle and no clean-room attempt.

## Characterization loop

Draft from public docs/RFCs. Confirm expected values with `tools/live_probe.py` against the installed library. Do not read implementation source into a generation prompt. Review `uncertainty.yaml` until every item is `resolved`, `deferred`, or `held_out`. Passing the public oracle is **not** qualification (ADR 0001). This family is characterization-only: no held-out oracle and no clean-room attempt.

## Provenance

Derived from the docs in the frontmatter and the public Layer 2 oracle. Not derived from implementation source files.
