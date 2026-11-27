#!/usr/bin/env bash
# Cloud environment setup script: restores user-level ~/.claude from this repo.
# Env vars required: CFG_DEPLOY_KEY (private SSH deploy key, read-only), CFG_REPO (e.g. you/claude-config)
set -u
CLAUDE_DIR="$HOME/.claude"
mkdir -p "$CLAUDE_DIR"
tmp=$(mktemp -d)
keyf="$tmp/key"; printf '%b
' "$CFG_DEPLOY_KEY" > "$keyf"; chmod 600 "$keyf"
GIT_SSH_COMMAND="ssh -i $keyf -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new"   git clone --depth 1 "git@github.com:${CFG_REPO}.git" "$tmp/cfg" || { echo "config clone failed"; exit 0; }
cp -r "$tmp/cfg/skills" "$tmp/cfg/rules" "$tmp/cfg/CLAUDE.md" "$CLAUDE_DIR/"
# merge settings: keep existing keys, config repo wins
if [ -f "$CLAUDE_DIR/settings.json" ]; then
  node -e 'const fs=require("fs");const a=JSON.parse(fs.readFileSync(process.argv[1]));const b=JSON.parse(fs.readFileSync(process.argv[2]));fs.writeFileSync(process.argv[1],JSON.stringify({...a,...b},null,2))' "$CLAUDE_DIR/settings.json" "$tmp/cfg/settings.json"
else
  cp "$tmp/cfg/settings.json" "$CLAUDE_DIR/settings.json"
fi
rm -rf "$tmp"
# CLIs (best effort)
npm i -g ctx7 @openai/codex 2>/dev/null || true
# Plugins (best effort; enabledPlugins in settings.json also triggers install)
if command -v claude >/dev/null; then
  claude plugin marketplace add obra/superpowers-marketplace || true
  claude plugin marketplace add mksglu/context-mode || true
  claude plugin marketplace add nextlevelbuilder/ui-ux-pro-max-skill || true
  claude plugin marketplace add alexgreensh/token-optimizer || true
  claude plugin marketplace add https://github.com/iLikeToLie/Horizon.git || true
  claude plugin marketplace add openai/codex-plugin-cc || true
  for p in superpowers@superpowers-marketplace context-mode@context-mode ui-ux-pro-max@ui-ux-pro-max-skill token-optimizer@alexgreensh-token-optimizer horizon@horizon codex@openai-codex; do claude plugin install "$p" || true; done
fi
