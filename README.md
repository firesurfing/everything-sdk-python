# Everything SDK Python

Python wrapper for the Windows Everything SDK (v3). Provides a clean, Pythonic interface to search files and folders using the [Everything](https://www.voidtools.com/) search engine.

[中文文档](README_CN.md)

## Requirements

- Windows OS
- Python 3.7+
- [Everything](https://www.voidtools.com/) application running (v1.5.0.1409a recommended)
- Everything SDK v3 DLL (`Everything3_x64.dll`)

### Getting the SDK

Download SDK v3 from the Everything official forum: [SDK Download](https://www.voidtools.com/forum/viewtopic.php?t=15853&sid=b9bf71c12ae48b33567ab9f8dafdaccc)

Recommended version: **Everything SDK v3** (bundled with Everything 1.5.0.1409a)

### Getting Everything 1.5

Download Everything 1.5 from the official site: [Everything 1.5 Download](https://www.voidtools.com/everything-1.5/)

> Note: This library requires the Everything application to be running.

## Installation

### From source

Download or clone the project repository, then:

```bash
cd everything-sdk-python
pip install -e .
```

### Direct usage

Copy the `src/everything` folder to your project and import directly.

## Quick Start

```python
from everything import EverythingClient, PropertyID, format_size

with EverythingClient() as client:
    client.connect("1.5")
    print(f"Everything version: {client.version}")

    # Search files in a directory
    results, total = client.search('parent:"D:\\\\test"', match_path=True)
    print(f"Found {len(results)} results (total: {total})")

    for r in results:
        if r.is_folder:
            size = client.get_folder_size(r.full_path)
        else:
            size = r.size
        print(f"{r.name}: {format_size(size)}")
```

## API Reference

### EverythingClient

#### `__init__(dll_path=None)`

Initialize the client. DLL discovery order:

1. If `dll_path` is specified, use it directly
2. Check `EVERYTHING_SDK_DIR` environment variable, use `<SDK_DIR>/dll/Everything3_x64.dll`
3. Search all directories in `PATH` environment variable for `Everything3_x64.dll`

#### `connect(version="1.5a")`

Connect to the Everything application. Raises `EverythingError` if connection fails.

#### `disconnect()`

Disconnect from Everything.

#### Context Manager

Supports `with` statement for automatic connection management:

```python
with EverythingClient() as client:
    client.connect("1.5a")
    # ... use client
# automatically disconnected
```

#### `version` (property)

Returns the Everything version string, e.g., `"1.5"`.

#### `full_version` (property)

Returns the full version string including major, minor, revision and build number, e.g., `"1.5.0.1234"`.

#### `is_db_loaded()`

Check if the Everything database has finished loading.

#### `get_target_machine()`

Get the target machine architecture (x86 or x64).

#### `search(search_text, match_path=False, match_case=False, match_whole_word=False, regex=False, properties=None, sort=None, max_results=None, offset=None)`

Execute a search.

- `search_text`: Everything search query (e.g., `parent:"D:\\test"`, `*.txt`, etc.)
- `match_path`: Whether to match against full paths
- `match_case`: Whether to match case
- `match_whole_word`: Whether to match whole words
- `regex`: Whether to use regular expressions
- `properties`: List of `PropertyID` values to retrieve. Defaults to NAME, PATH, SIZE, DATE_CREATED, DATE_MODIFIED, ATTRIBUTES, EXTENSION.
- `sort`: List of `(PropertyID, ascending)` tuples for server-side sorting.
- `max_results`: Maximum number of results to return.
- `offset`: Result offset for pagination.

Returns: `(results_list, total_count)` tuple.

#### `get_folder_size(folder_path)`

Get the actual size of a folder by querying Everything. Returns size in bytes.

### SearchResult

Represents a single search result with the following attributes:

- `name`: File/folder name
- `parent_path`: Parent directory path
- `full_path`: Full file/folder path
- `size`: Size in bytes (for files; folders may show 0 - use `get_folder_size` instead)
- `is_folder`: Boolean indicating if it's a folder
- `date_modified`: FILETIME timestamp
- `date_created`: FILETIME timestamp
- `date_accessed`: FILETIME timestamp
- `attributes`: File attribute bitmask
- `extension`: File extension (without dot)

Properties:
- `type_str`: `"File"` or `"Folder"`
- `modified_time`: Python `datetime` object
- `created_time`: Python `datetime` object
- `accessed_time`: Python `datetime` object
- `attr_str`: Human-readable attribute string (e.g., `"DA"`)

### PropertyID

Constants for all available property IDs:

```python
PropertyID.NAME          # 0
PropertyID.PATH          # 1
PropertyID.SIZE          # 2
PropertyID.EXTENSION     # 3
PropertyID.TYPE          # 4
PropertyID.DATE_MODIFIED # 5
PropertyID.DATE_CREATED  # 6
PropertyID.DATE_ACCESSED # 7
PropertyID.ATTRIBUTES    # 8
# ... and more
```

### format_size(size_bytes)

Format bytes into human-readable string:

```python
format_size(1024)        # "1.00 KB"
format_size(1048576)     # "1.00 MB"
format_size(1073741824)  # "1.00 GB"
```

### EverythingError

Exception raised on SDK errors. Includes `error_code` attribute.

## Advanced Usage

### Custom Properties

```python
results, total = client.search(
    search_text='*.txt',
    properties=[
        PropertyID.NAME,
        PropertyID.PATH,
        PropertyID.SIZE,
        PropertyID.DATE_MODIFIED,
    ]
)
```

### Sorting

```python
# Sort by size ascending, then by name descending
sort = [
    (PropertyID.SIZE, True),
    (PropertyID.NAME, False),
]
results, total = client.search(
    search_text='parent:"D:\\\\test"',
    match_path=True,
    sort=sort,
)
```

### Limit Results

```python
results, total = client.search(
    search_text='*.pdf',
    max_results=10,
)
```

## License

MIT
