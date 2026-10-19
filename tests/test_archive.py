import importlib.util
import io
from pathlib import Path
import tarfile
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('extract_sources', Path(__file__).parents[1] / 'scripts/extract_sources.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ExtractionTests(unittest.TestCase):
    def test_untrusted_archive_entries_are_not_followed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive_path = root / 'input.tar'
            with tarfile.open(archive_path, 'w') as archive:
                for name in ['release/good.txt', '../escape', '/absolute', 'release/dl/dependency']:
                    entry = tarfile.TarInfo(name)
                    entry.size = 4
                    entry.mode = 0o777
                    archive.addfile(entry, io.BytesIO(b'test'))
                link = tarfile.TarInfo('release/link')
                link.type = tarfile.SYMTYPE
                link.linkname = '../outside'
                archive.addfile(link)
            output = root / 'out'
            module.extract(archive_path, output)
            self.assertEqual([p.name for p in output.iterdir()], ['good.txt'])
            self.assertEqual((output / 'good.txt').read_bytes(), b'test')
            self.assertEqual((output / 'good.txt').stat().st_mode & 0o777, 0o600)
            with self.assertRaises(FileExistsError):
                module.extract(archive_path, output)


if __name__ == '__main__':
    unittest.main()
