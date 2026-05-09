import ctypes
import os
import sys
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from everything.client import (
    EverythingClient,
    EverythingError,
    FileAttribute,
    PropertyID,
    SearchResult,
    format_size,
)


@pytest.fixture
def mock_windll():
    with patch("ctypes.WinDLL") as mock:
        yield mock


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def test_data_path(tmp_path):
    """Create a temporary test data directory and return its path."""
    data_dir = tmp_path / "test_data"
    data_dir.mkdir()
    (data_dir / "test.txt").write_text("hello")
    (data_dir / "readme.md").write_text("# readme")
    sub = data_dir / "subdir"
    sub.mkdir()
    (sub / "nested.txt").write_text("nested")
    return str(data_dir)


@pytest.fixture
def sample_result(test_data_path):
    return SearchResult(
        name="test.txt",
        parent_path=test_data_path + os.sep,
        full_path=os.path.join(test_data_path, "test.txt"),
        size=1024,
        is_folder=False,
        date_modified=133000000000000000,
        date_created=132900000000000000,
        date_accessed=133100000000000000,
        attributes=0x20,
        extension="txt",
    )


@pytest.fixture
def sample_folder_result(test_data_path):
    return SearchResult(
        name="Documents",
        parent_path=test_data_path + os.sep,
        full_path=os.path.join(test_data_path, "Documents"),
        size=0,
        is_folder=True,
        date_modified=133000000000000000,
        date_created=132900000000000000,
        date_accessed=0,
        attributes=0x10,
        extension="",
    )


@pytest.fixture
def connected_client():
    with patch.object(EverythingClient, "_find_dll", return_value="fake.dll"):
        with patch("os.path.exists", return_value=True):
            with patch("ctypes.WinDLL") as mock_windll:
                mock_dll = MagicMock()
                mock_windll.return_value = mock_dll

                mock_dll.Everything3_ConnectW.return_value = MagicMock()
                mock_dll.Everything3_GetMajorVersion.return_value = 1
                mock_dll.Everything3_GetMinorVersion.return_value = 5
                mock_dll.Everything3_GetRevision.return_value = 0
                mock_dll.Everything3_GetBuildNumber.return_value = 1234
                mock_dll.Everything3_IsDBLoaded.return_value = True
                mock_dll.Everything3_GetTargetMachine.return_value = 1

                client = EverythingClient()
                client.connect("1.5a")
                yield client
                client.disconnect()


# ============================================================
# PropertyID Tests
# ============================================================

class TestPropertyID:
    def test_core_property_ids(self):
        assert PropertyID.NAME == 0
        assert PropertyID.PATH == 1
        assert PropertyID.SIZE == 2
        assert PropertyID.EXTENSION == 3
        assert PropertyID.TYPE == 4
        assert PropertyID.DATE_MODIFIED == 5
        assert PropertyID.DATE_CREATED == 6
        assert PropertyID.DATE_ACCESSED == 7
        assert PropertyID.ATTRIBUTES == 8

    def test_extended_property_ids(self):
        assert PropertyID.DATE_RECENTLY_CHANGED == 9
        assert PropertyID.RUN_COUNT == 10
        assert PropertyID.DATE_RUN == 11
        assert PropertyID.FILE_LIST_NAME == 12

    def test_media_property_ids(self):
        assert PropertyID.WIDTH == 13
        assert PropertyID.HEIGHT == 14
        assert PropertyID.DIMENSIONS == 15
        assert PropertyID.ASPECT_RATIO == 16
        assert PropertyID.BIT_DEPTH == 17
        assert PropertyID.LENGTH == 18

    def test_audio_property_ids(self):
        assert PropertyID.AUDIO_SAMPLE_RATE == 19
        assert PropertyID.AUDIO_CHANNELS == 20
        assert PropertyID.AUDIO_BITS_PER_SAMPLE == 21
        assert PropertyID.AUDIO_BIT_RATE == 22
        assert PropertyID.AUDIO_FORMAT == 23

    def test_hash_property_ids(self):
        assert PropertyID.MD5 == 37
        assert PropertyID.SHA1 == 38
        assert PropertyID.SHA256 == 39
        assert PropertyID.CRC32 == 40

    def test_size_on_disk(self):
        assert PropertyID.SIZE_ON_DISK == 41


