#!/usr/bin/env python3
"""检查encryption测试中的key长度"""

# 测试相同的key字符串
key1 = "test_master_key_32_characters!!"
print(f"Key 1: {repr(key1)}")
print(f"Length 1: {len(key1)}")
print()

# 从测试文件中读取
with open("tests/unit/security/test_encryption.py", "r", encoding="utf-8") as f:
    lines = f.readlines()
    for i, line in enumerate(lines, 1):
        if "master_key = " in line and "test_master_key_32" in line:
            print(f"Line {i}: {line.rstrip()}")
            # Extract the string value
            import re
            match = re.search(r'"([^"]+)"', line)
            if match:
                key_from_file = match.group(1)
                print(f"Key from file: {repr(key_from_file)}")
                print(f"Length from file: {len(key_from_file)}")
                print(f"Bytes: {key_from_file.encode('utf-8')}")
                print(f"Byte length: {len(key_from_file.encode('utf-8'))}")
                print()
                break
