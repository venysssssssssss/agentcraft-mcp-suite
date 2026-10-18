param(
    [string]$RepositoryName = 'agentcraft-mcp-suite',
    [string]$ExpectedOwner = 'venysssssssssss'
)
$ErrorActionPreference = 'Stop'
if (-not (Get-Command gh -ErrorAction SilentlyContinue)) { throw 'GitHub CLI (gh) is required' }
if (-not (Get-Command git -ErrorAction SilentlyContinue)) { throw 'git is required' }
gh auth status
if ($LASTEXITCODE -ne 0) { throw 'Authenticate with gh auth login' }
$CurrentOwner = (gh api user --jq .login).Trim()
if ($LASTEXITCODE -ne 0) { throw 'Could not determine active GitHub account' }
if ($CurrentOwner -ine $ExpectedOwner) { throw "Refusing to publish as $CurrentOwner (expected $ExpectedOwner)" }
gh repo view "$ExpectedOwner/$RepositoryName" *> $null
if ($LASTEXITCODE -eq 0) { throw "Repository $ExpectedOwner/$RepositoryName already exists; refusing to overwrite" }
if (-not (Test-Path .git)) { git init -b main }
git var GIT_AUTHOR_IDENT *> $null
if ($LASTEXITCODE -ne 0) { throw 'Configure Git author first: user.name and user.email' }
if (git status --porcelain) {
    git add README.md LICENSE pyproject.toml .gitignore agentcraft skills commands docs tests scripts .github
    git commit -m 'feat: publish AgentCraft MCP Suite multi-client integration'
    if ($LASTEXITCODE -ne 0) { throw 'Git commit failed' }
}
gh repo create "$ExpectedOwner/$RepositoryName" --public --source . --remote origin --push
if ($LASTEXITCODE -ne 0) { throw 'GitHub publication failed' }
Write-Host "Published: https://github.com/$ExpectedOwner/$RepositoryName"
