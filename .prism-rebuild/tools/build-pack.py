#!/usr/bin/env python3
"""Build a reproducible handoff ZIP. This does not package the rebuilt product."""
import argparse
from pathlib import Path
import re
import sys
import zipfile
from prism_pack import PACK_ROOT, digest, emit, pack_files, read_json, verify_manifest

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", default=str(PACK_ROOT))
    p.add_argument("--output", required=True)
    args = p.parse_args()
    root = Path(args.root).resolve(strict=True)
    out = Path(args.output).expanduser().resolve(strict=False)
    if out.is_relative_to(root) or out.exists() or out.is_symlink():
        raise ValueError("Choose a new output path outside the pack directory")
    integrity = verify_manifest(root)
    version = read_json(root / "pack.json")["packVersion"]
    if not isinstance(version, str) or not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+(?:-[0-9A-Za-z.-]+)?", version):
        raise ValueError("Pack version must be a portable semantic version")
    archive_root = "PRISM-Studio-Rebuild-Pack-v" + version
    files = sorted(pack_files(root) + [root / "MANIFEST.sha256"], key=lambda f: f.relative_to(root).as_posix())
    out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in files:
            rel = path.relative_to(root).as_posix()
            if path.suffix.lower() == ".pdf" or rel.startswith("project_sources/"):
                raise ValueError("Uploaded source books must not be redistributed in the handoff")
            item = zipfile.ZipInfo(archive_root + "/" + rel, date_time=(2026, 11, 26, 0, 0, 0))
            item.create_system = 3
            item.compress_type = zipfile.ZIP_DEFLATED
            item.external_attr = ((0o100755 if rel.startswith("tools/") and path.suffix == ".py" else 0o100644) << 16)
            archive.writestr(item, path.read_bytes(), compresslevel=9)
    emit({**integrity, "status": "BUILT", "scope": "Implementation handoff, not rebuilt product", "output": str(out), "files": len(files), "manifestEntries": integrity["files"], "archiveRoot": archive_root, "bytes": out.stat().st_size, "sha256": digest(out.read_bytes())})

if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, KeyError, zipfile.BadZipFile) as exc:
        emit({"status": "BLOCKED", "error": str(exc)})
        sys.exit(2)
