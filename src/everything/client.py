"""
Everything SDK v3 Python Wrapper

This module provides a Pythonic interface to the Everything desktop search
engine (https://www.voidtools.com/) via its native v3 DLL API.  It uses
``ctypes`` to call the C exports directly, so no compilation or additional
C-extension build step is required.

Typical usage::

    from everything import EverythingClient, format_size

    with EverythingClient() as client:
        client.connect()
        results, total = client.search("*.txt", match_path=True)
        for r in results:
            print(f"{r.full_path}: {format_size(r.size)}")

Note:
    Everything must be running on the host machine before a connection
    can be established.  Download it from https://www.voidtools.com/.
"""

import ctypes
import ctypes.wintypes as wintypes
import os
import sys
from datetime import datetime


class PropertyID:
    """Integer identifiers for the result properties exposed by the
    Everything SDK.  Used with ``Everything3_AddSearchPropertyRequest`` and
    ``Everything3_GetResultProperty*`` calls.

    See the SDK header ``Everything3.h`` for the canonical definitions.
    """

    NAME = 0
    PATH = 1
    SIZE = 2
    EXTENSION = 3
    TYPE = 4
    DATE_MODIFIED = 5
    DATE_CREATED = 6
    DATE_ACCESSED = 7
    ATTRIBUTES = 8
    DATE_RECENTLY_CHANGED = 9
    RUN_COUNT = 10
    DATE_RUN = 11
    FILE_LIST_NAME = 12
    WIDTH = 13
    HEIGHT = 14
    DIMENSIONS = 15
    ASPECT_RATIO = 16
    BIT_DEPTH = 17
    LENGTH = 18
    AUDIO_SAMPLE_RATE = 19
    AUDIO_CHANNELS = 20
    AUDIO_BITS_PER_SAMPLE = 21
    AUDIO_BIT_RATE = 22
    AUDIO_FORMAT = 23
    FILE_SIGNATURE = 24
    TITLE = 25
    ARTIST = 26
    ALBUM = 27
    YEAR = 28
    COMMENT = 29
    TRACK = 30
    GENRE = 31
    FRAME_RATE = 32
    VIDEO_BIT_RATE = 33
    VIDEO_FORMAT = 34
    RATING = 35
    TAGS = 36
    MD5 = 37
    SHA1 = 38
    SHA256 = 39
    CRC32 = 40
    SIZE_ON_DISK = 41


class FileAttribute:
    """Windows file-attribute bit flags (mirrors ``FILE_ATTRIBUTE_*``)."""

    READONLY = 0x01
    HIDDEN = 0x02
    SYSTEM = 0x04
    DIRECTORY = 0x10
    ARCHIVE = 0x20
    COMPRESSED = 0x40
    NORMAL = 0x80
    TEMPORARY = 0x100
    OFFLINE = 0x200
    INTEGRITY_STREAM = 0x1000


class EverythingError(Exception):
    """Raised when an Everything SDK call reports a failure.

    Attributes:
        error_code: The 32-bit error code returned by
            ``Everything3_GetLastError``.
    """

    ERROR_IPC_PIPE_NOT_FOUND = 0xE0000002

    def __init__(self, error_code):
        self.error_code = error_code
        if error_code == self.ERROR_IPC_PIPE_NOT_FOUND:
            message = "Everything is not running or IPC pipe not found"
        else:
            message = f"Everything SDK error, code: 0x{error_code:X}"
        super().__init__(message)


