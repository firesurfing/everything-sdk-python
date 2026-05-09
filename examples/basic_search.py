import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from everything import EverythingClient, PropertyID, format_size

with EverythingClient() as client:
    client.connect("1.5a")
    print(f"Everything version: {client.version}")

    results, total = client.search('parent:"D:\\\\test"', match_path=True)
    print(f"Found {len(results)} results (total: {total})")

    for r in results:
        if r.is_folder:
            size = client.get_folder_size(r.full_path)
        else:
            size = r.size
        print(f"{r.name}: {format_size(size)}")
