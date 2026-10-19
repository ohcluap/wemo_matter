#!/usr/bin/env python3
"""Extract bounded regular files for static inspection; never preserve executable modes."""
import argparse
from pathlib import Path, PurePosixPath
import tarfile


def extract(archive_path, destination):
    destination.mkdir(parents=True, exist_ok=False)
    total = 0
    with tarfile.open(archive_path, 'r:*') as archive:
        for entry in archive:
            path = PurePosixPath(entry.name)
            if path.is_absolute() or '..' in path.parts or not entry.isfile():
                continue
            parts = path.parts[1:]
            if not parts or parts[0] == 'dl' or entry.size > 4 * 1024 * 1024:
                continue
            total += entry.size
            if total > 512 * 1024 * 1024:
                raise ValueError('Extraction size limit exceeded')
            target = destination.joinpath(*parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.extractfile(entry) as source, target.open('xb') as output:
                output.write(source.read())
            target.chmod(0o600)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    parser.add_argument('destination', type=Path)
    args = parser.parse_args()
    extract(args.archive, args.destination)
