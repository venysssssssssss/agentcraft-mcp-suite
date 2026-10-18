"""AgentCraft installer, doctor and live MCP endpoint documentation generator."""
from __future__ import annotations
import argparse
import json
import re
import os
import shutil
import sys
import tempfile
import tomllib
from pathlib import Path
from typing import Any

from . import __version__
from .registry import APPS, CraftApp
from .mcp import MCPProcess, MCPError, discover_engine_commands

ROOT = Path(__file__).resolve().parents[1]
if not (ROOT / "skills" / "agentcraft" / "SKILL.md").is_file():
    ROOT = Path(__file__).resolve().parent / "bundled"
SCOPED_APPS = {'photocraft','vectorcraft','pdfcraft','effectcraft','designcraft','figcraft','wordcraft','soundcraft','deckcraft'}


def start_args(app: CraftApp, mode: str, workspace_root: str | None = None,
               photocraft_token_file: str | None = None) -> list[str]:
    result=app.args(mode)
    if mode=='desktop' and app.name=='photocraft':
        if not photocraft_token_file:
            raise ValueError('PhotoCraft bridge requires --photocraft-token-file (documented by upstream)')
        result += ['--control-token-file',str(Path(photocraft_token_file).expanduser().resolve())]
    if mode=='headless' and workspace_root:
        if app.name not in SCOPED_APPS:
            raise ValueError(f'{app.name} folder-confinement flags not verified in current MCP docs')
        root=str(Path(workspace_root).expanduser().resolve())
        result += ['--automation-read-root',root, '--automation-write-root',root]
    return result



def binary_path(app: CraftApp, bin_dir: str | None = None) -> str | None:
    name = app.binary + ('.exe' if os.name == 'nt' else '')
    if bin_dir:
        location = (Path(bin_dir).expanduser() / name).resolve()
        if location.is_file():
            return str(location)
    override=os.environ.get('AGENTCRAFT_' + app.name.upper() + '_CLI')
    if override and Path(override).expanduser().is_file():
        return str(Path(override).expanduser().resolve())
    found=shutil.which(app.binary) or shutil.which(name)
    if found:
        return found
    # Official Windows MSI releases normally install each binary next to its app,
    # outside PATH (e.g. C:\Program Files\EffectCraft\effectcraft-cli.exe).
    if os.name == 'nt':
        folder=app.name[:-5].capitalize()+'Craft'
        for key in ('ProgramFiles', 'ProgramFiles(x86)'):
            base=os.environ.get(key)
            if base:
                candidate=Path(base)/folder/name
                if candidate.is_file():
                    return str(candidate.resolve())
    return None


def selected_apps(value: str) -> list[CraftApp]:
    if value.strip().lower() == 'all':
        return list(APPS.values())
    names = [x.strip().lower() for x in value.split(',')]
    unknown = set(names) - APPS.keys()
    if unknown:
        raise ValueError('Unknown apps: ' + ', '.join(sorted(unknown)))
    return [APPS[k] for k in dict.fromkeys(names)]


def write_atomic(path: Path, value: str, dry_run: bool):
    if dry_run:
        print(f'DRY RUN write {path}')
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix='.agentcraft-')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as dest:
            dest.write(value)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def merge_json(path: Path, key: str, entries: dict, dry_run: bool):
    if path.exists():
        obj = json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(obj, dict):
            raise ValueError(f'Expected JSON object: {path}')
    else:
        obj = {}
    if key in obj and not isinstance(obj[key], dict):
        raise ValueError(f'Expected JSON object for {key} in {path}')
    obj.setdefault(key, {}).update(entries)
    write_atomic(path, json.dumps(obj, ensure_ascii=False, indent=2) + '\n', dry_run)


def toml_quoted(s: str) -> str:
    return json.dumps(s, ensure_ascii=False)


