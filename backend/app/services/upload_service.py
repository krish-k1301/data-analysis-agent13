import os
import uuid

from fastapi import UploadFile

from app.config import settings

ALLOWED_EXTENSIONS = {".csv", ".xlsx", ".xls"}


class UploadValidationError(Exception):
    pass


def validate_upload(file: UploadFile, size_bytes: int) -> str:
    """Validate extension and size. Returns the lowercase extension (with dot)."""
    _, ext = os.path.splitext(file.filename or "")
    ext = ext.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise UploadValidationError(
            f"Unsupported file type '{ext}'. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )

    max_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024
    if size_bytes > max_bytes:
        raise UploadValidationError(
            f"File exceeds max size of {settings.MAX_FILE_SIZE_MB}MB"
        )

    return ext


def save_upload(dataset_id: str, ext: str, content: bytes) -> str:
    """Persist raw upload bytes to disk. Returns the raw file path."""
    dataset_dir = os.path.join(settings.UPLOAD_DIR, dataset_id)
    os.makedirs(dataset_dir, exist_ok=True)
    raw_path = os.path.join(dataset_dir, f"raw{ext}")
    with open(raw_path, "wb") as f:
        f.write(content)
    return raw_path


def new_dataset_id() -> str:
    return str(uuid.uuid4())


FORMULA_PREFIXES = ("=", "+", "-", "@")


def sanitize_formula_injection(value):
    """Neutralize spreadsheet formula injection by prefixing risky leading
    characters with a single quote. Applied to string cells before any
    downstream export back to CSV/XLSX, since these files may be reopened
    in Excel by an auditor.
    """
    if isinstance(value, str) and value.startswith(FORMULA_PREFIXES):
        return "'" + value
    return value
