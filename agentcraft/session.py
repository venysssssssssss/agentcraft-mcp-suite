"""On-demand MCP sessions, without a host-wide MCP registration.

A selected slash-command/skill can start one local, authenticated session, call
its discovered tools repeatedly, and stop it. No ArtCraft CLI is launched while
Codex/Claude/OpenCode initializes. Sessions have an idle expiration failsafe.
"""
from __future__ import annotations

import argparse
import json
import os
import secrets
import socket
import socketserver
import subprocess
import sys
import threading
import time
from pathlib import Path

from .mcp import MCPProcess
from .registry import APPS

MAX_MESSAGE = 32 * 1024 * 1024


def session_dir() -> Path:
    path = Path(os.environ.get('AGENTCRAFT_SESSION_DIR', str(Path.home()/'.cache/agentcraft/sessions'))).expanduser().resolve()
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    if os.name != 'nt':
        path.chmod(0o700)
    return path


def metadata_path(sid: str) -> Path:
    if len(sid) != 24 or any(c not in '0123456789abcdef' for c in sid):
        raise ValueError('Invalid session id')
    return session_dir()/(sid+'.json')


def store_metadata(path: Path, data: dict):
    raw = json.dumps(data, ensure_ascii=False, indent=2).encode('utf-8')
    fd = os.open(str(path), os.O_WRONLY|os.O_CREAT|os.O_EXCL, 0o600)
    with os.fdopen(fd, 'wb') as file:
        file.write(raw)


def read_metadata(sid: str) -> dict:
    file = metadata_path(sid)
    if not file.is_file():
        raise FileNotFoundError(f'No active AgentCraft session {sid}; start it with `agentcraft session start <app>`')
    if os.name != 'nt' and file.stat().st_mode & 0o077:
        raise PermissionError(f'Session credentials have unsafe permissions: {file}')
    return json.loads(file.read_text(encoding='utf-8'))


def rpc(meta: dict, action: str, *, timeout: float = 60.0, **kwargs):
    with socket.create_connection(('127.0.0.1', meta['port']), timeout=min(timeout,15)) as conn:
        conn.settimeout(timeout)
        payload=json.dumps({'token':meta['token'],'action':action,**kwargs},ensure_ascii=False).encode('utf-8')+b'\n'
        conn.sendall(payload)
        with conn.makefile('rb') as file:
            line=file.readline(MAX_MESSAGE+1)
        if not line or len(line)>MAX_MESSAGE:
            raise RuntimeError('AgentCraft session closed connection or returned oversized data')
    result=json.loads(line)
    if not result.get('ok'):
        raise RuntimeError(result.get('error','Unknown AgentCraft session error'))
    return result.get('result',{})


def client_request(sid: str, action: str, *, timeout: float = 120.0, **kwargs):
    meta=read_metadata(sid)
    try:
        return rpc(meta,action,timeout=timeout,**kwargs)
    except (OSError,TimeoutError) as exc:
        raise RuntimeError(f'Session {sid} is unavailable: {exc}; start a new session if it expired') from exc


class LocalServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = False
    daemon_threads = True

    def __init__(self, address, mcp, app: str, token: str, idle: float):
        super().__init__(address, SessionHandler)
        self.mcp=mcp
        self.app=app
        self.token=token
        self.idle=idle
        self.last_activity=time.monotonic()
        self.lock=threading.Lock()
        self.stopping=False


