"""WebSocket/WebUI channel for EasyGS.

This intentionally supports text-only browser chat. Media upload and
``/api/media`` routes are not implemented for EasyGS WebUI.
"""

from __future__ import annotations

import asyncio
import email.utils
import hmac
import http
import json
import mimetypes
import re
import secrets
import ssl
import time
import uuid
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import parse_qs, unquote, urlparse

from loguru import logger
from websockets.asyncio.server import ServerConnection, serve
from websockets.datastructures import Headers
from websockets.exceptions import ConnectionClosed
from websockets.http11 import Request as WsRequest
from websockets.http11 import Response

from easygs.bus.events import OutboundMessage
from easygs.bus.queue import MessageBus
from easygs.channels.base import BaseChannel
from easygs.config.loader import get_config_path, load_config, save_config
from easygs.config.schema import WebSocketConfig

if TYPE_CHECKING:
    from easygs.session.manager import SessionManager


def _strip_trailing_slash(path: str) -> str:
    if len(path) > 1 and path.endswith("/"):
        return path.rstrip("/")
    return path or "/"


def _normalize_config_path(path: str) -> str:
    return _strip_trailing_slash(path)


def _parse_request_path(path_with_query: str) -> tuple[str, dict[str, list[str]]]:
    parsed = urlparse("ws://x" + path_with_query)
    path = _strip_trailing_slash(parsed.path or "/")
    return path, parse_qs(parsed.query)


def _parse_query(path_with_query: str) -> dict[str, list[str]]:
    return _parse_request_path(path_with_query)[1]


def _query_first(query: dict[str, list[str]], key: str) -> str | None:
    values = query.get(key)
    return values[0] if values else None


def _parse_inbound_payload(raw: str) -> str | None:
    text = raw.strip()
    if not text:
        return None
    if text.startswith("{"):
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return text
        if isinstance(data, dict):
            for key in ("content", "text", "message"):
                value = data.get(key)
                if isinstance(value, str) and value.strip():
                    return value
        return None
    return text


_CHAT_ID_RE = re.compile(r"^[A-Za-z0-9_:-]{1,64}$")
_API_KEY_RE = re.compile(r"^[A-Za-z0-9_:.-]{1,128}$")
_LOCALHOSTS = frozenset({"127.0.0.1", "::1", "localhost"})


def _is_valid_chat_id(value: Any) -> bool:
    return isinstance(value, str) and _CHAT_ID_RE.match(value) is not None


def _parse_envelope(raw: str) -> dict[str, Any] | None:
    text = raw.strip()
    if not text.startswith("{"):
        return None
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    return data if isinstance(data.get("type"), str) else None


def _decode_api_key(raw_key: str) -> str | None:
    key = unquote(raw_key)
    if _API_KEY_RE.match(key) is None:
        return None
    return key


def _is_localhost(connection: Any) -> bool:
    addr = getattr(connection, "remote_address", None)
    if not addr:
        return False
    host = addr[0] if isinstance(addr, tuple) else addr
    if not isinstance(host, str):
        return False
    if host.startswith("::ffff:"):
        host = host[7:]
    return host in _LOCALHOSTS


def _http_response(
    body: bytes,
    *,
    status: int = 200,
    content_type: str = "text/plain; charset=utf-8",
    extra_headers: list[tuple[str, str]] | None = None,
) -> Response:
    headers = [
        ("Date", email.utils.formatdate(usegmt=True)),
        ("Connection", "close"),
        ("Content-Length", str(len(body))),
        ("Content-Type", content_type),
    ]
    if extra_headers:
        headers.extend(extra_headers)
    return Response(status, http.HTTPStatus(status).phrase, Headers(headers), body)


def _http_json_response(data: dict[str, Any], *, status: int = 200) -> Response:
    body = json.dumps(data, ensure_ascii=False).encode("utf-8")
    return _http_response(body, status=status, content_type="application/json; charset=utf-8")


def _http_error(status: int, message: str | None = None) -> Response:
    body = (message or http.HTTPStatus(status).phrase).encode("utf-8")
    return _http_response(body, status=status)


def _bearer_token(headers: Any) -> str | None:
    auth = headers.get("Authorization") or headers.get("authorization")
    if auth and auth.lower().startswith("bearer "):
        return auth[7:].strip() or None
    return None


def _is_websocket_upgrade(request: WsRequest) -> bool:
    upgrade = request.headers.get("Upgrade") or request.headers.get("upgrade")
    connection = request.headers.get("Connection") or request.headers.get("connection")
    if not upgrade or "websocket" not in upgrade.lower():
        return False
    if not connection or "upgrade" not in connection.lower():
        return False
    return True