class SearchResult:
    """Immutable container holding the properties of a single Everything
    search result.

    All FILETIME timestamps are stored as raw 64-bit integers.  Convenience
    properties (``modified_time``, ``created_time``, ``accessed_time``)
    convert them to :class:`datetime.datetime` objects on the fly.
    """

    def __init__(self, name, parent_path, full_path, size, is_folder,
                 date_modified, date_created, date_accessed, attributes,
                 extension=""):
        self.name = name
        self.parent_path = parent_path
        self.full_path = full_path
        self.size = size
        self.is_folder = is_folder
        self.date_modified = date_modified
        self.date_created = date_created
        self.date_accessed = date_accessed
        self.attributes = attributes
        self.extension = extension

    @property
    def type_str(self):
        """Return ``"Folder"`` or ``"File"``."""
        return "Folder" if self.is_folder else "File"

    @property
    def modified_time(self):
        """Convert the FILETIME timestamp to a :class:`datetime`, or
        ``None`` if the value is zero (not available)."""
        if self.date_modified == 0:
            return None
        return datetime.fromtimestamp(
            self.date_modified / 10_000_000 - 11644473600
        )

    @property
    def created_time(self):
        """Convert the FILETIME timestamp to a :class:`datetime`, or
        ``None`` if the value is zero (not available)."""
        if self.date_created == 0:
            return None
        return datetime.fromtimestamp(
            self.date_created / 10_000_000 - 11644473600
        )

    @property
    def accessed_time(self):
        """Convert the FILETIME timestamp to a :class:`datetime`, or
        ``None`` if the value is zero (not available)."""
        if self.date_accessed == 0:
            return None
        return datetime.fromtimestamp(
            self.date_accessed / 10_000_000 - 11644473600
        )

    @property
    def attr_str(self):
        """Human-readable attribute string, e.g. ``"DA"`` for a normal
        directory with the archive bit set."""
        attr_map = {
            0x01: "R", 0x02: "H", 0x04: "S", 0x10: "D",
            0x20: "A", 0x40: "C", 0x80: "N", 0x100: "T",
            0x200: "O", 0x1000: "I",
        }
        result = []
        for bit, char in attr_map.items():
            if self.attributes & bit:
                result.append(char)
        return "".join(result) if result else "-"


