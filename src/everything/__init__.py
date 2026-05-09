"""
everything — Python wrapper for the Everything SDK v3.

Provides :class:`EverythingClient`, :class:`SearchResult`,
:class:`PropertyID`, :class:`FileAttribute`, :class:`EverythingError`,
and the :func:`format_size` utility.

Quick start::

    from everything import EverythingClient, format_size

    with EverythingClient() as client:
        client.connect()
        results, total = client.search("*.txt")
        for r in results:
            print(f"{r.full_path}: {format_size(r.size)}")
"""

from .client import EverythingClient, EverythingError, PropertyID, FileAttribute, SearchResult, format_size

__version__ = "1.0.0"
__all__ = [
    "EverythingClient",
    "EverythingError",
    "PropertyID",
    "FileAttribute",
    "SearchResult",
    "format_size",
]