# ============================================================
# FileAttribute Tests
# ============================================================

class TestFileAttribute:
    def test_readonly(self):
        assert FileAttribute.READONLY == 0x01

    def test_hidden(self):
        assert FileAttribute.HIDDEN == 0x02

    def test_system(self):
        assert FileAttribute.SYSTEM == 0x04

    def test_directory(self):
        assert FileAttribute.DIRECTORY == 0x10

    def test_archive(self):
        assert FileAttribute.ARCHIVE == 0x20

    def test_compressed(self):
        assert FileAttribute.COMPRESSED == 0x40

    def test_normal(self):
        assert FileAttribute.NORMAL == 0x80

    def test_temporary(self):
        assert FileAttribute.TEMPORARY == 0x100

    def test_offline(self):
        assert FileAttribute.OFFLINE == 0x200

    def test_integrity_stream(self):
        assert FileAttribute.INTEGRITY_STREAM == 0x1000


# ============================================================
# EverythingError Tests
# ============================================================

class TestEverythingError:
    def test_ipc_pipe_not_found_error(self):
        error = EverythingError(EverythingError.ERROR_IPC_PIPE_NOT_FOUND)
        assert error.error_code == 0xE0000002
        assert "Everything is not running" in str(error)

    def test_generic_error(self):
        error = EverythingError(0xDEADBEEF)
        assert error.error_code == 0xDEADBEEF
        assert "0xDEADBEEF" in str(error)

    def test_is_exception(self):
        assert issubclass(EverythingError, Exception)


# ============================================================
# SearchResult Tests
# ============================================================

class TestSearchResult:
    def test_file_type_str(self, sample_result):
        assert sample_result.type_str == "File"

    def test_folder_type_str(self, sample_folder_result):
        assert sample_folder_result.type_str == "Folder"

    def test_modified_time(self, sample_result):
        dt = sample_result.modified_time
        assert isinstance(dt, datetime)
        assert dt.year > 2020

    def test_created_time(self, sample_result):
        dt = sample_result.created_time
        assert isinstance(dt, datetime)
        assert dt.year > 2020

    def test_accessed_time(self, sample_result):
        dt = sample_result.accessed_time
        assert isinstance(dt, datetime)
        assert dt.year > 2020

    def test_accessed_time_zero(self, sample_folder_result):
        assert sample_folder_result.accessed_time is None

    def test_modified_time_zero(self):
        result = SearchResult(
            name="test", parent_path="", full_path="", size=0,
            is_folder=False, date_modified=0, date_created=0,
            date_accessed=0, attributes=0,
        )
        assert result.modified_time is None
        assert result.created_time is None

    def test_attr_str_archive(self, sample_result):
        assert "A" in sample_result.attr_str

    def test_attr_str_directory(self, sample_folder_result):
        assert "D" in sample_folder_result.attr_str

    def test_attr_str_empty(self):
        result = SearchResult(
            name="test", parent_path="", full_path="", size=0,
            is_folder=False, date_modified=0, date_created=0,
            date_accessed=0, attributes=0,
        )
        assert result.attr_str == "-"

    def test_attr_str_multiple(self):
        result = SearchResult(
            name="test", parent_path="", full_path="", size=0,
            is_folder=False, date_modified=0, date_created=0,
            date_accessed=0, attributes=0x22,
        )
        assert "H" in result.attr_str
        assert "A" in result.attr_str

    def test_extension_file(self, sample_result):
        assert sample_result.extension == "txt"

    def test_extension_folder(self, sample_folder_result):
        assert sample_folder_result.extension == ""

    def test_full_path(self, sample_result, test_data_path):
        assert sample_result.full_path == os.path.join(test_data_path, "test.txt")

    def test_size(self, sample_result):
        assert sample_result.size == 1024


# ============================================================
# format_size Tests
# ============================================================