class SessionHandler(socketserver.StreamRequestHandler):
    def handle(self):
        server: LocalServer = self.server
        try:
            raw=self.rfile.readline(MAX_MESSAGE+1)
            if not raw or len(raw)>MAX_MESSAGE:
                raise ValueError('Missing or oversized request')
            message=json.loads(raw)
            if not secrets.compare_digest(str(message.get('token','')),server.token):
                raise PermissionError('Invalid session token')
            action=message.get('action')
            with server.lock:
                server.last_activity=time.monotonic()
                if action=='ping':
                    result={'app':server.app,'pid':os.getpid(),'idle_seconds':server.idle}
                elif action=='tools':
                    available=server.mcp.list_paginated('tools/list','tools')
                    match=message.get('filter','').casefold()
                    available=[item for item in available if match in item.get('name','').casefold() or match in item.get('description','').casefold()]
                    if not message.get('details',False):
                        result=[{'name':item.get('name'),'description':item.get('description','')[:240],
                                 'readOnlyHint':item.get('annotations',{}).get('readOnlyHint',False)} for item in available]
                    else:
                        result=available
                elif action=='call':
                    tool=message['tool']
                    args=message.get('arguments',{})
                    if not isinstance(args,dict):
                        raise ValueError('Tool arguments must be a JSON object')
                    available=server.mcp.list_paginated('tools/list','tools')
                    match=next((t for t in available if t.get('name')==tool),None)
                    if match is None:
                        raise ValueError(f'Tool {tool!r} is not exposed by {server.app}')
                    if not match.get('annotations',{}).get('readOnlyHint',False) and not message.get('allow_write',False):
                        raise PermissionError('Potentially mutating MCP tool: pass --allow-write after review')
                    result=server.mcp.request('tools/call',{'name':tool,'arguments':args})
                elif action=='stop':
                    result={'stopping':True,'app':server.app}
                    server.stopping=True
                    threading.Thread(target=server.shutdown,daemon=True).start()
                else:
                    raise ValueError(f'Unsupported session action {action!r}')
                server.last_activity=time.monotonic()
            response={'ok':True,'result':result}
        except Exception as exc:
            response={'ok':False,'error':str(exc)}
        self.wfile.write(json.dumps(response,ensure_ascii=False).encode('utf-8')+b'\n')
        self.wfile.flush()


def serve(args):
    from .cli import start_args
    sid=args.sid
    meta_file=metadata_path(sid)
    binary=Path(args.binary).expanduser().resolve()
    if not binary.is_file():
        raise FileNotFoundError(binary)
    app=APPS[args.app]
    cmd=[str(binary),*start_args(app,args.mode,args.workspace_root,args.photocraft_token_file)]
    args.token=os.environ.pop('AGENTCRAFT_EPHEMERAL_TOKEN',None)
    if not args.token:
        raise RuntimeError('Missing ephemeral session credential')
    try:
        with MCPProcess(cmd,timeout=args.timeout) as mcp:
            with LocalServer(('127.0.0.1',0),mcp,args.app,args.token,args.idle_seconds) as server:
                # The secret and local port are only written after MCP initialize succeeds.
                store_metadata(meta_file,{'app':args.app,'port':server.server_address[1],
                       'token':args.token,'pid':os.getpid(),'created':time.time(),
                       'binary':str(binary)})
                def expire():
                    while not server.stopping:
                        time.sleep(1)
                        if server.lock.acquire(blocking=False):
                            try:
                                if time.monotonic()-server.last_activity > server.idle:
                                    server.stopping=True
                                    threading.Thread(target=server.shutdown,daemon=True).start()
                                    return
                            finally:
                                server.lock.release()
                threading.Thread(target=expire,daemon=True).start()
                server.serve_forever(poll_interval=0.2)
    finally:
        try:
            meta_file.unlink(missing_ok=True)
        except OSError:
            pass


