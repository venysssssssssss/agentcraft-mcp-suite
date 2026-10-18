#!/usr/bin/env bash
# Publication guard: never accidentally publish under the user's corporate GitHub identity.
set -euo pipefail
REPO_NAME="${1:-agentcraft-mcp-suite}"
EXPECTED_OWNER="${2:-venysssssssssss}"
command -v gh >/dev/null || { echo 'Install GitHub CLI: https://cli.github.com/'; exit 1; }
command -v git >/dev/null || { echo 'Git is required'; exit 1; }
gh auth status >/dev/null
CURRENT_OWNER="$(gh api user --jq .login)"
if [[ "${CURRENT_OWNER,,}" != "${EXPECTED_OWNER,,}" ]]; then
  echo "Refusing to publish: active gh account '$CURRENT_OWNER' != required '$EXPECTED_OWNER'" >&2
  exit 2
fi
if gh repo view "$EXPECTED_OWNER/$REPO_NAME" >/dev/null 2>&1; then
  echo "Refusing to overwrite existing repository $EXPECTED_OWNER/$REPO_NAME" >&2
  exit 3
fi
if [[ ! -d .git ]]; then git init -b main; fi
git var GIT_AUTHOR_IDENT >/dev/null
if [[ -n "$(git status --porcelain)" ]]; then
  git add README.md LICENSE pyproject.toml .gitignore agentcraft skills commands docs tests scripts .github
  git commit -m 'feat: publish AgentCraft MCP Suite multi-client integration'
fi
gh repo create "$EXPECTED_OWNER/$REPO_NAME" --public --source . --remote origin --push
printf 'Published: https://github.com/%s/%s\n' "$EXPECTED_OWNER" "$REPO_NAME"
