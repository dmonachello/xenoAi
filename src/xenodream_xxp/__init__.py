"""Lossless tools for observed XenoDream X parameter-file syntax."""

from .document import Document, parse_bytes, parse_file

__all__ = ["Document", "parse_bytes", "parse_file"]

