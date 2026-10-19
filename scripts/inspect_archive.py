#!/usr/bin/env python3
"""Read a tar archive without extracting or executing its contents."""
import argparse
import hashlib
import json
from pathlib import Path
import tarfile


def inspect(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    entries = []
    with tarfile.open(path, 'r:*') as archive:
        for entry in archive:
            entries.append({'path': entry.name, 'size': entry.size,
                            'type': entry.type.decode('ascii', errors='replace'),
                            'link': entry.linkname or None})
    return {'file': path.name, 'bytes': path.stat().st_size,
            'sha256': digest.hexdigest(), 'entries': entries}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.write_text(json.dumps(inspect(args.archive), indent=2) + '\n')
