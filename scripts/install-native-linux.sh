#!/usr/bin/env bash
# Install official Linux ArtCraft release trees, without system-wide package changes.
# Asset names and SHA-256 values are discovered from the GitHub Releases API.
set -Eeuo pipefail

APPS=(photocraft vectorcraft filmcraft lightcraft pdfcraft effectcraft designcraft figcraft wordcraft soundcraft deckcraft cadcraft gridcraft)
PREFIX="${AGENTCRAFT_NATIVE_PREFIX:-$HOME/.local/share/agentcraft/native}"
BIN_DIR="${AGENTCRAFT_NATIVE_BIN_DIR:-$HOME/.local/bin}"
SELECTED=()

usage() {
  cat <<'HELP'
Install official Storytold ArtCraft Linux release CLIs for AgentCraft MCP.

Usage:
  bash scripts/install-native-linux.sh effectcraft
  bash scripts/install-native-linux.sh effectcraft filmcraft vectorcraft
  bash scripts/install-native-linux.sh --all

Requires: curl, python3, tar, sha256sum. Supports Linux x86_64 / aarch64.
Installs app release trees under ~/.local/share/agentcraft/native and creates
CLI symlinks under ~/.local/bin. Does not use sudo or modify system Python.
It does not guarantee availability of optional OS shared libraries; use
'agentcraft doctor --apps ...' after installation to verify the MCP handshake.

Environment variables:
  AGENTCRAFT_NATIVE_PREFIX  Alternative installation root
  AGENTCRAFT_NATIVE_BIN_DIR Alternative CLI symlink directory
HELP
}

if [[ $# -eq 0 ]]; then usage; exit 2; fi
if [[ ${1:-} == "--help" || ${1:-} == "-h" ]]; then usage; exit 0; fi
if [[ ${1:-} == "--all" ]]; then
  if [[ $# -ne 1 ]]; then echo '--all cannot be combined with names' >&2; exit 2; fi
  SELECTED=("${APPS[@]}")
else
  for app in "$@"; do
    known=0
    for candidate in "${APPS[@]}"; do
      if [[ "$candidate" == "$app" ]]; then known=1; break; fi
    done
    if [[ $known -ne 1 ]]; then echo "Unknown app: $app" >&2; exit 2; fi
    SELECTED+=("$app")
  done
fi

for command in curl python3 tar sha256sum find mktemp; do
  command -v "$command" >/dev/null || { echo "Missing executable: $command" >&2; exit 1; }
done
[[ $(uname -s) == Linux ]] || { echo 'This script is only for native Linux/WSL2.' >&2; exit 1; }
arch=$(uname -m)
case "$arch" in x86_64|aarch64) ;; *) echo "Unsupported architecture: $arch" >&2; exit 1 ;; esac
mkdir -p "$PREFIX" "$BIN_DIR"

tmp_dir=''
archive=''
cleanup() {
  [[ -z "$archive" ]] || rm -f -- "$archive"
  [[ -z "$tmp_dir" ]] || rm -rf -- "$tmp_dir"
}
trap cleanup EXIT

for app in "${SELECTED[@]}"; do
  echo "==> $app: querying official GitHub release"
  metadata=$(curl --fail --silent --show-error --location --retry 3 \
    --connect-timeout 15 --max-time 60 \
    "https://api.github.com/repos/storytold/$app/releases/latest")
  fields=$(python3 -c '
import json, sys
app, arch = sys.argv[1:]
release = json.load(sys.stdin)
tag = release.get("tag_name", "")
if not tag.startswith("v"):
    sys.exit("Release tag is missing or unexpected")
name = f"{app}-{tag.removeprefix(chr(118))}-linux-{arch}.tar.gz"
asset = next((a for a in release.get("assets", []) if a.get("name") == name), None)
if not asset:
    sys.exit(f"Release asset not found: {name}")
url = asset.get("browser_download_url", "")
digest = asset.get("digest", "")
if not url.startswith("https://github.com/storytold/") or not digest.startswith("sha256:"):
    sys.exit("Official URL or SHA256 digest is missing")
print(tag)
print(url)
print(digest.removeprefix("sha256:"))
print(asset.get("size", 0))
' "$app" "$arch" <<<"$metadata") || exit 1
  tag=$(printf '%s\n' "$fields" | sed -n '1p')
  url=$(printf '%s\n' "$fields" | sed -n '2p')
  digest=$(printf '%s\n' "$fields" | sed -n '3p')
  bytes=$(printf '%s\n' "$fields" | sed -n '4p')
  version="${tag#v}"
  final="$PREFIX/$app/$version"
  if [[ -d "$final" ]]; then
    echo "Existing release tree: $final"
  else
    mkdir -p "$PREFIX/$app"
    archive=$(mktemp "${TMPDIR:-/tmp}/agentcraft-${app}-XXXXXXXX.tar.gz")
    echo "Downloading: $version ($((bytes / 1048576)) MiB)"
    curl --fail --show-error --silent --location --retry 3 --connect-timeout 20 \
      "$url" --output "$archive"
    printf '%s  %s\n' "$digest" "$archive" | sha256sum --check --status || {
      echo "SHA-256 mismatch for $app: refusing extraction" >&2; exit 1;
    }
    tmp_dir=$(mktemp -d "$PREFIX/$app/.staging-XXXXXXXX")
    tar -xzf "$archive" -C "$tmp_dir" --no-same-owner --no-same-permissions
    binary=$(find "$tmp_dir" -type f -name "$app-cli" -print -quit)
    if [[ -z "$binary" ]]; then
      echo "No $app-cli binary inside official archive: $url" >&2; exit 1
    fi
    # Rename the complete release tree: CLI resources and shared assets remain alongside it.
    mv -- "$tmp_dir" "$final"
    tmp_dir=''
    rm -f -- "$archive"
    archive=''
  fi
  binary=$(find "$final" -type f -name "$app-cli" -print -quit)
  [[ -n "$binary" ]] || { echo "$app-cli not found in $final" >&2; exit 1; }
  chmod u+x "$binary"
  link="$BIN_DIR/$app-cli"
  if [[ -e "$link" && ! -L "$link" ]]; then
    echo "Refusing to overwrite non-symlink: $link" >&2; exit 1
  fi
  ln -sfn -- "$binary" "$link"
  echo "READY: $link -> $binary"
done

printf '\nNative app CLI installation complete.\n'
printf 'If needed: export PATH="%s:$PATH"\n' "$BIN_DIR"
printf 'Then: agentcraft install --scope project --target . --apps all --client all --bin-dir "%s"\n' "$BIN_DIR"
printf 'Verify: agentcraft doctor --apps all --bin-dir "%s"\n' "$BIN_DIR"
