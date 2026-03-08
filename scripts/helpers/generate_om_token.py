"""
OpenMetadata JWT トークン生成スクリプト

Airflow Lineage Backend に設定する OM JWT トークンを生成し、
.env ファイルに AIRFLOW__LINEAGE__JWT_TOKEN として書き出します。

使用方法:
    python scripts/helpers/generate_om_token.py [--host http://localhost:8585] [--user admin] [--password admin]
    python scripts/helpers/generate_om_token.py --print  # .env に書かず表示のみ

生成後に ingestion コンテナを再起動:
    docker compose up -d ingestion
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from helpers.om_client import OMClient

BASE64_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/="


def _b64encode(s: str) -> str:
    import base64
    return base64.b64encode(s.encode()).decode()


def generate_unlimited_token(host: str, user: str, password: str) -> str:
    """OM の admin ユーザーに無期限 JWT を生成して返す。"""
    import json
    from urllib.request import Request, urlopen

    api_url = host.rstrip("/") + "/api/v1"

    # NoopAuthorizer の場合は認証なしで user ID を取得できる
    # basic 認証の場合はログインを試みる
    try:
        login_payload = json.dumps({"email": f"{user}@open-metadata.org", "password": _b64encode(password)}).encode()
        req = Request(f"{api_url}/users/login", data=login_payload,
                      headers={"Content-Type": "application/json"}, method="POST")
        with urlopen(req) as resp:
            access_token = json.loads(resp.read())["accessToken"]
        auth_header = {"Authorization": f"Bearer {access_token}"}
    except Exception:
        # NoopAuthorizer の場合は認証ヘッダー不要
        auth_header = {}

    # user ID 取得
    req = Request(f"{api_url}/users/name/{user}", headers=auth_header)
    with urlopen(req) as resp:
        user_id = json.loads(resp.read())["id"]

    # Unlimited JWT 生成 (NoopAuthorizer では認証ヘッダーなしで呼び出し可能)
    token_payload = json.dumps({"JWTTokenExpiry": "Unlimited"}).encode()
    req = Request(f"{api_url}/users/generateToken/{user_id}",
                  data=token_payload,
                  headers={"Content-Type": "application/json"},
                  method="PUT")
    with urlopen(req) as resp:
        return json.loads(resp.read())["JWTToken"]


def write_env(jwt_token: str, env_path: Path = Path(".env")) -> None:
    """既存の .env を保持しつつ AIRFLOW__LINEAGE__JWT_TOKEN を更新/追加する。"""
    key = "AIRFLOW__LINEAGE__JWT_TOKEN"
    lines: list[str] = []

    if env_path.exists():
        lines = env_path.read_text().splitlines()

    updated = False
    for i, line in enumerate(lines):
        if line.startswith(f"{key}=") or line.startswith(f"{key} ="):
            lines[i] = f'{key}={jwt_token}'
            updated = True
            break

    if not updated:
        lines.append(f'{key}={jwt_token}')

    env_path.write_text("\n".join(lines) + "\n")
    print(f"✓ {env_path} に {key} を書き込みました")


def main():
    parser = argparse.ArgumentParser(description="OM JWT トークン生成")
    parser.add_argument("--host",     default="http://localhost:8585")
    parser.add_argument("--user",     default="admin")
    parser.add_argument("--password", default="admin")
    parser.add_argument("--print",    action="store_true", help=".env に書かず標準出力に表示のみ")
    args = parser.parse_args()

    print(f"OM ({args.host}) から無期限 JWT を生成中...")
    token = generate_unlimited_token(args.host, args.user, args.password)
    print(f"✓ JWT 生成完了 (length={len(token)})")

    if args.print:
        print(f"\nAIRFLOW__LINEAGE__JWT_TOKEN={token}")
    else:
        env_path = Path(__file__).parent.parent.parent / ".env"
        write_env(token, env_path)
        print("\n次のコマンドで ingestion コンテナを再起動してください:")
        print("  docker compose up -d ingestion")


if __name__ == "__main__":
    main()
