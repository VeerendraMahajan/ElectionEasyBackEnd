import hashlib


def calculate_sha256(file_path: str) -> str:
    """Calculate SHA-256 hash of a file using chunked streaming."""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def calculate_bytes_sha256(data: bytes) -> str:
    """Calculate SHA-256 hash of byte content."""
    return hashlib.sha256(data).hexdigest()
