"""Atomic files and content-addressed cache entries with checked metadata."""
from __future__ import annotations
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import tempfile
from atar.identity import canonical_json, digest


def atomic_text(path: Path, text: str):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".pending-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def atomic_json(path: Path, value):
    atomic_text(path, json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


@contextmanager
def writer_lock(root: Path):
    root = Path(root)
    if root.is_symlink():
        raise ValueError("Output root must not be a symlink")
    root.mkdir(parents=True, exist_ok=True)
    path = root / ".writer.lock"
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise RuntimeError("Output is locked. Do not remove a lock while another writer runs") from exc
    try:
        os.write(fd, str(os.getpid()).encode())
        os.close(fd)
        yield
    finally:
        path.unlink(missing_ok=True)


class ResultCache:
    """A result is reusable only under the same complete caller-supplied context.

    Corruption is an error, not an excuse to silently replace an experiment.
    Cache keys cover code, data, configuration, candidate and window in the demo.
    """
    def __init__(self, root):
        self.root = Path(root)

    def get_or_compute(self, context: dict, compute):
        key = digest(context)
        path = self.root / f"{key}.json"
        if path.is_symlink():
            raise ValueError("Cache entry is a symlink")
        if path.exists():
            try:
                envelope = json.loads(path.read_text())
                result = envelope["result"]
                if envelope["context"] != context or envelope["sha256"] != digest(result):
                    raise ValueError("Cache context or digest mismatch")
            except (ValueError, KeyError, TypeError) as exc:
                raise RuntimeError("Corrupt or incompatible cache entry") from exc
            return result, True
        result = compute()
        atomic_json(path, {"context": context, "sha256": digest(result), "result": result})
        return result, False


def package_fingerprint() -> str:
    """Hash public Python sources without recording any absolute local paths."""
    root = Path(__file__).parent
    h = hashlib.sha256()
    for path in sorted(root.rglob("*.py")):
        h.update(path.relative_to(root).as_posix().encode())
        h.update(path.read_bytes())
    return h.hexdigest()
