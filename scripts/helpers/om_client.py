"""
OpenMetadata REST API クライアント

使用例:
    client = OMClient("http://localhost:8585")
    client.login("admin", "admin")
    result = client.create_or_update("services/databaseServices", payload)
"""

import base64
import json
from typing import Any
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from urllib.parse import urlencode


class OMClient:
    def __init__(self, base_url: str = "http://localhost:8585"):
        self.api_url = base_url.rstrip("/") + "/api/v1"
        self._token: str | None = None

    # ── 認証 ─────────────────────────────────────────────────────
    def login(self, username: str = "admin", password: str = "admin") -> None:
        payload = {"email": f"{username}@open-metadata.org", "password": password}
        # NoopAuthorizer 構成では Basic 認証ヘッダーで代替
        creds = base64.b64encode(f"{username}:{password}".encode()).decode()
        self._token = f"Basic {creds}"

    def _headers(self, extra: dict | None = None) -> dict:
        h = {"Content-Type": "application/json", "Accept": "application/json"}
        if self._token:
            h["Authorization"] = self._token
        if extra:
            h.update(extra)
        return h

    # ── 汎用 CRUD ────────────────────────────────────────────────
    def _request(self, method: str, path: str, body: Any = None) -> dict:
        url = f"{self.api_url}/{path.lstrip('/')}"
        data = json.dumps(body).encode() if body is not None else None
        req = Request(url, data=data, headers=self._headers(), method=method)
        try:
            with urlopen(req) as resp:
                return json.loads(resp.read())
        except HTTPError as e:
            err_body = e.read().decode()
            raise RuntimeError(
                f"[{method} {url}] HTTP {e.code}: {err_body}"
            ) from e

    def get(self, path: str) -> dict:
        return self._request("GET", path)

    def create_or_update(self, entity_type: str, payload: dict) -> dict:
        """PUT /api/v1/{entity_type} でエンティティを作成または更新する。"""
        return self._request("PUT", entity_type, payload)

    def add_lineage(self, edge: dict) -> dict:
        """PUT /api/v1/lineage でリネージエッジを登録する。"""
        url = f"{self.api_url}/lineage"
        data = json.dumps(edge).encode()
        req = Request(url, data=data, headers=self._headers(), method="PUT")
        try:
            with urlopen(req) as resp:
                body = resp.read()
                return json.loads(body) if body.strip() else {}
        except HTTPError as e:
            err_body = e.read().decode()
            raise RuntimeError(f"[PUT {url}] HTTP {e.code}: {err_body}") from e

    # ── ユーティリティ ────────────────────────────────────────────
    def get_entity_by_fqn(self, entity_type: str, fqn: str, fields: str = "") -> dict | None:
        """FQN でエンティティを取得する。存在しない場合は None を返す。"""
        params = f"?fields={fields}" if fields else ""
        try:
            return self.get(f"{entity_type}/name/{fqn}{params}")
        except RuntimeError as e:
            if "HTTP 404" in str(e):
                return None
            raise

    def get_fqn(self, entity_type: str, fqn: str) -> str:
        """FQN からエンティティ ID を取得する。"""
        entity = self.get_entity_by_fqn(entity_type, fqn)
        if not entity:
            raise ValueError(f"Entity not found: {entity_type}/{fqn}")
        return entity["id"]