def merge_codex_toml(path: Path, entries: dict[str, tuple[str, list[str]]], dry_run: bool):
    original = path.read_text(encoding='utf-8') if path.exists() else ''
    marker = '# AgentCraft MCP servers (generated; review before use)'
    # Reinstall replaces our generated section; we never touch user-owned sections.
    if marker in original:
        original = original.split(marker, 1)[0].rstrip() + '\n'
    try:
        existing = tomllib.loads(original)
    except Exception as exc:
        raise ValueError(f'Invalid TOML: {path}: {exc}') from exc
    current = existing.get('mcp_servers', {})
    if not isinstance(current, dict):
        raise ValueError('Existing mcp_servers must be a table')
    for key in entries:
        if key in current:
            raise ValueError(f'Codex MCP key already exists: {key}. Remove it before reinstalling to avoid silent overrides.')
    block = '\n# AgentCraft MCP servers (generated; review before use)\n'
    for name, (cmd, args) in entries.items():
        block += f'\n[mcp_servers.{name}]\ncommand = {toml_quoted(cmd)}\n'
        block += 'args = [' + ', '.join(toml_quoted(arg) for arg in args) + ']\n'
        block += 'startup_timeout_sec = 30\ntool_timeout_sec = 120\n'
    write_atomic(path, original.rstrip() + '\n' + block, dry_run)


def _artcraft_binary_match(name: str, binary: str, argv: list) -> bool:
    """Only manage prior AgentCraft-generated native STDIO MCP entries."""
    if not isinstance(binary, str) or not isinstance(argv, list) or not argv:
        return False
    basename = Path(binary).name.lower()
    return basename in {f'{name}-cli', f'{name}-cli.exe'} and argv[0] == 'mcp'


def _cleanup_json_registration(path: Path, client: str, dry_run: bool) -> list[str]:
    if not path.is_file():
        return []
    data=json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(data,dict):
        raise ValueError(f'Invalid client JSON object: {path}')
    key='mcpServers' if client=='claude' else 'mcp'
    registry=data.get(key,{})
    if not isinstance(registry,dict):
        raise ValueError(f'Invalid {key} in {path}')
    removed=[]
    for name in APPS:
        item=registry.get(name)
        if not isinstance(item,dict):
            continue
        if client=='claude':
            candidate=_artcraft_binary_match(name,item.get('command'),item.get('args'))
        else:
            command=item.get('command',[])
            candidate=(item.get('type')=='local' and isinstance(command,list) and len(command)>1
                      and _artcraft_binary_match(name,command[0],command[1:]))
        if not candidate:
            raise ValueError(f'Cannot guarantee on-demand: pre-existing {client} MCP entry {name} '
                             f'in {path} is not recognizably AgentCraft-generated. Disable it manually.')
        del registry[name]
        removed.append(name)
    if client=='opencode' and isinstance(registry.get('servers'),dict):
        legacy=registry['servers']
        for name in list(legacy):
            item=legacy[name]
            command=item.get('command',[]) if isinstance(item,dict) else []
            if name in APPS and isinstance(command,list) and len(command)>1 and _artcraft_binary_match(name,command[0],command[1:]):
                del legacy[name]
                removed.append(name+' (legacy)')
        if not legacy:
            del registry['servers']
    if removed:
        if not registry: del data[key]
        if dry_run: print(f'DRY RUN unregister {client}: {path}: {removed}')
        else: write_atomic(path,json.dumps(data,ensure_ascii=False,indent=2)+'\n',False)
    return removed


def _cleanup_codex_registration(path: Path, dry_run: bool) -> list[str]:
    if not path.is_file():
        return []
    original=path.read_text(encoding='utf-8')
    marker='# AgentCraft MCP servers (generated; review before use)'
    if marker not in original:
        try:
            data=tomllib.loads(original)
        except Exception as exc:
            raise ValueError(f'Invalid Codex TOML {path}: {exc}') from exc
        for name in APPS:
            if name in data.get('mcp_servers',{}):
                raise ValueError(f'Cannot guarantee on-demand: unmanaged Codex MCP {name} exists in {path}')
        return []
    before,tail=original.split(marker,1)
    # Split at TOML headings; only remove generated app sections, preserve custom
    # sections appended by the user after the generated block.
    segments=re.split(r'(?=^\[[^\]\n]+\])',tail,flags=re.MULTILINE)
    remaining=[]
    removed=[]
    for seg in segments:
        mat=re.match(r'^\[mcp_servers\.([a-z]+)\]',seg)
        if mat and mat.group(1) in APPS:
            name=mat.group(1)
            try:
                entry=tomllib.loads(seg)['mcp_servers'][name]
            except Exception as exc:
                raise ValueError(f'Cannot safely migrate invalid Codex MCP config: {path}: {exc}') from exc
            if not _artcraft_binary_match(name,entry.get('command'),entry.get('args')):
                raise ValueError(f'Cannot guarantee on-demand: unrecognized Codex config for {name}')
            removed.append(name)
        elif seg.strip():
            remaining.append(seg)
    cleaned=before.rstrip('\n')+'\n'+''.join(remaining).strip('\n')
    if cleaned.strip(): cleaned=cleaned.rstrip()+'\n'
    if original!=cleaned:
        write_atomic(path,cleaned,dry_run)
    return removed