class EverythingClient:
    """High-level wrapper around the Everything v3 DLL.

    Args:
        dll_path: Optional path to ``Everything3_x64.dll``.  When *None*
            (the default), the constructor searches for the DLL in several
            well-known locations — see :meth:`_find_dll` for details.

    Example::

        with EverythingClient() as client:
            client.connect()
            results, total = client.search("*.pdf")
    """

    def __init__(self, dll_path=None):
        if dll_path is None:
            dll_path = self._find_dll()

        if not os.path.exists(dll_path):
            raise FileNotFoundError(
                f"Everything3 DLL not found: {dll_path}"
            )

        self._dll = ctypes.WinDLL(dll_path)
        self._client = None
        self._setup_function_signatures()

    # ------------------------------------------------------------------
    # DLL discovery
    # ------------------------------------------------------------------

    @staticmethod
    def _find_dll():
        """Locate ``Everything3_x64.dll`` using a multi-strategy search.

        Strategies (checked in order):

        1. ``EVERYTHING_SDK_DIR`` environment variable — looks for
           ``<dir>/dll/Everything3_x64.dll`` or ``<dir>/Everything3_x64.dll``.
        2. ``PATH`` environment variable — scans every directory for
           ``Everything3_x64.dll``.
        3. Relative to this module — looks in sibling ``Everything-SDK``
           directories that are commonly found in developer setups.
        4. Common installation directories — checks ``Program Files`` and
           ``Program Files (x86)`` under an ``Everything`` sub-folder.

        Returns:
            Absolute path to the DLL.

        Raises:
            FileNotFoundError: If none of the strategies found the DLL.
        """
        # Strategy 1: Check EVERYTHING_SDK_DIR environment variable
        sdk_dir = os.environ.get("EVERYTHING_SDK_DIR")
        if sdk_dir:
            dll_path = os.path.join(sdk_dir, "dll", "Everything3_x64.dll")
            if os.path.exists(dll_path):
                return dll_path
            dll_path = os.path.join(sdk_dir, "Everything3_x64.dll")
            if os.path.exists(dll_path):
                return dll_path

        # Strategy 2: Check PATH environment variable
        path_env = os.environ.get("PATH", "")
        for path_dir in path_env.split(os.pathsep):
            dll_path = os.path.join(path_dir, "Everything3_x64.dll")
            if os.path.exists(dll_path):
                return dll_path

        # Strategy 3: Search relative to the SDK module location
        module_dir = os.path.dirname(os.path.abspath(__file__))
        for search_dir in [
            os.path.join(module_dir, "..", "..", "Everything-SDK"),
            os.path.join(module_dir, "..", "..", "..", "Everything-SDK"),
        ]:
            search_dir = os.path.normpath(search_dir)
            if os.path.exists(search_dir):
                for dll_subdir in ["dll", "SDK/DLL/x64", ""]:
                    dll_path = os.path.join(
                        search_dir, dll_subdir, "Everything3_x64.dll"
                    )
                    if os.path.exists(dll_path):
                        return dll_path

        # Strategy 4: Common installation locations
        common_paths = [
            os.path.join(
                os.environ.get("ProgramFiles", "C:\\Program Files"),
                "Everything", "Everything3_x64.dll",
            ),
            os.path.join(
                os.environ.get("ProgramFiles(x86)",
                               "C:\\Program Files (x86)"),
                "Everything", "Everything3_x64.dll",
            ),
        ]
        for dll_path in common_paths:
            if os.path.exists(dll_path):
                return dll_path

        raise FileNotFoundError(
            "Cannot find Everything3_x64.dll. Tried:\n"
            "  1. EVERYTHING_SDK_DIR environment variable, or\n"
            "  2. PATH environment variable, or\n"
            "  3. Passing dll_path directly to EverythingClient()"
        )

    # ------------------------------------------------------------------
    # DLL function signature setup
    # ------------------------------------------------------------------

    def _setup_function_signatures(self):
        """Declare ``restype`` / ``argtypes`` for every DLL export we use.

        This avoids ctypes calling-convention mis-detection and improves
        both safety and error messages when argument types are wrong.
        """
        dll = self._dll

        # Client lifecycle
        dll.Everything3_ConnectW.restype = ctypes.c_void_p
        dll.Everything3_ConnectW.argtypes = [ctypes.c_wchar_p]

        dll.Everything3_DestroyClient.restype = wintypes.BOOL
        dll.Everything3_DestroyClient.argtypes = [ctypes.c_void_p]

        dll.Everything3_GetLastError.restype = wintypes.DWORD
        dll.Everything3_GetLastError.argtypes = []

        # Version information
        dll.Everything3_GetMajorVersion.restype = wintypes.DWORD
        dll.Everything3_GetMajorVersion.argtypes = [ctypes.c_void_p]

        dll.Everything3_GetMinorVersion.restype = wintypes.DWORD
        dll.Everything3_GetMinorVersion.argtypes = [ctypes.c_void_p]

        dll.Everything3_GetRevision.restype = wintypes.DWORD
        dll.Everything3_GetRevision.argtypes = [ctypes.c_void_p]

        dll.Everything3_GetBuildNumber.restype = wintypes.DWORD
        dll.Everything3_GetBuildNumber.argtypes = [ctypes.c_void_p]

        # Database status
        dll.Everything3_IsDBLoaded.restype = wintypes.BOOL
        dll.Everything3_IsDBLoaded.argtypes = [ctypes.c_void_p]

        dll.Everything3_GetTargetMachine.restype = wintypes.DWORD
        dll.Everything3_GetTargetMachine.argtypes = [ctypes.c_void_p]

        # Search state management
        dll.Everything3_CreateSearchState.restype = ctypes.c_void_p
        dll.Everything3_CreateSearchState.argtypes = []

        dll.Everything3_DestroySearchState.restype = wintypes.BOOL
        dll.Everything3_DestroySearchState.argtypes = [ctypes.c_void_p]

        # Search options
        dll.Everything3_SetSearchTextW.restype = wintypes.BOOL
        dll.Everything3_SetSearchTextW.argtypes = [
            ctypes.c_void_p, ctypes.c_wchar_p,
        ]

        dll.Everything3_SetSearchMatchPath.restype = wintypes.BOOL
        dll.Everything3_SetSearchMatchPath.argtypes = [
            ctypes.c_void_p, wintypes.BOOL,
        ]

        dll.Everything3_SetSearchMatchCase.restype = wintypes.BOOL
        dll.Everything3_SetSearchMatchCase.argtypes = [
            ctypes.c_void_p, wintypes.BOOL,
        ]

        dll.Everything3_SetSearchMatchWholeWords.restype = wintypes.BOOL
        dll.Everything3_SetSearchMatchWholeWords.argtypes = [
            ctypes.c_void_p, wintypes.BOOL,
        ]

        dll.Everything3_SetSearchRegex.restype = wintypes.BOOL
        dll.Everything3_SetSearchRegex.argtypes = [
            ctypes.c_void_p, wintypes.BOOL,
        ]

        # Viewport (pagination) control
        dll.Everything3_SetSearchViewportCount.restype = wintypes.BOOL
        dll.Everything3_SetSearchViewportCount.argtypes = [
            ctypes.c_void_p, ctypes.c_size_t,
        ]

        dll.Everything3_SetSearchViewportOffset.restype = wintypes.BOOL
        dll.Everything3_SetSearchViewportOffset.argtypes = [
            ctypes.c_void_p, ctypes.c_size_t,
        ]

        # Property request / sort
        dll.Everything3_AddSearchPropertyRequest.restype = wintypes.BOOL
        dll.Everything3_AddSearchPropertyRequest.argtypes = [
            ctypes.c_void_p, wintypes.DWORD,
        ]

        dll.Everything3_AddSearchSort.restype = wintypes.BOOL
        dll.Everything3_AddSearchSort.argtypes = [
            ctypes.c_void_p, wintypes.DWORD, wintypes.BOOL,
        ]

        dll.Everything3_ClearSearchSorts.restype = wintypes.BOOL
        dll.Everything3_ClearSearchSorts.argtypes = [ctypes.c_void_p]

        # Execution & result list
        dll.Everything3_Search.restype = ctypes.c_void_p
        dll.Everything3_Search.argtypes = [
            ctypes.c_void_p, ctypes.c_void_p,
        ]

        dll.Everything3_DestroyResultList.restype = wintypes.BOOL
        dll.Everything3_DestroyResultList.argtypes = [ctypes.c_void_p]

        dll.Everything3_GetResultListCount.restype = ctypes.c_size_t
        dll.Everything3_GetResultListCount.argtypes = [ctypes.c_void_p]

        dll.Everything3_GetResultListViewportCount.restype = ctypes.c_size_t
        dll.Everything3_GetResultListViewportCount.argtypes = [
            ctypes.c_void_p,
        ]

        # Result property accessors
        dll.Everything3_GetResultPropertyUINT64.restype = ctypes.c_uint64
        dll.Everything3_GetResultPropertyUINT64.argtypes = [
            ctypes.c_void_p, ctypes.c_size_t, wintypes.DWORD,
        ]

        dll.Everything3_GetResultPropertyDWORD.restype = wintypes.DWORD
        dll.Everything3_GetResultPropertyDWORD.argtypes = [
            ctypes.c_void_p, ctypes.c_size_t, wintypes.DWORD,
        ]

        dll.Everything3_GetResultPropertyTextW.restype = ctypes.c_size_t
        dll.Everything3_GetResultPropertyTextW.argtypes = [
            ctypes.c_void_p, ctypes.c_size_t, wintypes.DWORD,
            ctypes.c_wchar_p, ctypes.c_size_t,
        ]

        dll.Everything3_IsFolderResult.restype = wintypes.BOOL
        dll.Everything3_IsFolderResult.argtypes = [
            ctypes.c_void_p, ctypes.c_size_t,
        ]

        dll.Everything3_GetResultFullPathNameW.restype = ctypes.c_size_t
        dll.Everything3_GetResultFullPathNameW.argtypes = [
            ctypes.c_void_p, ctypes.c_size_t, ctypes.c_wchar_p,
            ctypes.c_size_t,
        ]

        # Folder size query
        dll.Everything3_GetFolderSizeFromFilenameW.restype = ctypes.c_uint64
        dll.Everything3_GetFolderSizeFromFilenameW.argtypes = [
            ctypes.c_void_p, ctypes.c_wchar_p,
        ]

    # ------------------------------------------------------------------
    # Public connection API
    # ------------------------------------------------------------------

    def connect(self, version="1.5.0.1409a"):
        """Connect to a running Everything instance.

        Args:
            version: API version string to request (e.g. ``"1.5.0.1409a"``).

        Returns:
            *self*, to allow chaining with the constructor.

        Raises:
            EverythingError: If the connection attempt fails.
        """
        self._client = self._dll.Everything3_ConnectW(version)
        if not self._client:
            error = self._dll.Everything3_GetLastError()
            raise EverythingError(error)
        return self

    def disconnect(self):
        """Gracefully disconnect and release the client handle."""
        if self._client:
            self._dll.Everything3_DestroyClient(self._client)
            self._client = None

    # Context-manager support

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()

    # ------------------------------------------------------------------
    # Informational properties
    # ------------------------------------------------------------------

    @property
    def version(self):
        """Short version string, e.g. ``"1.5"``."""
        if not self._client:
            raise RuntimeError("Not connected to Everything")
        major = self._dll.Everything3_GetMajorVersion(self._client)
        minor = self._dll.Everything3_GetMinorVersion(self._client)
        return f"{major}.{minor}"

    @property
    def full_version(self):
        """Full version string including revision and build, e.g.
        ``"1.5.0.1234"``."""
        if not self._client:
            raise RuntimeError("Not connected to Everything")
        major = self._dll.Everything3_GetMajorVersion(self._client)
        minor = self._dll.Everything3_GetMinorVersion(self._client)
        revision = self._dll.Everything3_GetRevision(self._client)
        build = self._dll.Everything3_GetBuildNumber(self._client)
        return f"{major}.{minor}.{revision}.{build}"

    def is_db_loaded(self):
        """Return ``True`` if the Everything database has finished
        loading."""
        if not self._client:
            raise RuntimeError("Not connected to Everything")
        return bool(self._dll.Everything3_IsDBLoaded(self._client))

    def get_target_machine(self):
        """Return the target machine architecture code (0 = x86, 1 =
        x64)."""
        if not self._client:
            raise RuntimeError("Not connected to Everything")
        return self._dll.Everything3_GetTargetMachine(self._client)

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def search(self, search_text, match_path=False, match_case=False,
               match_whole_word=False, regex=False, properties=None,
               sort=None, max_results=None, offset=None):
        """Execute an Everything search query.

        Args:
            search_text: Everything query string (e.g. ``"*.txt"``,
                ``parent:"C:\\\\Users"``).
            match_path: Match against full file paths as well as names.
            match_case: Perform a case-sensitive match.
            match_whole_word: Only match whole words.
            regex: Treat *search_text* as a regular expression.
            properties: List of :class:`PropertyID` values to request.
                Defaults to NAME, PATH, SIZE, DATE_CREATED, DATE_MODIFIED,
                ATTRIBUTES, and EXTENSION.
            sort: List of ``(PropertyID, ascending)`` tuples for
                server-side result ordering.
            max_results: Maximum number of results to return (viewport
                count).
            offset: Result offset for pagination.

        Returns:
            A tuple ``(results, total_count)`` where *results* is a list
            of :class:`SearchResult` instances.

        Raises:
            RuntimeError: If the client is not connected.
            EverythingError: If the DLL reports an error during the search.
        """
        if not self._client:
            raise RuntimeError("Not connected to Everything")

        if properties is None:
            properties = [
                PropertyID.NAME, PropertyID.PATH, PropertyID.SIZE,
                PropertyID.DATE_CREATED, PropertyID.DATE_MODIFIED,
                PropertyID.ATTRIBUTES, PropertyID.EXTENSION,
            ]

        search_state = self._dll.Everything3_CreateSearchState()
        if not search_state:
            raise RuntimeError("Failed to create search state")

        try:
            # Configure search options
            self._dll.Everything3_SetSearchTextW(search_state, search_text)
            self._dll.Everything3_SetSearchMatchPath(
                search_state, match_path
            )
            self._dll.Everything3_SetSearchMatchCase(
                search_state, match_case
            )
            self._dll.Everything3_SetSearchMatchWholeWords(
                search_state, match_whole_word
            )
            self._dll.Everything3_SetSearchRegex(search_state, regex)

            # Pagination
            if max_results is not None:
                self._dll.Everything3_SetSearchViewportCount(
                    search_state, max_results
                )
            if offset is not None:
                self._dll.Everything3_SetSearchViewportOffset(
                    search_state, offset
                )

            # Request specific properties
            for prop_id in properties:
                self._dll.Everything3_AddSearchPropertyRequest(
                    search_state, prop_id
                )

            # Server-side sorting
            if sort:
                self._dll.Everything3_ClearSearchSorts(search_state)
                for prop_id, ascending in sort:
                    self._dll.Everything3_AddSearchSort(
                        search_state, prop_id, ascending
                    )

            # Execute
            result_list = self._dll.Everything3_Search(
                self._client, search_state
            )
            if not result_list:
                error = self._dll.Everything3_GetLastError()
                raise EverythingError(error)

            try:
                return self._parse_results(result_list, max_results)
            finally:
                self._dll.Everything3_DestroyResultList(result_list)
        finally:
            self._dll.Everything3_DestroySearchState(search_state)

    # ------------------------------------------------------------------
    # Internal result parsing
    # ------------------------------------------------------------------

    def _parse_results(self, result_list, max_results=None):
        """Convert a raw DLL result list into Python :class:`SearchResult`
        objects.

        Args:
            result_list: Opaque pointer returned by ``Everything3_Search``.
            max_results: Optional cap on how many results to extract.

        Returns:
            A tuple ``(results, total_count)``.
        """
        num_results = self._dll.Everything3_GetResultListViewportCount(
            result_list
        )
        total_results = self._dll.Everything3_GetResultListCount(
            result_list
        )

        if max_results is not None:
            num_results = min(num_results, max_results)

        # Pre-allocate reusable buffers to avoid per-iteration allocations
        name_buf = ctypes.create_unicode_buffer(260)
        path_buf = ctypes.create_unicode_buffer(1024)
        ext_buf = ctypes.create_unicode_buffer(64)

        results = []
        for i in range(num_results):
            is_folder = bool(
                self._dll.Everything3_IsFolderResult(result_list, i)
            )

            # File name
            self._dll.Everything3_GetResultPropertyTextW(
                result_list, i, PropertyID.NAME, name_buf, 260
            )
            file_name = name_buf.value

            # Parent directory path
            self._dll.Everything3_GetResultPropertyTextW(
                result_list, i, PropertyID.PATH, path_buf, 1024
            )
            parent_path = path_buf.value

            if parent_path and not parent_path.endswith("\\"):
                parent_path += "\\"
            full_path = os.path.join(parent_path, file_name)

            # Numeric properties
            size_val = self._dll.Everything3_GetResultPropertyUINT64(
                result_list, i, PropertyID.SIZE
            )
            date_modified = self._dll.Everything3_GetResultPropertyUINT64(
                result_list, i, PropertyID.DATE_MODIFIED
            )
            date_created = self._dll.Everything3_GetResultPropertyUINT64(
                result_list, i, PropertyID.DATE_CREATED
            )
            date_accessed = self._dll.Everything3_GetResultPropertyUINT64(
                result_list, i, PropertyID.DATE_ACCESSED
            )
            attrs_val = self._dll.Everything3_GetResultPropertyDWORD(
                result_list, i, PropertyID.ATTRIBUTES
            )

            # Extension (files only — folders return an empty string)
            extension = ""
            if not is_folder:
                self._dll.Everything3_GetResultPropertyTextW(
                    result_list, i, PropertyID.EXTENSION, ext_buf, 64
                )
                extension = ext_buf.value

            results.append(SearchResult(
                name=file_name,
                parent_path=parent_path,
                full_path=full_path,
                size=size_val,
                is_folder=is_folder,
                date_modified=date_modified,
                date_created=date_created,
                date_accessed=date_accessed,
                attributes=attrs_val,
                extension=extension,
            ))

        return results, total_results

    # ------------------------------------------------------------------
    # Folder size helper
    # ------------------------------------------------------------------

    def get_folder_size(self, folder_path):
        """Retrieve the on-disk size of a folder by querying Everything.

        Args:
            folder_path: Absolute path to the folder.

        Returns:
            Size in bytes.
        """
        if not self._client:
            raise RuntimeError("Not connected to Everything")
        return self._dll.Everything3_GetFolderSizeFromFilenameW(
            self._client, folder_path
        )


# ------------------------------------------------------------------
# Standalone utility
# ------------------------------------------------------------------

def format_size(size_bytes):
    """Format a byte count into a human-readable string.

    Examples::

        >>> format_size(1024)
        '1.00 KB'
        >>> format_size(1073741824)
        '1.00 GB'
    """
    if size_bytes == 0:
        return "0 B"
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"
