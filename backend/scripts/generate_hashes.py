"""Generate bcrypt password hashes for seed data."""

import bcrypt
import json

passwords = {
    "admin123456": bcrypt.hashpw(b"admin123456", bcrypt.gensalt(rounds=12)).decode("utf-8"),
    "finance123456": bcrypt.hashpw(b"finance123456", bcrypt.gensalt(rounds=12)).decode("utf-8"),
    "operator123456": bcrypt.hashpw(b"operator123456", bcrypt.gensalt(rounds=12)).decode("utf-8"),
}

print(json.dumps(passwords, indent=2))