def _read_webui_model_name() -> str | None:
    try:
        model = load_config().agents.defaults.model.strip()
        return model or None
    except Exception as exc:
        logger.debug("webui bootstrap could not load model name: {}", exc)
        return None


def _message_source_from_metadata(metadata: dict[str, Any]) -> dict[str, str] | None:
    workflow_id = str(metadata.get("workflow_id") or "").strip()
    if workflow_id:
        source = {
            "kind": "workflow",
            "id": workflow_id,
        }
        name = str(metadata.get("workflow_name") or "").strip()
        status = str(metadata.get("workflow_status") or "").strip()
        if name:
            source["name"] = name
        if status:
            source["status"] = status
        return source

    return None


class WebSocketChannel(BaseChannel):
    """Run a local WebSocket server and embedded text-only WebUI surface."""

    name = "websocket"

    def __init__(
        self,
        config: Any,
        bus: MessageBus,
        *,
        session_manager: "SessionManager | None" = None,
        static_dist_path: Path | None = None,
    ):
        if isinstance(config, dict):
            config = WebSocketConfig.model_validate(config)
        super().__init__(config, bus)
        self.config: WebSocketConfig = config
        self._session_manager = session_manager
        self._static_dist_path = static_dist_path.resolve() if static_dist_path else None
        self._subs: dict[str, set[Any]] = {}
        self._conn_chats: dict[Any, set[str]] = {}
        self._conn_default: dict[Any, str] = {}
        self._issued_tokens: dict[str, float] = {}
        self._api_tokens: dict[str, float] = {}
        self._stop_event: asyncio.Event | None = None
        self._server_task: asyncio.Task[None] | None = None

    @classmethod
    def default_config(cls) -> dict[str, Any]:
        return WebSocketConfig().model_dump()

    def is_allowed(self, sender_id: str) -> bool:
        allow = self.config.allow_from
        if "*" in allow:
            return True
        return str(sender_id) in allow

    def _expected_path(self) -> str:
        return _normalize_config_path(self.config.path)

    def _attach(self, connection: Any, chat_id: str) -> None:
        self._subs.setdefault(chat_id, set()).add(connection)
        self._conn_chats.setdefault(connection, set()).add(chat_id)

    def _cleanup_connection(self, connection: Any) -> None:
        for chat_id in self._conn_chats.pop(connection, set()):
            subs = self._subs.get(chat_id)
            if subs is None:
                continue
            subs.discard(connection)
            if not subs:
                self._subs.pop(chat_id, None)
        self._conn_default.pop(connection, None)

    async def _send_event(self, connection: Any, event: str, **fields: Any) -> None:
        payload = {"event": event, **fields}
        try:
            await connection.send(json.dumps(payload, ensure_ascii=False))
        except ConnectionClosed:
            self._cleanup_connection(connection)
        except Exception as exc:
            logger.warning("websocket: failed to send {} event: {}", event, exc)

    _MAX_ISSUED_TOKENS = 10_000

    def _purge_expired_issued_tokens(self) -> None:
        now = time.monotonic()
        for token_key, expiry in list(self._issued_tokens.items()):
            if now > expiry:
                self._issued_tokens.pop(token_key, None)

    def _purge_expired_api_tokens(self) -> None:
        now = time.monotonic()
        for token_key, expiry in list(self._api_tokens.items()):
            if now > expiry:
                self._api_tokens.pop(token_key, None)

    def _take_issued_token_if_valid(self, token_value: str | None) -> bool:
        if not token_value:
            return False
        self._purge_expired_issued_tokens()
        expiry = self._issued_tokens.pop(token_value, None)
        return bool(expiry is not None and time.monotonic() <= expiry)

    def _check_api_token(self, request: WsRequest) -> bool:
        self._purge_expired_api_tokens()
        token = _bearer_token(request.headers) or _query_first(_parse_query(request.path), "token")
        if not token:
            return False
        expiry = self._api_tokens.get(token)
        if expiry is None or time.monotonic() > expiry:
            self._api_tokens.pop(token, None)
            return False
        return True

    def _handle_webui_bootstrap(self, connection: Any) -> Response:
        if not _is_localhost(connection):
            return _http_error(403, "webui bootstrap is localhost-only")
        self._purge_expired_issued_tokens()
        self._purge_expired_api_tokens()
        if (
            len(self._issued_tokens) >= self._MAX_ISSUED_TOKENS
            or len(self._api_tokens) >= self._MAX_ISSUED_TOKENS
        ):
            return _http_json_response({"error": "too many outstanding tokens"}, status=429)
        token = f"egwt_{secrets.token_urlsafe(32)}"
        expiry = time.monotonic() + float(self.config.token_ttl_s)
        self._issued_tokens[token] = expiry
        self._api_tokens[token] = expiry
        return _http_json_response({
            "token": token,
            "ws_path": self._expected_path(),
            "expires_in": self.config.token_ttl_s,
            "model_name": _read_webui_model_name(),
        })

    @staticmethod
    def _is_webui_session_key(key: str) -> bool:
        return key.startswith("websocket:")

    def _handle_sessions_list(self, request: WsRequest) -> Response:
        if not self._check_api_token(request):
            return _http_error(401, "Unauthorized")
        if self._session_manager is None:
            return _http_error(503, "session manager unavailable")
        cleaned = [
            {k: v for k, v in session.items() if k != "path"}
            for session in self._session_manager.list_sessions()
            if isinstance(session.get("key"), str) and session["key"].startswith("websocket:")
        ]
        return _http_json_response({"sessions": cleaned})

    def _settings_payload(self, *, requires_restart: bool = False) -> dict[str, Any]:
        from easygs.providers.registry import PROVIDERS

        config = load_config()
        defaults = config.agents.defaults
        provider_name = config.get_provider_name(defaults.model)
        provider = config.get_provider(defaults.model)
        return {
            "agent": {
                "model": defaults.model,
                "provider": "auto",
                "resolved_provider": provider_name,
                "has_api_key": bool(provider and provider.api_key),
            },
            "providers": [{"name": "auto", "label": "Auto"}]
            + [{"name": spec.name, "label": spec.label} for spec in PROVIDERS],
            "runtime": {"config_path": str(get_config_path().expanduser())},
            "requires_restart": requires_restart,
        }

    def _handle_settings(self, request: WsRequest) -> Response:
        if not self._check_api_token(request):
            return _http_error(401, "Unauthorized")
        return _http_json_response(self._settings_payload())

    def _handle_settings_update(self, request: WsRequest) -> Response:
        if not self._check_api_token(request):
            return _http_error(401, "Unauthorized")

        query = _parse_query(request.path)
        config = load_config()
        defaults = config.agents.defaults
        changed = False

        model = _query_first(query, "model")
        if model is not None:
            model = model.strip()
            if not model:
                return _http_error(400, "model is required")
            if defaults.model != model:
                defaults.model = model
                changed = True

        # EasyGS routes providers automatically from the model/configured keys.
        # Accept the field for WebUI compatibility, but do not persist it.
        provider = _query_first(query, "provider")
        if provider is not None and not provider.strip():
            return _http_error(400, "provider is required")

        if changed:
            save_config(config)
        return _http_json_response(self._settings_payload(requires_restart=changed))

    def _handle_session_messages(self, request: WsRequest, key: str) -> Response:
        if not self._check_api_token(request):
            return _http_error(401, "Unauthorized")
        if self._session_manager is None:
            return _http_error(503, "session manager unavailable")
        decoded_key = _decode_api_key(key)
        if decoded_key is None:
            return _http_error(400, "invalid session key")
        if not self._is_webui_session_key(decoded_key):
            return _http_error(404, "session not found")
        data = self._session_manager.read_session_file(decoded_key)
        if data is None:
            return _http_error(404, "session not found")
        return _http_json_response(data)

    def _handle_session_delete(self, request: WsRequest, key: str) -> Response:
        if not self._check_api_token(request):
            return _http_error(401, "Unauthorized")
        if self._session_manager is None:
            return _http_error(503, "session manager unavailable")
        decoded_key = _decode_api_key(key)
        if decoded_key is None:
            return _http_error(400, "invalid session key")
        if not self._is_webui_session_key(decoded_key):
            return _http_error(404, "session not found")
        deleted = self._session_manager.delete_session(decoded_key)
        return _http_json_response({"deleted": deleted})

    def _serve_static(self, request_path: str) -> Response | None:
        assert self._static_dist_path is not None
        rel = request_path.lstrip("/") or "index.html"
        if ".." in rel.split("/") or rel.startswith("/"):
            return _http_error(403, "Forbidden")
        candidate = (self._static_dist_path / rel).resolve()
        try:
            candidate.relative_to(self._static_dist_path)
        except ValueError:
            return _http_error(403, "Forbidden")
        if not candidate.is_file():
            index = self._static_dist_path / "index.html"
            if index.is_file():
                candidate = index
            else:
                return None
        try:
            body = candidate.read_bytes()
        except OSError as exc:
            logger.warning("websocket static: failed to read {}: {}", candidate, exc)
            return _http_error(500, "Internal Server Error")
        content_type, _ = mimetypes.guess_type(candidate.name)
        if content_type is None:
            content_type = "application/octet-stream"
        if content_type.startswith("text/") or content_type in {
            "application/javascript",
            "application/json",
        }:
            content_type = f"{content_type}; charset=utf-8"
        cache = (
            "no-cache"
            if candidate.name == "index.html" or rel.startswith("brand/")
            else "public, max-age=31536000, immutable"
        )
        return _http_response(body, content_type=content_type, extra_headers=[("Cache-Control", cache)])

    async def _dispatch_http(self, connection: Any, request: WsRequest) -> Any:
        got, query = _parse_request_path(request.path)

        if got == "/webui/bootstrap":
            return self._handle_webui_bootstrap(connection)
        if got == "/api/sessions":
            return self._handle_sessions_list(request)
        if got == "/api/settings":
            return self._handle_settings(request)
        if got == "/api/settings/update":
            return self._handle_settings_update(request)

        match = re.match(r"^/api/sessions/([^/]+)/messages$", got)
        if match:
            return self._handle_session_messages(request, match.group(1))
        match = re.match(r"^/api/sessions/([^/]+)/delete$", got)
        if match:
            return self._handle_session_delete(request, match.group(1))

        expected_ws = self._expected_path()
        if got == expected_ws and _is_websocket_upgrade(request):
            client_id = _query_first(query, "client_id") or ""
            if len(client_id) > 128:
                client_id = client_id[:128]
            if not self.is_allowed(client_id):
                return connection.respond(403, "Forbidden")
            return self._authorize_websocket_handshake(connection, query)

        if self._static_dist_path is not None:
            response = self._serve_static(got)
            if response is not None:
                return response

        return connection.respond(404, "Not Found")

    def _authorize_websocket_handshake(self, connection: Any, query: dict[str, list[str]]) -> Any:
        supplied = _query_first(query, "token")
        static_token = self.config.token.strip()
        if static_token:
            if supplied and hmac.compare_digest(supplied, static_token):
                return None
            if supplied and self._take_issued_token_if_valid(supplied):
                return None
            return connection.respond(401, "Unauthorized")
        if self.config.websocket_requires_token:
            if supplied and self._take_issued_token_if_valid(supplied):
                return None
            return connection.respond(401, "Unauthorized")
        if supplied:
            self._take_issued_token_if_valid(supplied)
        return None

    def _build_ssl_context(self) -> ssl.SSLContext | None:
        cert = self.config.ssl_certfile.strip()
        key = self.config.ssl_keyfile.strip()
        if not cert and not key:
            return None
        if not cert or not key:
            raise ValueError("websocket: ssl_certfile and ssl_keyfile must both be set")
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.minimum_version = ssl.TLSVersion.TLSv1_2
        ctx.load_cert_chain(certfile=cert, keyfile=key)
        return ctx

    async def start(self) -> None:
        self._running = True
        self._stop_event = asyncio.Event()
        ssl_context = self._build_ssl_context()
        scheme = "wss" if ssl_context else "ws"

        async def process_request(connection: ServerConnection, request: WsRequest) -> Any:
            return await self._dispatch_http(connection, request)

        async def handler(connection: ServerConnection) -> None:
            await self._connection_loop(connection)

        logger.info(
            "WebSocket/WebUI server listening on {}://{}:{}{}",
            scheme,
            self.config.host,
            self.config.port,
            self.config.path,
        )
        async def runner() -> None:
            async with serve(
                handler,
                self.config.host,
                self.config.port,
                process_request=process_request,
                max_size=self.config.max_message_bytes,
                ping_interval=self.config.ping_interval_s,
                ping_timeout=self.config.ping_timeout_s,
                ssl=ssl_context,
            ):
                assert self._stop_event is not None
                await self._stop_event.wait()

        self._server_task = asyncio.create_task(runner())
        await self._server_task

    async def _connection_loop(self, connection: Any) -> None:
        request = connection.request
        path_part = request.path if request else "/"
        _, query = _parse_request_path(path_part)
        client_id_raw = _query_first(query, "client_id")
        client_id = client_id_raw.strip() if client_id_raw else ""
        if not client_id:
            client_id = f"anon-{uuid.uuid4().hex[:12]}"
        elif len(client_id) > 128:
            client_id = client_id[:128]

        default_chat_id = str(uuid.uuid4())
        try:
            await connection.send(json.dumps({
                "event": "ready",
                "chat_id": default_chat_id,
                "client_id": client_id,
            }, ensure_ascii=False))
            self._conn_default[connection] = default_chat_id
            self._attach(connection, default_chat_id)

            async for raw in connection:
                if isinstance(raw, bytes):
                    try:
                        raw = raw.decode("utf-8")
                    except UnicodeDecodeError:
                        logger.warning("websocket: ignoring non-utf8 binary frame")
                        continue
                envelope = _parse_envelope(raw)
                if envelope is not None:
                    await self._dispatch_envelope(connection, client_id, envelope)
                    continue
                content = _parse_inbound_payload(raw)
                if content is None:
                    continue
                await self._handle_message(
                    sender_id=client_id,
                    chat_id=default_chat_id,
                    content=content,
                    metadata={"remote": getattr(connection, "remote_address", None)},
                )
        except Exception as exc:
            logger.debug("websocket connection ended: {}", exc)
        finally:
            self._cleanup_connection(connection)

    async def _dispatch_envelope(
        self,
        connection: Any,
        client_id: str,
        envelope: dict[str, Any],
    ) -> None:
        message_type = envelope.get("type")
        if message_type == "new_chat":
            new_id = str(uuid.uuid4())
            request_id = envelope.get("request_id")
            extra = {"request_id": request_id} if isinstance(request_id, str) else {}
            self._attach(connection, new_id)
            await self._send_event(connection, "attached", chat_id=new_id, **extra)
            return
        if message_type == "attach":
            chat_id = envelope.get("chat_id")
            if not _is_valid_chat_id(chat_id):
                await self._send_event(connection, "error", detail="invalid chat_id")
                return
            self._attach(connection, chat_id)
            await self._send_event(connection, "attached", chat_id=chat_id)
            return
        if message_type == "message":
            chat_id = envelope.get("chat_id")
            content = envelope.get("content")
            if not _is_valid_chat_id(chat_id):
                await self._send_event(connection, "error", detail="invalid chat_id")
                return
            if not isinstance(content, str) or not content.strip():
                await self._send_event(connection, "error", detail="missing content")
                return
            self._attach(connection, chat_id)
            await self._handle_message(
                sender_id=client_id,
                chat_id=chat_id,
                content=content,
                metadata={"remote": getattr(connection, "remote_address", None)},
            )
            return
        await self._send_event(connection, "error", detail=f"unknown type: {message_type!r}")

    async def stop(self) -> None:
        if not self._running:
            return
        self._running = False
        if self._stop_event:
            self._stop_event.set()
        if self._server_task:
            try:
                await self._server_task
            except Exception as exc:
                logger.warning("websocket: server task error during shutdown: {}", exc)
            self._server_task = None
        self._subs.clear()
        self._conn_chats.clear()
        self._conn_default.clear()
        self._issued_tokens.clear()
        self._api_tokens.clear()

    async def _safe_send_to(self, connection: Any, raw: str) -> None:
        try:
            await connection.send(raw)
        except ConnectionClosed:
            self._cleanup_connection(connection)
        except Exception as exc:
            logger.error("websocket send failed: {}", exc)
            raise

    async def send(self, msg: OutboundMessage) -> None:
        conns = list(self._subs.get(msg.chat_id, ()))
        if not conns:
            logger.warning("websocket: no active subscribers for chat_id={}", msg.chat_id)
            return
        payload: dict[str, Any] = {
            "event": "message",
            "chat_id": msg.chat_id,
            "text": msg.content,
        }
        buttons = getattr(msg, "buttons", None)
        if buttons:
            payload["buttons"] = buttons
            payload["button_prompt"] = msg.content
        if msg.reply_to:
            payload["reply_to"] = msg.reply_to
        if msg.metadata.get("_tool_hint"):
            payload["kind"] = "tool_hint"
        elif msg.metadata.get("_progress"):
            payload["kind"] = "progress"
        source = _message_source_from_metadata(msg.metadata)
        if source:
            payload["source"] = source
        turn_complete = bool(msg.metadata.get("_turn_complete"))
        if turn_complete:
            payload["turn_complete"] = True

        raw = json.dumps(payload, ensure_ascii=False)
        done_raw = json.dumps({
            "event": "stream_end",
            "chat_id": msg.chat_id,
        }, ensure_ascii=False)
        for connection in conns:
            await self._safe_send_to(connection, raw)
            if turn_complete:
                await self._safe_send_to(connection, done_raw)
