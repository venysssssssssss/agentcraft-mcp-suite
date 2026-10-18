# AgentCraft — instalação em português (Windows e WSL2)

AgentCraft é um conjunto de 14 Agent Skills que utiliza os **13 MCPs nativos da suíte Storytold ArtCraft** no Codex, Claude Code e OpenCode. Ele não instala os aplicativos criativos e não substitui seus executáveis.

> **Status:** v0.1.1, infraestrutura funcional com testes automatizados utilizando MCP simulado. Sem certificação de workflows completos de render/export nos 13 aplicativos reais.

## 1. Instale o CLI do aplicativo desejado

Obtenha os releases oficiais em https://getartcraft.com/apps ou construa o binário a partir do repositório upstream. É necessário localizar `effectcraft-cli` / `effectcraft-cli.exe`, por exemplo. No Windows, o executável pode estar em `C:\Program Files\EffectCraft\effectcraft-cli.exe`.

**WSL2:** prefira executar o Codex/Claude Code/OpenCode e o CLI ArtCraft no mesmo ambiente Linux do WSL. Os executáveis Windows e Linux não compartilham necessariamente GUI, caminhos de arquivos e sessões MCP.

## 2. Instale o AgentCraft (Ubuntu / WSL2)

O Ubuntu com Python 3.12 pode bloquear instalações globais com `externally-managed-environment` (PEP 668). **Não use `--break-system-packages`.**

**Opção recomendada para um CLI reutilizável em vários projetos — pipx:**

```bash
git clone https://github.com/venysssssssssss/agentcraft-mcp-suite.git
cd agentcraft-mcp-suite
sudo apt update && sudo apt install -y pipx
pipx ensurepath
pipx install .
~/.local/bin/agentcraft --version
```

Após `pipx ensurepath`, abra um novo terminal caso `agentcraft` ainda não seja encontrado no `PATH`.

**Alternativa para desenvolvimento e instalação editável — venv:**

```bash
git clone https://github.com/venysssssssssss/agentcraft-mcp-suite.git
cd agentcraft-mcp-suite
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
agentcraft --version
```

Se faltar `ensurepip`, instale `python3-venv` via `apt`. Em sessões posteriores, reative com `source .venv/bin/activate` ou utilize `./.venv/bin/agentcraft` diretamente.

Atenção: o pacote AgentCraft instala as **skills** e configurações, mas não fornece os executáveis ArtCraft. A opção `--target .` configura o repositório atual; indique a pasta de um projeto real para integrar os agentes nele.

## 3. Configure as skills no projeto

Exemplo Linux/WSL:

```bash
agentcraft install --scope project --target ~/meu-projeto --apps effectcraft,filmcraft,vectorcraft --client all
```

PowerShell:

```powershell
$env:AGENTCRAFT_EFFECTCRAFT_CLI = 'C:\Program Files\EffectCraft\effectcraft-cli.exe'
agentcraft install --scope project --target C:\Dev\meu-projeto --apps effectcraft --client all
```

Quando necessário, informe `--bin-dir` (diretório contendo vários CLIs). Use `--strict` para interromper se algum binário selecionado não for encontrado.

## 4. Faça o diagnóstico

```bash
agentcraft doctor --apps effectcraft
agentcraft catalog --apps effectcraft --engine --out docs/generated
```

A execução cria `docs/generated/effectcraft.md` e `docs/generated/effectcraft.json` com os **endpoints e schemas descobertos do binário instalado**. Reinicie seu cliente depois da instalação.

## 5. Como invocar

- Codex: `$agentcraft-effectcraft`.
- Claude Code: `/agentcraft-effectcraft`.
- OpenCode: `/agentcraft-effectcraft`.
- Orquestração entre várias ferramentas: `agentcraft`.

## 6. Cuidados

O MCP executa processos e pode criar/modificar arquivos. Para builds cuja documentação upstream confirma isolamento de diretórios, use `--file-scope workspace` com `--scope project`. Cada app possui limitações de bridge, tokens, modo headless e exportação. Não presuma que endpoints internos tenham IDs idênticos entre versões.

Leia o [README principal](../README.md) para arquitetura, todas as ferramentas, matriz de compatibilidade e troubleshooting.