def start(args):
    from .cli import binary_path
    app=APPS[args.app]
    binary=binary_path(app,args.bin_dir)
    if not binary:
        raise FileNotFoundError(f'Missing {app.binary}; install the official native ArtCraft CLI first')
    if args.idle_seconds < 30:
        raise ValueError('--idle-seconds must be at least 30')
    sid=secrets.token_hex(12)
    token=secrets.token_hex(32)
    command=[sys.executable,'-m','agentcraft.session','_serve','--sid',sid,
             '--app',args.app,'--binary',binary,'--mode',args.mode,
             '--timeout',str(args.timeout),'--idle-seconds',str(args.idle_seconds)]
    if args.workspace_root:
        command+=['--workspace-root',str(Path(args.workspace_root).expanduser().resolve())]
    if args.photocraft_token_file:
        command+=['--photocraft-token-file',args.photocraft_token_file]
    log=session_dir()/(sid+'.log')
    env=os.environ.copy()
    env['AGENTCRAFT_EPHEMERAL_TOKEN']=token
    with log.open('wb') as out:
        proc=subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=out,stderr=subprocess.STDOUT,
                              close_fds=True,start_new_session=(os.name != 'nt'),env=env,
                              creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0) if os.name=='nt' else 0)
    # Reap detached child without warning or leaving a Popen zombie in this process.
    threading.Thread(target=proc.wait,daemon=True).start()
    deadline=time.monotonic()+20
    while time.monotonic()<deadline:
        if proc.poll() is not None:
            raise RuntimeError(f'MCP startup failed (exit={proc.returncode}): {log.read_text(encoding="utf-8",errors="replace")[-3000:]}')
        file=metadata_path(sid)
        if file.exists():
            try:
                result=client_request(sid,'ping',timeout=3)
                return {'session':sid,'app':args.app,'pid':result['pid'],
                        'idle_seconds':args.idle_seconds,'log':str(log)}
            except (OSError,RuntimeError,ValueError):
                pass
        time.sleep(0.1)
    proc.terminate()
    raise RuntimeError(f'MCP did not initialize in 20s. Check {log}')


def main(argv=None):
    p=argparse.ArgumentParser(prog='agentcraft session')
    sub=p.add_subparsers(dest='operation',required=True)
    startp=sub.add_parser('start',help='start one authenticated, temporary native MCP subprocess')
    startp.add_argument('app',choices=list(APPS))
    startp.add_argument('--bin-dir')
    startp.add_argument('--mode',choices=['headless','desktop'],default='headless')
    startp.add_argument('--workspace-root',help='confine read/write to this folder on supported apps')
    startp.add_argument('--photocraft-token-file')
    startp.add_argument('--timeout',type=float,default=1800)
    startp.add_argument('--idle-seconds',type=float,default=600)
    for name in ('status','tools','call','stop'):
        a=sub.add_parser(name)
        a.add_argument('session')
        if name=='tools':
            a.add_argument('--filter',default='')
            a.add_argument('--details',action='store_true')
        if name=='call':
            a.add_argument('tool')
            a.add_argument('--arguments',default='{}')
            a.add_argument('--args-file')
            a.add_argument('--allow-write',action='store_true')
            a.add_argument('--timeout',type=float,default=1800)
            a.add_argument('--output',type=Path,help='save complete JSON response to an explicit path')
    serv=sub.add_parser('_serve',help=argparse.SUPPRESS)
    for flag in ('sid','app','binary','mode'):
        serv.add_argument('--'+flag,required=True)
    serv.add_argument('--timeout',type=float,required=True)
    serv.add_argument('--idle-seconds',type=float,required=True)
    serv.add_argument('--workspace-root')
    serv.add_argument('--photocraft-token-file')
    a=p.parse_args(argv)
    try:
        if a.operation=='_serve':
            serve(a)
            return 0
        if a.operation=='start':
            result=start(a)
        elif a.operation=='status':
            result=client_request(a.session,'ping',timeout=8)
        elif a.operation=='tools':
            result=client_request(a.session,'tools',filter=a.filter,details=a.details)
        elif a.operation=='call':
            args=json.loads(a.args_file and Path(a.args_file).read_text(encoding='utf-8') or a.arguments)
            result=client_request(a.session,'call',tool=a.tool,arguments=args,allow_write=a.allow_write,timeout=a.timeout)
        else:
            result=client_request(a.session,'stop',timeout=10)
        output=json.dumps(result,ensure_ascii=False,indent=2)
        if a.operation=='call' and a.output:
            a.output.expanduser().resolve().parent.mkdir(parents=True,exist_ok=True)
            a.output.expanduser().resolve().write_text(output+'\n',encoding='utf-8')
            print(f'Wrote: {a.output}')
        else:
            print(output)
        return int(a.operation=='call' and isinstance(result,dict) and result.get('isError',False))
    except (OSError,ValueError,RuntimeError,PermissionError,TimeoutError) as exc:
        print(f'ERROR: {exc}',file=sys.stderr)
        return 2

if __name__=='__main__':
    raise SystemExit(main())