def install(args):
    """Install skill/command routers only. Native MCPs are never host-registered."""
    apps=selected_apps(args.apps)
    if args.scope=='global' and args.file_scope=='workspace':
        raise ValueError('File scope workspace only works with project scope')
    dest=Path(args.target).expanduser().resolve() if args.scope=='project' else Path.home()
    clients=['codex','claude','opencode'] if args.client=='all' else [args.client]
    if args.strict:
        missing=[a.binary for a in apps if not binary_path(a,args.bin_dir)]
        if missing:
            raise FileNotFoundError('Missing native binaries: '+', '.join(missing))
    # Cleanup is not limited to selected apps: previous `--apps all` may have
    # eagerly registered more MCPs than the current selection. Fail closed for
    # unfamiliar entries rather than incorrectly advertising a guarantee.
    for client in clients:
        if client=='claude' and args.scope=='project':
            removed=_cleanup_json_registration(dest/'.mcp.json','claude',args.dry_run)
        elif client=='opencode':
            cfg=dest/('opencode.json' if args.scope=='project' else '.config/opencode/opencode.json')
            removed=_cleanup_json_registration(cfg,'opencode',args.dry_run)
        elif client=='codex':
            removed=_cleanup_codex_registration(dest/'.codex/config.toml',args.dry_run)
        else:
            removed=[]
        if removed:
            print(f'Unregistered {client} eager MCP entries: {", ".join(removed)}')
    for client in clients:
        if client=='codex':
            skills_dest=dest/'.agents/skills'
        elif client=='claude':
            skills_dest=dest/'.claude/skills'
        else:
            skills_dest=dest/('.opencode/skills' if args.scope=='project' else '.config/opencode/skills')
        for app in apps:
            path=skills_dest/('agentcraft-'+app.name)/'SKILL.md'
            source=ROOT/'skills'/('agentcraft-'+app.name)/'SKILL.md'
            write_atomic(path,source.read_text(encoding='utf-8'),args.dry_run)
        write_atomic(skills_dest/'agentcraft/SKILL.md',(ROOT/'skills/agentcraft/SKILL.md').read_text(encoding='utf-8'),args.dry_run)
        if client in {'claude','opencode'}:
            cmd_dest=dest/('.claude/commands' if client=='claude' else
                           ('.opencode/commands' if args.scope=='project' else '.config/opencode/commands'))
            for app in apps:
                filename=f'agentcraft-{app.name}.md'
                write_atomic(cmd_dest/filename,(ROOT/'commands'/filename).read_text(encoding='utf-8'),args.dry_run)
            write_atomic(cmd_dest/'agentcraft.md',(ROOT/'commands/agentcraft.md').read_text(encoding='utf-8'),args.dry_run)
    available=sum(bool(binary_path(app,args.bin_dir)) for app in apps)
    print(f'Installed {len(apps)} specialist skills + orchestrator for {", ".join(clients)}. '
          f'Native CLIs detected: {available}/{len(apps)}. Client MCP servers registered: 0.')
    print('ON-DEMAND: no ArtCraft MCP starts on client startup. Slash/skill commands use '
          '`agentcraft session start <app>` and stop their temporary session after the task.')
    if args.mode!='headless' or args.file_scope!='none':
        print('INFO: choose --mode and --workspace-root at `agentcraft session start` time.')
    print('Restart client(s) to clear pre-existing in-memory MCP connections.')