class TestFormatSize:
    def test_zero_bytes(self):
        assert format_size(0) == "0 B"

    def test_bytes(self):
        assert format_size(512) == "512.00 B"

    def test_kilobytes(self):
        assert format_size(1024) == "1.00 KB"

    def test_megabytes(self):
        assert format_size(1048576) == "1.00 MB"

    def test_gigabytes(self):
        assert format_size(1073741824) == "1.00 GB"

    def test_terabytes(self):
        assert format_size(1099511627776) == "1.00 TB"

    def test_fractional(self):
        result = format_size(1536)
        assert "1.50 KB" == result

    def test_large_value(self):
        result = format_size(10**18)
        assert "PB" in result


# ============================================================
# EverythingClient DLL Discovery Tests
# ============================================================

class TestClientDLLDiscovery:
    def test_find_dll_via_env_var(self, tmp_path, monkeypatch):
        sdk_dir = tmp_path / "sdk"
        dll_dir = sdk_dir / "dll"
        dll_dir.mkdir(parents=True)
        dll_file = dll_dir / "Everything3_x64.dll"
        dll_file.touch()

        monkeypatch.setenv("EVERYTHING_SDK_DIR", str(sdk_dir))

        with patch.object(EverythingClient, "_find_dll", wraps=EverythingClient._find_dll):
            result = EverythingClient._find_dll()
            assert result == str(dll_file)

    def test_find_dll_via_path_env(self, tmp_path, monkeypatch):
        dll_dir = tmp_path / "bin"
        dll_dir.mkdir()
        dll_file = dll_dir / "Everything3_x64.dll"
        dll_file.touch()

        monkeypatch.setenv("PATH", str(dll_dir))
        monkeypatch.delenv("EVERYTHING_SDK_DIR", raising=False)

        with patch.object(EverythingClient, "_find_dll", wraps=EverythingClient._find_dll):
            result = EverythingClient._find_dll()
            assert result == str(dll_file)

    def test_find_dll_not_found(self, monkeypatch):
        monkeypatch.delenv("EVERYTHING_SDK_DIR", raising=False)
        monkeypatch.setenv("PATH", "")

        with patch.object(EverythingClient, "_find_dll", wraps=EverythingClient._find_dll):
            with patch("os.path.exists", return_value=False):
                with pytest.raises(FileNotFoundError, match="找不到"):
                    EverythingClient._find_dll()


# ============================================================
# EverythingClient Connection Tests
# ============================================================

class TestClientConnection:
    def test_connect_success(self, connected_client):
        assert connected_client._client is not None

    def test_disconnect(self, connected_client):
        connected_client.disconnect()
        assert connected_client._client is None

    def test_context_manager(self):
        with patch.object(EverythingClient, "_find_dll", return_value="fake.dll"):
            with patch("os.path.exists", return_value=True):
                with patch("ctypes.WinDLL") as mock_windll:
                    mock_dll = MagicMock()
                    mock_windll.return_value = mock_dll
                    mock_dll.Everything3_ConnectW.return_value = MagicMock()

                    with EverythingClient() as client:
                        client.connect("1.5a")
                        assert client._client is not None

                    mock_dll.Everything3_DestroyClient.assert_called_once()

    def test_connect_failure(self):
        with patch.object(EverythingClient, "_find_dll", return_value="fake.dll"):
            with patch("os.path.exists", return_value=True):
                with patch("ctypes.WinDLL") as mock_windll:
                    mock_dll = MagicMock()
                    mock_windll.return_value = mock_dll
                    mock_dll.Everything3_ConnectW.return_value = None
                    mock_dll.Everything3_GetLastError.return_value = EverythingError.ERROR_IPC_PIPE_NOT_FOUND

                    client = EverythingClient()
                    with pytest.raises(EverythingError):
                        client.connect("1.5a")

    def test_dll_not_found(self):
        with pytest.raises(FileNotFoundError):
            EverythingClient(dll_path="nonexistent.dll")


# ============================================================
# EverythingClient Version Tests
# ============================================================

class TestClientVersion:
    def test_version(self, connected_client):
        assert connected_client.version == "1.5"

    def test_full_version(self, connected_client):
        assert connected_client.full_version == "1.5.0.1234"

    def test_version_not_connected(self):
        with patch.object(EverythingClient, "_find_dll", return_value="fake.dll"):
            with patch("os.path.exists", return_value=True):
                with patch("ctypes.WinDLL") as mock_windll:
                    mock_windll.return_value = MagicMock()
                    client = EverythingClient()
                    with pytest.raises(RuntimeError, match="未连接到"):
                        _ = client.version

    def test_full_version_not_connected(self):
        with patch.object(EverythingClient, "_find_dll", return_value="fake.dll"):
            with patch("os.path.exists", return_value=True):
                with patch("ctypes.WinDLL") as mock_windll:
                    mock_windll.return_value = MagicMock()
                    client = EverythingClient()
                    with pytest.raises(RuntimeError, match="未连接到"):
                        _ = client.full_version


