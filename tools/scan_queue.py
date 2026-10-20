#!/usr/bin/env python3
"""Plan and run finite metadata scans, ranked by distinct dependency consumers."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from theseus.scan_queue import plan, run, _atomic_json


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['plan', 'run'])
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--queue', type=Path, default=ROOT / 'reports/scan-queue.json')
    parser.add_argument('--report', type=Path, default=ROOT / 'reports/scan-results.json')
    parser.add_argument('--limit', type=int, default=20)
    parser.add_argument('--jobs', type=int, default=4, help='Bounded concurrent registry requests (1..16)')
    parser.add_argument('--timeout', type=int, default=15)
    parser.add_argument('--ecosystem', action='append', choices=['pypi', 'npm'])
    parser.add_argument('--package', action='append', help='Exact ecosystem:name from queue')
    parser.add_argument('--refresh-covered', action='store_true')
    args = parser.parse_args(argv)
    try:
        if args.action == 'plan':
            result = plan(args.root)
            _atomic_json(args.queue, result)
            print(json.dumps(dict(queue=str(args.queue), counts=result['counts'])))
        else:
            result = run(args.root, json.loads(args.queue.read_text()), limit=args.limit,
                         timeout=args.timeout, jobs=args.jobs, ecosystems=args.ecosystem, packages=args.package,
                         refresh_covered=args.refresh_covered)
            _atomic_json(args.report, result)
            print(json.dumps(result, indent=2))
        return 1 if result.get('failed') else 0
    except (OSError, ValueError, KeyError) as exc:
        print('Error: %s' % exc, file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
