"""Dependency-free newline-delimited MCP stdio client for catalog discovery.

This is designed for Storytold CLI servers (JSON lines over stdio). It is NOT a
universal MCP transport; HTTP/SSE and content-length framing aren't supported.
"""
import json
import os
import queue
import subprocess
import threading
import time
from typing import Any

class MCPError(RuntimeError):
    pass

class MCPProcess:
    def __init__(self, command: list[str], timeout: float = 15.0):
        self.command = command
        self.timeout = timeout
        self._next_id = 0
        self._pending: dict[int, dict[str, Any]] = {}
        self._lines: queue.Queue[bytes | None] = queue.Queue()
        self._errors: list[str] = []
        self.proc: subprocess.Popen | None = None

    def __enter__(self):
        self.proc = subprocess.Popen(self.command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE, bufsize=0)
        threading.Thread(target=self._read_stdout, daemon=True).start()
        threading.Thread(target=self._read_stderr, daemon=True).start()
        try:
            self.initialize()
        except Exception:
            self.__exit__(None, None, None)
            raise
        return self

    def __exit__(self, *_):
        if self.proc:
            if self.proc.stdin:
                self.proc.stdin.close()
            try:
                self.proc.wait(timeout=1)
            except subprocess.TimeoutExpired:
                self.proc.terminate()
                try:
                    self.proc.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    self.proc.kill()
                    self.proc.wait(timeout=1)
            if self.proc.stdout:
                self.proc.stdout.close()
            if self.proc.stderr:
                self.proc.stderr.close()

    def _read_stdout(self):
        assert self.proc and self.proc.stdout
        for line in self.proc.stdout:
            self._lines.put(line)
        self._lines.put(None)

    def _read_stderr(self):
        assert self.proc and self.proc.stderr
        for line in self.proc.stderr:
            if len(self._errors) < 100:
                self._errors.append(line.decode('utf-8', errors='replace').strip())

    def _send(self, message: dict):
        assert self.proc and self.proc.stdin
        payload = (json.dumps(message, ensure_ascii=False, separators=(',', ':')) + '\n').encode('utf-8')
        try:
            self.proc.stdin.write(payload)
            self.proc.stdin.flush()
        except (BrokenPipeError, OSError) as exc:
            raise MCPError(f"MCP server closed stdin: {exc}; stderr={self._errors[-3:]}") from exc

    def notify(self, method: str, params: dict | None = None):
        self._send({'jsonrpc': '2.0', 'method': method, 'params': params or {}})

    def request(self, method: str, params: dict | None = None) -> Any:
        self._next_id += 1
        request_id = self._next_id
        self._send({'jsonrpc': '2.0', 'id': request_id, 'method': method, 'params': params or {}})
        deadline = time.monotonic() + self.timeout
        while time.monotonic() < deadline:
            if request_id in self._pending:
                return self._unpack(self._pending.pop(request_id))
            try:
                line = self._lines.get(timeout=max(0.001, deadline-time.monotonic()))
            except queue.Empty:
                break
            if line is None:
                raise MCPError(f"MCP process exited during {method}; stderr={self._errors[-5:]}")
            try:
                msg = json.loads(line)
            except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                raise MCPError(f"Invalid JSON-RPC line: {line[:150]!r}") from exc
            if not isinstance(msg, dict) or 'id' not in msg:  # notifications
                continue
            if msg['id'] == request_id:
                return self._unpack(msg)
            if isinstance(msg['id'], int):
                self._pending[msg['id']] = msg
        raise MCPError(f"Timed out after {self.timeout}s calling {method}; stderr={self._errors[-5:]}")

    @staticmethod
    def _unpack(message: dict):
        if 'error' in message:
            err = message['error']
            raise MCPError(f"MCP error {err}")
        return message.get('result', {})

    def initialize(self):
        result = self.request('initialize', {
            'protocolVersion': '2025-06-18',
            'capabilities': {},
            'clientInfo': {'name': 'agentcraft-catalog', 'version': '0.1.1'},
        })
        self.notify('notifications/initialized')
        return result

    def list_paginated(self, method: str, field: str) -> list:
        records = []
        cursor = None
        visited = set()
        while True:
            params = {'cursor': cursor} if cursor is not None else {}
            try:
                response = self.request(method, params)
            except MCPError as exc:
                # Older servers may legitimately have no prompts/resources endpoint.
                if '-32601' in str(exc) or 'Method not found' in str(exc) or 'method not found' in str(exc):
                    return []
                raise
            records.extend(response.get(field, []))
            cursor = response.get('nextCursor')
            if not cursor:
                return records
            if cursor in visited:
                raise MCPError(f'Pagination loop in {method}: {cursor}')
            visited.add(cursor)

    def snapshot(self):
        return {
            'tools': self.list_paginated('tools/list', 'tools'),
            'resources': self.list_paginated('resources/list', 'resources'),
            'resourceTemplates': self.list_paginated('resources/templates/list', 'resourceTemplates'),
            'prompts': self.list_paginated('prompts/list', 'prompts'),
        }


def discover_engine_commands(mcp: MCPProcess, tools: list[dict]):
    """Optionally discover the app engine command registry through read-only tools.

    Engine command ids are not top-level MCP method names. Their schema and
    availability may depend on project state; use command_list filters as needed.
    """
    names = {x.get('name') for x in tools}
    for name in ('command_list', 'list_commands', 'commands_list', 'engine_commands'):
        if name not in names:
            continue
        try:
            output = mcp.request('tools/call', {'name': name, 'arguments': {}})
        except MCPError:
            continue
        if output.get('isError'):
            continue
        for part in output.get('content', []):
            if part.get('type') == 'text' and isinstance(part.get('text'),str):
                try:
                    parsed=json.loads(part['text'])
                except json.JSONDecodeError:
                    parsed=part['text']
                return {'sourceTool': name, 'catalog': parsed}
        return {'sourceTool': name, 'catalog': output}
    return {'sourceTool': None, 'catalog': None}
