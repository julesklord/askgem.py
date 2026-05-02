import asyncio
import contextlib
import json
import logging
import os
import subprocess
import sys
from typing import Any

_logger = logging.getLogger("mentask")


class LSPClient:
    """
    Asynchronous LSP client with background reader and request tracking.
    Specialized for Ruff Server.
    """

    def __init__(self, workspace_path: str):
        self.workspace_path = os.path.abspath(workspace_path)
        self.process: asyncio.subprocess.Process | None = None
        self._request_id = 1
        self._pending_requests: dict[int, asyncio.Future] = {}
        self._diagnostics: dict[str, list[dict[str, Any]]] = {}
        self._reader_task: asyncio.Task | None = None
        self._initialized = False

    async def start(self) -> bool:
        """Starts the server and initiates the handshake."""
        try:
            self.process = await asyncio.create_subprocess_exec(
                sys.executable,
                "-m",
                "ruff",
                "server",
                "--preview",
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            # Start background reader
            self._reader_task = asyncio.create_task(self._reader_loop())
            return await self._handshake()
        except Exception as e:
            _logger.error(f"LSP Error: {e}")
            return False

    async def _reader_loop(self):
        """Continuously reads messages from the server's stdout."""
        try:
            while self.process and self.process.stdout and not self.process.stdout.at_eof():
                try:
                    # 1. Read headers
                    content_length = 0
                    while True:
                        line = await self.process.stdout.readline()
                        if not line:
                            break
                        # Strip to handle both \r\n and \n safely
                        clean_line = line.strip()
                        if not clean_line:
                            break
                        line_str = clean_line.decode("utf-8").lower()
                        if line_str.startswith("content-length:"):
                            content_length = int(line_str.split(":")[1].strip())

                    if content_length == 0:
                        continue

                    # 2. Read body
                    body = await self.process.stdout.readexactly(content_length)
                    msg = json.loads(body.decode())
                    self._handle_message(msg)
                except asyncio.IncompleteReadError:
                    break
                except Exception as e:
                    _logger.error(f"LSP Reader Error: {e}")
                    break
        finally:
            # If the loop ends, fail all pending requests to prevent hangs
            _logger.warning("LSP Reader loop terminated. Failing all pending requests.")
            for future in self._pending_requests.values():
                if not future.done():
                    future.set_exception(RuntimeError("LSP server disconnected or crashed."))
            self._pending_requests.clear()

    def _handle_message(self, msg: dict[str, Any]):
        """Dispatches incoming messages to pending requests or notification handlers."""
        if "id" in msg:
            # It's a response to a request
            req_id = msg["id"]
            if req_id in self._pending_requests:
                future = self._pending_requests.pop(req_id)
                if not future.done():
                    future.set_result(msg)
        elif "method" in msg:
            # It's a notification
            method = msg["method"]
            if method == "textDocument/publishDiagnostics":
                params = msg.get("params", {})
                uri = params.get("uri")
                self._diagnostics[uri] = params.get("diagnostics", [])

    async def send_request(self, method: str, params: dict[str, Any], timeout: float = 5.0) -> Any:
        """Sends a request and waits for the response with a timeout."""
        req_id = self._request_id
        self._request_id += 1

        future = asyncio.get_running_loop().create_future()
        self._pending_requests[req_id] = future

        payload = {"jsonrpc": "2.0", "id": req_id, "method": method, "params": params}
        await self._send_payload(payload)

        try:
            return await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            if req_id in self._pending_requests:
                self._pending_requests.pop(req_id)
            raise TimeoutError(f"LSP request '{method}' timed out after {timeout}s") from None

    async def send_notification(self, method: str, params: dict[str, Any]):
        """Sends a one-way notification."""
        payload = {"jsonrpc": "2.0", "method": method, "params": params}
        await self._send_payload(payload)

    async def _send_payload(self, payload: dict[str, Any]):
        if not self.process or not self.process.stdin:
            return
        body = json.dumps(payload).encode()
        header = f"Content-Length: {len(body)}\r\n\r\n".encode()
        self.process.stdin.write(header + body)
        await self.process.stdin.drain()

    async def _handshake(self, timeout: float = 10.0) -> bool:
        """LSP Handshake sequence with timeout."""
        try:
            init_params = {
                "processId": os.getpid(),
                "rootUri": f"file:///{self.workspace_path.replace(os.sep, '/')}",
                "capabilities": {"textDocument": {"publishDiagnostics": {}}},
            }
            # Use a slightly longer timeout for initialize
            response = await self.send_request("initialize", init_params, timeout=timeout)
            if "result" not in response:
                return False

            await self.send_notification("initialized", {})
            self._initialized = True
            return True
        except Exception as e:
            _logger.error(f"LSP Handshake failed: {e}")
            return False

    async def check_file(self, file_path: str, content: str) -> list[dict[str, Any]]:
        """Updates the server version of the file and returns current diagnostics."""
        abs_path = os.path.abspath(file_path).replace(os.sep, "/")
        uri = f"file:///{abs_path}"

        # Clear old diagnostics for this specific check session
        self._diagnostics[uri] = []

        await self.send_notification(
            "textDocument/didOpen",
            {
                "textDocument": {
                    "uri": uri,
                    "languageId": "python",
                    "version": 1,
                    "text": content,
                }
            },
        )

        # Give Ruff a moment to push diagnostics
        await asyncio.sleep(0.5)
        return self._diagnostics.get(uri, [])

    @staticmethod
    def _close_stream_transport(stream: Any) -> None:
        transport = getattr(stream, "_transport", None)
        if transport is not None:
            with contextlib.suppress(Exception):
                transport.close()

    async def stop(self):
        """Cleanly (or forcibly) terminates the LSP server process."""
        process = self.process
        reader_task = self._reader_task

        for future in self._pending_requests.values():
            if not future.done():
                future.cancel()
        self._pending_requests.clear()
        if process:
            try:
                if process.stdin and not process.stdin.is_closing():
                    payload = {"jsonrpc": "2.0", "id": self._request_id, "method": "shutdown", "params": {}}
                    self._request_id += 1
                    with contextlib.suppress(Exception):
                        await self._send_payload(payload)
                    with contextlib.suppress(Exception):
                        await self._send_payload({"jsonrpc": "2.0", "method": "exit", "params": {}})
                    process.stdin.close()
                    with contextlib.suppress(Exception):
                        await process.stdin.wait_closed()

                with contextlib.suppress(ProcessLookupError):
                    process.terminate()
                await asyncio.wait_for(process.wait(), timeout=2.0)
            except (asyncio.TimeoutError, Exception):
                with contextlib.suppress(BaseException):
                    process.kill()
                with contextlib.suppress(BaseException):
                    await process.wait()
            finally:
                self._close_stream_transport(process.stdout)
                self._close_stream_transport(process.stderr)

        if reader_task:
            reader_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await reader_task

        self._initialized = False
        self.process = None
        self._reader_task = None