def probe(app: CraftApp, args):
    binpath = binary_path(app, args.bin_dir)
    if not binpath:
        raise FileNotFoundError(f'{app.binary} not found on PATH or --bin-dir')
    with MCPProcess([binpath, *start_args(app,args.mode,args.workspace_root,args.photocraft_token_file)], timeout=args.timeout) as mcp:
        snapshot=mcp.snapshot()
        if getattr(args,'engine',False):
            snapshot['engineCommands']=discover_engine_commands(mcp,snapshot['tools'])
        return snapshot


def doctor(args):
    failed = 0
    for app in selected_apps(args.apps):
        try:
            result = probe(app, args)
            counts = ', '.join(f'{key}={len(val)}' for key,val in result.items())
            print(f'OK   {app.name:<12} {counts}')
        except (FileNotFoundError, MCPError, OSError, ValueError) as exc:
            failed += 1
            print(f'FAIL {app.name:<12} {str(exc)[:260]}')
    return 1 if failed else 0


def md_escape(value: Any) -> str:
    return str(value or '').replace('|','\\|').replace('\n', '<newline>')


def describe(app: CraftApp, snapshot: dict[str, list]) -> str:
    md = [f'# {app.name.title()} MCP: live catalog', '',
          '> Generated from the connected binary at runtime, not inferred from website feature claims.', '',
          f'- Official documentation: {app.mcp_docs}',
          f'- Official repository: {app.repository}',
          f'- MCP start: `{app.binary} {" ".join(app.args())}`', '',
          f'## Tools ({len(snapshot["tools"])})', '',
          '| Tool | Description |', '|---|---|']
    for tool in snapshot['tools']:
        md.append(f'| `{md_escape(tool.get("name"))}` | {md_escape(tool.get("description"))[:240]} |')
    for tool in snapshot['tools']:
        md.extend(['', f'### `{tool.get("name")}`', '', tool.get('description','') or 'No description supplied.', '',
                   '**Input schema (as returned by `tools/list`):**', '', '```json',
                   json.dumps(tool.get('inputSchema', {}), ensure_ascii=False, indent=2, sort_keys=True), '```', '',
                   '**Annotations:**', '', '```json', json.dumps(tool.get('annotations', {}), ensure_ascii=False, indent=2), '```'])
    if 'engineCommands' in snapshot:
        md.extend(['','## Engine command catalog', '', f'Source: `{snapshot["engineCommands"]["sourceTool"]}`', '', '```json', json.dumps(snapshot['engineCommands']['catalog'],ensure_ascii=False,indent=2), '```'])
    for key,label in [('resources','Resources'),('resourceTemplates','Resource templates'),('prompts','Prompts')]:
        md.extend(['',f'## {label} ({len(snapshot[key])})','', '```json',json.dumps(snapshot[key],ensure_ascii=False,indent=2),'```'])
    md.append('')
    return '\n'.join(md)


def catalog(args):
    out = Path(args.out).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)
    failed = []
    for app in selected_apps(args.apps):
        try:
            snap = probe(app, args)
            payload = {'app':app.name, 'repository':app.repository, 'source_documentation':app.mcp_docs,
                       'transport': 'stdio-jsonlines', 'mode':args.mode, **snap}
            write_atomic(out / f'{app.name}.json',json.dumps(payload,ensure_ascii=False,indent=2)+'\n',False)
            write_atomic(out / f'{app.name}.md',describe(app,snap),False)
            print(f'OK {app.name}: {len(snap["tools"])} tools -> {out}')
        except (FileNotFoundError,MCPError,OSError,ValueError) as err:
            failed.append(app.name)
            print(f'FAIL {app.name}: {err}')
    return 1 if failed else 0


