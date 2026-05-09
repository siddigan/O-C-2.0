from __future__ import annotations

import argparse
import getpass

from cryptography.fernet import Fernet


def main() -> None:
    parser = argparse.ArgumentParser(description="Encrypt a Firecrawl API key for .env usage.")
    parser.add_argument("--key", help="Existing Fernet key. If omitted, a new one is generated.")
    args = parser.parse_args()

    secret_key = args.key or Fernet.generate_key().decode("utf-8")
    api_key = getpass.getpass("Firecrawl API key: ").strip()
    encrypted = Fernet(secret_key.encode("utf-8")).encrypt(api_key.encode("utf-8")).decode("utf-8")

    print(f"FIRECRAWL_SECRET_KEY={secret_key}")
    print(f"FIRECRAWL_API_KEY_ENCRYPTED={encrypted}")


if __name__ == "__main__":
    main()
