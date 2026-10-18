"""Check whether any known ArtCraft MCP remains eagerly enabled in client configs.

Checks filesystem configs; cannot inspect running client internal state or every
external config source/plugin. Restart clients after migrating old registrations.
"""
from __future__ import annotations
import json
import tomllib
from pathlib import Path
from .registry import APPS


def audit(target: Path, home: Path | None = None) -> dict:
    target=target.expanduser().resolve()
    home=home or Path.home()
    paths={
        'opencode': [target/'opencode.json',home/'.config/opencode/opencode.json'],
        'codex': [target/'.codex/config.toml',home/'.codex/config.toml'],
        'claude': [target/'.mcp.json',home/'.claude.json'],
    }
    findings=[]
    inspected=[]
    for client,configs in paths.items():
        for path in configs:
            if not path.is_file():
                continue
            inspected.append(str(path))
            try:
                if client=='codex':
                    obj=tomllib.loads(path.read_text(encoding='utf-8'))
                    entries=obj.get('mcp_servers',{})
                else:
                    obj=json.loads(path.read_text(encoding='utf-8'))
                    entries=obj.get('mcp',{}) if client=='opencode' else obj.get('mcpServers',{})
                if not isinstance(entries,dict):
                    raise ValueError('Expected MCP mapping object')
                for name,item in entries.items():
                    if name in APPS and isinstance(item,dict) and item.get('enabled') is not False:
                        findings.append({'client':client,'file':str(path),'server':name,'reason':'eager registration is present'})
                if client=='opencode' and isinstance(entries.get('servers'),dict):
                    for name,item in entries['servers'].items():
                        if name in APPS and isinstance(item,dict) and item.get('enabled') is not False:
                            findings.append({'client':client,'file':str(path),'server':name,'reason':'legacy eager MCP registration'})
                if client=='claude' and path.name=='.claude.json':
                    projects=obj.get('projects',{})
                    if isinstance(projects,dict):
                        for dirname,cfg in projects.items():
                            if not isinstance(cfg,dict): continue
                            regs=cfg.get('mcpServers',{})
                            if isinstance(regs,dict):
                                for name,item in regs.items():
                                    if name in APPS and isinstance(item,dict) and item.get('enabled') is not False:
                                        findings.append({'client':'claude','file':str(path),'project':dirname,'server':name,
                                                         'reason':'Claude project-scoped registration'})
            except (ValueError, OSError, tomllib.TOMLDecodeError) as exc:
                findings.append({'client':client,'file':str(path),'reason':'unreadable configuration: '+str(exc)})
    return {'ok':not findings,'inspected':inspected,'findings':findings,
            'caveat':'Static config audit; cannot inspect live client state, external plugins, remote policies, or unpublished global config sources. Restart clients.'}