def call_tool(args):
    app=selected_apps(args.app)
    if len(app)!=1:
        raise ValueError('Only one app allowed in call')
    b=binary_path(app[0],args.bin_dir)
    if not b:
        raise FileNotFoundError(f'{app[0].binary} not found')
    payload=json.loads(Path(args.args_file).read_text(encoding='utf-8')) if args.args_file else json.loads(args.arguments)
    if not isinstance(payload,dict):
        raise ValueError('MCP tool input must be a JSON object')
    with MCPProcess([b,*start_args(app[0],args.mode,args.workspace_root,args.photocraft_token_file)],timeout=args.timeout) as mcp:
        catalog=mcp.list_paginated('tools/list','tools')
        match=next((t for t in catalog if t.get('name')==args.tool),None)
        if not match:
            raise ValueError(f'{app[0].name}: tool {args.tool!r} not listed in live server')
        if not match.get('annotations',{}).get('readOnlyHint',False) and not args.allow_write:
            raise ValueError('Tool is not explicitly read-only. Supply --allow-write after inspecting arguments and effects.')
        result=mcp.request('tools/call',{'name':args.tool,'arguments':payload})
        print(json.dumps(result,ensure_ascii=False,indent=2))
        return int(bool(result.get('isError',False)))


def main(argv: list[str] | None = None) -> int:
    parser=argparse.ArgumentParser(prog='agentcraft',description='AgentCraft multi-agent MCP setup & discovery')
    parser.add_argument('--version', action='version',version=__version__)
    sub=parser.add_subparsers(dest='action',required=True)
    def common(p):
        p.add_argument('--bin-dir',help='directory containing *craft-cli binaries')
        p.add_argument('--mode',choices=['headless','desktop'],default='headless')
        p.add_argument('--timeout',type=float,default=15.0)
        p.add_argument('--photocraft-token-file',help='private control token file for PhotoCraft desktop bridge')
        p.add_argument('--workspace-root',help='optional read/write confined workspace for supported headless apps')
    install_p=sub.add_parser('install',help='install slash/skill routers WITHOUT eager host MCP registrations')
    install_p.add_argument('--scope',choices=['project','global'],default='project')
    install_p.add_argument('--target',default='.',help='project root (project scope)')
    install_p.add_argument('--client',choices=['all','codex','claude','opencode'],default='all')
    install_p.add_argument('--apps',default='all',help='all or comma-separated app names')
    install_p.add_argument('--file-scope',choices=['none','workspace'],default='none',
                           help='add scoped read/write roots for verified headless MCP apps')
    install_p.add_argument('--strict',action='store_true',help='require all selected binaries')
    install_p.add_argument('--dry-run',action='store_true')
    common(install_p)
    diag=sub.add_parser('doctor',help='read-only MCP handshake and endpoints discovery')
    diag.add_argument('--apps',default='all')
    common(diag)
    cat=sub.add_parser('catalog',help='generate exhaustive runtime MCP JSON Schemas + Markdown')
    cat.add_argument('--apps',default='all')
    cat.add_argument('--out',default='docs/generated')
    cat.add_argument('--engine',action='store_true',help='add read-only engine command registry where available')
    common(cat)
    call=sub.add_parser('call',help='call one actual advertised MCP tool by name')
    call.add_argument('app',choices=list(APPS))
    call.add_argument('tool')
    call.add_argument('--arguments',default='{}')
    call.add_argument('--args-file')
    call.add_argument('--allow-write',action='store_true')
    common(call)
    auditp=sub.add_parser('audit',help='detect remaining eager ArtCraft MCP registrations')
    auditp.add_argument('--target',default='.')
    sess=sub.add_parser('session',help='manage explicit on-demand, persistent native MCP sessions')
    sess.add_argument('session_args',nargs=argparse.REMAINDER)
    args=parser.parse_args(argv)
    try:
        if args.action=='audit':
            from .audit import audit
            result=audit(Path(args.target))
            print(json.dumps(result,ensure_ascii=False,indent=2))
            return 0 if result['ok'] else 1
        if args.action=='session':
            from .session import main as session_main
            return session_main(args.session_args)
        if args.action=='install':
            install(args)
            return 0
        if args.action=='doctor':
            return doctor(args)
        if args.action=='catalog':
            return catalog(args)
        if args.action=='call':
            return call_tool(args)
    except (ValueError,FileNotFoundError,MCPError,PermissionError) as exc:
        print(f'ERROR: {exc}',file=sys.stderr)
        return 2
    return 1
