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

## 3. Instale os executáveis ArtCraft no WSL2

As skills já podem estar instaladas, mas o MCP só será registrado quando o executável `*-cli` correspondente estiver disponível.

O repositório contém um instalador opcional para Linux x86_64/aarch64 que baixa os releases **oficiais**, confere SHA-256 e preserva os arquivos auxiliares. Comece por um aplicativo:

```bash
cd ~/BIG/agentcraft-mcp-suite
git pull
bash scripts/install-native-linux.sh effectcraft

agentcraft install --scope project --target . --apps effectcraft --client all --bin-dir "$HOME/.local/bin"
agentcraft doctor --apps effectcraft --bin-dir "$HOME/.local/bin"
```

Depois, para todos os 13 aplicativos:

```bash
df -h /
bash scripts/install-native-linux.sh --all
agentcraft install --scope project --target . --apps all --client all --bin-dir "$HOME/.local/bin"
agentcraft doctor --apps all --bin-dir "$HOME/.local/bin"
```

O download das 13 versões x86_64 consultadas soma aproximadamente **938 MiB compactados**, antes da extração. O tamanho instalado e as dependências do sistema variam; no WSL2 a imagem do disco virtual poderá crescer. O `doctor` confirma apenas o handshake MCP, não a qualidade dos renders.

## 4. Configure as skills no projeto — sem iniciar MCPs

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


### Migração da v0.1.x para v0.2.0 (ativação sob demanda)

```bash
cd ~/BIG/agentcraft-mcp-suite
git pull --ff-only
python -m pip install -e .
agentcraft install --scope project --target . --apps all --client all --bin-dir "$HOME/.local/bin"
agentcraft audit --target .
```

**Zero registros MCP ArtCraft ativos** no OpenCode, Claude Code e Codex após a migração do projeto. Reinicie os três clientes para descarregar processos já inicializados. A auditoria verifica configurações locais e globais comuns, mas não inspeciona plugins externos ou processos internos. Se aparecer um conflito não reconhecido, desative o MCP manualmente e execute a auditoria outra vez.

**Invocação direta:** OpenCode e Claude Code: `/agentcraft-pdfcraft`. Codex: `$agentcraft-pdfcraft`. A skill inicia somente o MCP solicitado via `agentcraft session start pdfcraft`, utiliza `session tools/call` e termina com `session stop`, em comandos de shell. Leia [documentação da arquitetura sob demanda](on-demand.md).

## 5. Faça o diagnóstico

```bash
agentcraft doctor --apps effectcraft
agentcraft catalog --apps effectcraft --engine --out docs/generated
```

A execução cria `docs/generated/effectcraft.md` e `docs/generated/effectcraft.json` com os **endpoints e schemas descobertos do binário instalado**. Reinicie seu cliente depois da instalação.

## 6. Como invocar

- Codex: `$agentcraft-effectcraft`.
- Claude Code: `/agentcraft-effectcraft`.
- OpenCode: `/agentcraft-effectcraft`.
- Orquestração entre várias ferramentas: `agentcraft`.

## 7. Teste real de exportação MP4 (EffectCraft)

Com o projeto nativo `~/BIG/agentcraft-smoke/effectcraft-smoke.ecproj` já salvo e contendo a composição `AgentCraft Smoke Test`:

```bash
sudo apt install -y ffmpeg
python examples/effectcraft_render_e2e.py
```

O exemplo abre o projeto numa **única sessão MCP**, adiciona 1 segundo à fila H.264, aguarda a renderização e valida o MP4 com FFprobe. Não sobrescreve arquivos existentes sem `--overwrite`. Passou em testes unitários com MCP simulado; o render real no WSL2 precisa ser executado e conferido. [Procedimento completo](effectcraft-render-e2e.md).

## 8. Cuidados

O MCP executa processos e pode criar/modificar arquivos. Para builds cuja documentação upstream confirma isolamento de diretórios, use `--file-scope workspace` com `--scope project`. Cada app possui limitações de bridge, tokens, modo headless e exportação. Não presuma que endpoints internos tenham IDs idênticos entre versões.

Leia o [README principal](../README.md) para arquitetura, todas as ferramentas, matriz de compatibilidade e troubleshooting.
