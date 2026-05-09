# Everything SDK Python

Windows Everything SDK (v3) 的 Python 封装库。提供简洁的 Python 接口，通过 [Everything](https://www.voidtools.com/) 搜索引擎快速查找文件和文件夹。

[English Documentation](README.md)

## 环境要求

- Windows 操作系统
- Python 3.7+
- [Everything](https://www.voidtools.com/) 应用程序正在运行（推荐 v1.5.0.1409a）
- Everything SDK v3 DLL（`Everything3_x64.dll`）

### 获取 SDK

从 Everything 官方论坛下载 SDK v3：[SDK 下载](https://www.voidtools.com/forum/viewtopic.php?t=15853&sid=b9bf71c12ae48b33567ab9f8dafdaccc)

当前推荐版本：**Everything SDK v3**（随 Everything 1.5.0.1409a 发布）

### 获取 Everything 1.5

从 Everything 官网下载：[Everything 1.5 下载](https://www.voidtools.com/everything-1.5/)

> 注意：本库需要 Everything 应用程序正在运行才能使用。

## 安装

### 从源码安装

下载或克隆项目仓库，然后：

```bash
cd everything-sdk-python
pip install -e .
```

### 直接使用

将 `src/everything` 文件夹复制到你的项目中，然后直接导入使用。

## 快速开始

```python
from everything import EverythingClient, PropertyID, format_size

with EverythingClient() as client:
    client.connect("1.5a")
    print(f"Everything 版本: {client.version}")

    # 搜索目录中的文件
    results, total = client.search('parent:"D:\\\\test"', match_path=True)
    print(f"找到 {len(results)} 个结果 (总计: {total})")

    for r in results:
        if r.is_folder:
            size = client.get_folder_size(r.full_path)
        else:
            size = r.size
        print(f"{r.name}: {format_size(size)}")
```

## API 参考

### EverythingClient

#### `__init__(dll_path=None)`

初始化客户端。DLL 查找顺序：

1. 如果指定了 `dll_path`，直接使用该路径
2. 检查 `EVERYTHING_SDK_DIR` 环境变量，使用 `<SDK_DIR>/dll/Everything3_x64.dll`
3. 搜索 `PATH` 环境变量中的所有目录，查找 `Everything3_x64.dll`

#### `connect(version="1.5a")`

连接到 Everything 应用程序。如果连接失败会抛出 `EverythingError`。

#### `disconnect()`

断开与 Everything 的连接。

#### 上下文管理器

支持 `with` 语句自动管理连接：

```python
with EverythingClient() as client:
    client.connect("1.5a")
    # ... 使用 client
# 自动断开连接
```

#### `version` (属性)

返回 Everything 版本字符串，例如 `"1.5"`。

#### `full_version` (属性)

返回完整版本号，包含主版本、次版本、修订号和构建号，例如 `"1.5.0.1234"`。

#### `is_db_loaded()`

检查 Everything 数据库是否已加载完成。

#### `get_target_machine()`

获取目标机器架构（x86 或 x64）。

#### `search(search_text, match_path=False, match_case=False, match_whole_word=False, regex=False, properties=None, sort=None, max_results=None, offset=None)`

执行搜索。

- `search_text`: Everything 搜索查询（例如 `parent:"D:\\test"`、`*.txt` 等）
- `match_path`: 是否匹配完整路径
- `match_case`: 是否区分大小写
- `match_whole_word`: 是否匹配整个单词
- `regex`: 是否使用正则表达式
- `properties`: 要获取的 `PropertyID` 列表。默认为 NAME、PATH、SIZE、DATE_CREATED、DATE_MODIFIED、ATTRIBUTES、EXTENSION。
- `sort`: `(PropertyID, ascending)` 元组列表，用于服务端排序。
- `max_results`: 返回的最大结果数。
- `offset`: 结果偏移量（分页用）。

返回: `(results_list, total_count)` 元组。

#### `get_folder_size(folder_path)`

通过查询 Everything 获取文件夹的实际大小。返回字节数。

### SearchResult

表示单个搜索结果，包含以下属性：

- `name`: 文件/文件夹名称
- `parent_path`: 父目录路径
- `full_path`: 完整文件/文件夹路径
- `size`: 大小（字节）（文件的实际大小；文件夹通常为 0，请使用 `get_folder_size`）
- `is_folder`: 是否为文件夹
- `date_modified`: 修改时间（FILETIME 格式）
- `date_created`: 创建时间（FILETIME 格式）
- `date_accessed`: 访问时间（FILETIME 格式）
- `attributes`: 文件属性位掩码
- `extension`: 文件扩展名（不含点）

属性方法：
- `type_str`: `"文件"` 或 `"文件夹"`
- `modified_time`: Python `datetime` 对象
- `created_time`: Python `datetime` 对象
- `accessed_time`: Python `datetime` 对象
- `attr_str`: 人类可读的属性字符串（例如 `"DA"`）

### PropertyID

所有可用属性 ID 的常量：

```python
PropertyID.NAME          # 0  文件名
PropertyID.PATH          # 1  路径
PropertyID.SIZE          # 2  大小
PropertyID.EXTENSION     # 3  扩展名
PropertyID.TYPE          # 4  类型
PropertyID.DATE_MODIFIED # 5  修改时间
PropertyID.DATE_CREATED  # 6  创建时间
PropertyID.DATE_ACCESSED # 7  访问时间
PropertyID.ATTRIBUTES    # 8  属性
# ... 更多属性
```

### format_size(size_bytes)

将字节数格式化为人类可读的字符串：

```python
format_size(1024)        # "1.00 KB"
format_size(1048576)     # "1.00 MB"
format_size(1073741824)  # "1.00 GB"
```

### EverythingError

SDK 错误异常。包含 `error_code` 属性。

## 高级用法

### 自定义属性

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

### 排序

```python
# 按大小升序，再按名称降序
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

### 限制结果数量

```python
results, total = client.search(
    search_text='*.pdf',
    max_results=10,
)
```

## 许可证

MIT
