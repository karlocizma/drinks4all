_SIGNATURES: list[tuple[bytes, str]] = [
    (b"\xff\xd8\xff", ".jpg"),
    (b"\x89PNG\r\n\x1a\n", ".png"),
    (b"GIF87a", ".gif"),
    (b"GIF89a", ".gif"),
]


def sniff_image_extension(data: bytes) -> str | None:
    """Identify an image format from its magic bytes, ignoring any client-supplied filename/Content-Type.

    Returns the matching extension (e.g. ".png"), or None if the bytes don't match a known image format.
    """
    for signature, ext in _SIGNATURES:
        if data.startswith(signature):
            return ext
    if len(data) >= 12 and data[0:4] == b"RIFF" and data[8:12] == b"WEBP":
        return ".webp"
    return None