# ============================================================
# EverythingClient Status Tests
# ============================================================

class TestClientStatus:
    def test_is_db_loaded(self, connected_client):
        assert connected_client.is_db_loaded() is True

    def test_get_target_machine(self, connected_client):
        assert connected_client.get_target_machine() == 1


# ============================================================
# EverythingClient Search Tests
# ============================================================

class TestClientSearch:
    @pytest.fixture
    def search_client(self, mock_windll, test_data_path):
        mock_dll = MagicMock()
        mock_windll.return_value = mock_dll
        mock_dll.Everything3_ConnectW.return_value = MagicMock()
        mock_dll.Everything3_GetMajorVersion.return_value = 1
        mock_dll.Everything3_GetMinorVersion.return_value = 5
        mock_dll.Everything3_GetRevision.return_value = 0
        mock_dll.Everything3_GetBuildNumber.return_value = 1234
        mock_dll.Everything3_CreateSearchState.return_value = MagicMock()
        mock_dll.Everything3_GetResultListViewportCount.return_value = 3
        mock_dll.Everything3_GetResultListCount.return_value = 10
        mock_dll.Everything3_IsFolderResult.return_value = False
        mock_dll.Everything3_GetResultPropertyTextW.return_value = 0
        mock_dll.Everything3_GetResultPropertyUINT64.return_value = 0
        mock_dll.Everything3_GetResultPropertyDWORD.return_value = 0
        mock_dll.Everything3_Search.return_value = MagicMock()

        def get_text_side_effect(result_list, index, prop_id, buf, buf_size):
            if prop_id == PropertyID.NAME:
                buf.value = f"file{index}.txt"
            elif prop_id == PropertyID.PATH:
                buf.value = test_data_path
            elif prop_id == PropertyID.EXTENSION:
                buf.value = "txt"

        mock_dll.Everything3_GetResultPropertyTextW.side_effect = get_text_side_effect
        return mock_dll

    def test_basic_search(self, search_client, test_data_path):
        with patch.object(EverythingClient, "_find_dll", return_value="fake.dll"):
            with patch("os.path.exists", return_value=True):
                client = EverythingClient()
                client.connect("1.5a")
                results, total = client.search("test")

                assert total == 10
                assert len(results) == 3
                search_client.Everything3_SetSearchTextW.assert_called_once()
                search_client.Everything3_Search.assert_called_once()

    def test_search_with_match_path(self, search_client, test_data_path):
        with patch.object(EverythingClient, "_find_dll", return_value="fake.dll"):
            with patch("os.path.exists", return_value=True):
                client = EverythingClient()
                client.connect("1.5a")
                client.search("test", match_path=True)

                search_client.Everything3_SetSearchMatchPath.assert_called_with(
                    search_client.Everything3_CreateSearchState.return_value, True)

    def test_search_with_match_case(self, search_client):
        with patch.object(EverythingClient, "_find_dll", return_value="fake.dll"):
            with patch("os.path.exists", return_value=True):
                client = EverythingClient()
                client.connect("1.5a")
                client.search("Test", match_case=True)

                search_client.Everything3_SetSearchMatchCase.assert_called_with(
                    search_client.Everything3_CreateSearchState.return_value, True)

    def test_search_with_match_whole_word(self, search_client):
        with patch.object(EverythingClient, "_find_dll", return_value="fake.dll"):
            with patch("os.path.exists", return_value=True):
                client = EverythingClient()
                client.connect("1.5a")
                client.search("test", match_whole_word=True)

                search_client.Everything3_SetSearchMatchWholeWords.assert_called_with(
                    search_client.Everything3_CreateSearchState.return_value, True)

    def test_search_with_regex(self, search_client):
        with patch.object(EverythingClient, "_find_dll", return_value="fake.dll"):
            with patch("os.path.exists", return_value=True):
                client = EverythingClient()
                client.connect("1.5a")
                client.search(".*\\.txt$", regex=True)

                search_client.Everything3_SetSearchRegex.assert_called_with(
                    search_client.Everything3_CreateSearchState.return_value, True)

    def test_search_with_max_results(self, search_client):
        search_client.Everything3_GetResultListViewportCount.return_value = 100

        with patch.object(EverythingClient, "_find_dll", return_value="fake.dll"):
            with patch("os.path.exists", return_value=True):
                client = EverythingClient()
                client.connect("1.5a")
                results, total = client.search("test", max_results=5)

                assert len(results) == 5
                search_client.Everything3_SetSearchViewportCount.assert_called_once()

    def test_search_with_offset(self, search_client):
        with patch.object(EverythingClient, "_find_dll", return_value="fake.dll"):
            with patch("os.path.exists", return_value=True):
                client = EverythingClient()
                client.connect("1.5a")
                client.search("test", offset=10)

                search_client.Everything3_SetSearchViewportOffset.assert_called_with(
                    search_client.Everything3_CreateSearchState.return_value, 10)

    def test_search_with_sort(self, search_client):
        with patch.object(EverythingClient, "_find_dll", return_value="fake.dll"):
            with patch("os.path.exists", return_value=True):
                client = EverythingClient()
                client.connect("1.5a")
                sort = [(PropertyID.SIZE, False), (PropertyID.NAME, True)]
                client.search("test", sort=sort)

                search_client.Everything3_ClearSearchSorts.assert_called_once()
                assert search_client.Everything3_AddSearchSort.call_count == 2

    def test_search_with_custom_properties(self, search_client):
        with patch.object(EverythingClient, "_find_dll", return_value="fake.dll"):
            with patch("os.path.exists", return_value=True):
                client = EverythingClient()
                client.connect("1.5a")
                client.search("test", properties=[PropertyID.NAME, PropertyID.SIZE])

                assert search_client.Everything3_AddSearchPropertyRequest.call_count == 2

    def test_search_not_connected(self):
        with patch.object(EverythingClient, "_find_dll", return_value="fake.dll"):
            with patch("os.path.exists", return_value=True):
                with patch("ctypes.WinDLL") as mock_windll:
                    mock_windll.return_value = MagicMock()
                    client = EverythingClient()
                    with pytest.raises(RuntimeError, match="未连接到"):
                        client.search("test")

    def test_search_failure(self, mock_windll):
        mock_dll = MagicMock()
        mock_windll.return_value = mock_dll
        mock_dll.Everything3_ConnectW.return_value = MagicMock()
        mock_dll.Everything3_GetMajorVersion.return_value = 1
        mock_dll.Everything3_GetMinorVersion.return_value = 5
        mock_dll.Everything3_GetRevision.return_value = 0
        mock_dll.Everything3_GetBuildNumber.return_value = 1234
        mock_dll.Everything3_CreateSearchState.return_value = MagicMock()
        mock_dll.Everything3_Search.return_value = None
        mock_dll.Everything3_GetLastError.return_value = 1

        with patch.object(EverythingClient, "_find_dll", return_value="fake.dll"):
            with patch("os.path.exists", return_value=True):
                client = EverythingClient()
                client.connect("1.5a")
                with pytest.raises(EverythingError):
                    client.search("test")


# ============================================================
# EverythingClient Database Management Tests
# ============================================================

class TestClientDBManagement:
    pass


# ============================================================
# EverythingClient get_folder_size Tests
# ============================================================

class TestClientFolderSize:
    def test_get_folder_size(self, connected_client):
        connected_client._dll.Everything3_GetFolderSizeFromFilenameW.return_value = 1048576
        result = connected_client.get_folder_size("C:\\test\\folder")
        assert result == 1048576

    def test_get_folder_size_not_connected(self):
        with patch.object(EverythingClient, "_find_dll", return_value="fake.dll"):
            with patch("os.path.exists", return_value=True):
                with patch("ctypes.WinDLL") as mock_windll:
                    mock_windll.return_value = MagicMock()
                    client = EverythingClient()
                    with pytest.raises(RuntimeError, match="未连接到"):
                        client.get_folder_size("C:\\test")


# ============================================================
# Integration Tests (requires Everything running)
# ============================================================

@pytest.fixture
def real_client():
    try:
        client = EverythingClient()
        client.connect("1.5a")
        yield client
        client.disconnect()
    except (FileNotFoundError, EverythingError):
        pytest.skip("Everything is not running")


class TestIntegration:
    def test_connection(self, real_client):
        assert real_client._client is not None

    def test_version(self, real_client):
        version = real_client.version
        assert isinstance(version, str)
        assert len(version) > 0

    def test_full_version(self, real_client):
        version = real_client.full_version
        assert isinstance(version, str)
        parts = version.split(".")
        assert len(parts) == 4

    def test_is_db_loaded(self, real_client):
        assert isinstance(real_client.is_db_loaded(), bool)

    def test_get_target_machine(self, real_client):
        result = real_client.get_target_machine()
        assert isinstance(result, int)

    def test_search_basic(self, real_client):
        results, total = real_client.search("*", max_results=5)
        assert isinstance(results, list)
        assert isinstance(total, int)
        assert total >= 0
        assert len(results) <= 5

    def test_search_with_properties(self, real_client):
        results, total = real_client.search(
            "*",
            properties=[PropertyID.NAME, PropertyID.PATH, PropertyID.SIZE],
            max_results=3,
        )
        assert len(results) <= 3
        for r in results:
            assert r.name is not None
            assert r.full_path is not None

    def test_search_with_sort(self, real_client):
        results, total = real_client.search(
            "*",
            sort=[(PropertyID.NAME, True)],
            max_results=5,
        )
        names = [r.name.lower() for r in results]
        assert names == sorted(names)

    def test_search_match_path(self, real_client, test_data_path):
        results, total = real_client.search(test_data_path, match_path=True, max_results=3)
        assert isinstance(results, list)

    def test_search_match_case(self, real_client):
        results, total = real_client.search("README", match_case=True, max_results=10)
        for r in results:
            assert "README" in r.name

    def test_search_regex(self, real_client):
        results, total = real_client.search(".*\\.txt$", regex=True, max_results=5)
        for r in results:
            assert r.name.lower().endswith(".txt") or r.is_folder

    def test_search_pagination(self, real_client):
        results1, total = real_client.search("*", max_results=5, offset=0)
        results2, _ = real_client.search("*", max_results=5, offset=5)

        if len(results1) == 5 and len(results2) > 0:
            assert results1[0].full_path != results2[0].full_path

    def test_search_result_fields(self, real_client):
        results, _ = real_client.search("*", max_results=1)
        if results:
            r = results[0]
            assert isinstance(r.name, str)
            assert isinstance(r.full_path, str)
            assert isinstance(r.is_folder, bool)
            assert isinstance(r.size, int)

    def test_search_result_times(self, real_client):
        results, _ = real_client.search("*", max_results=1)
        if results:
            r = results[0]
            if r.date_modified > 0:
                assert isinstance(r.modified_time, datetime)
            if r.date_created > 0:
                assert isinstance(r.created_time, datetime)

    def test_search_result_type_str(self, real_client):
        results, _ = real_client.search("*", max_results=5)
        for r in results:
            assert r.type_str in ("File", "Folder")

    def test_search_result_attr_str(self, real_client):
        results, _ = real_client.search("*", max_results=5)
        for r in results:
            assert isinstance(r.attr_str, str)
            assert len(r.attr_str) > 0

    def test_search_result_extension(self, real_client):
        results, _ = real_client.search("*.txt", max_results=5)
        for r in results:
            if not r.is_folder:
                assert r.extension == "txt"

    def test_folder_size(self, real_client):
        results, _ = real_client.search("folder:", match_path=True, max_results=1)
        if results:
            for r in results:
                if r.is_folder:
                    size = real_client.get_folder_size(r.full_path)
                    assert isinstance(size, int)
                    assert size >= 0

    def test_context_manager(self):
        try:
            with EverythingClient() as client:
                client.connect("1.5a")
                results, _ = client.search("*", max_results=1)
                assert isinstance(results, list)
        except (FileNotFoundError, EverythingError):
            pytest.skip("Everything is not running")
