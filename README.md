# claude-config
User-level Claude Code config (skills, CLAUDE.md, rules, plugins) restored into cloud environments.
Excludes Orca skills/hooks and the local `synced` skill bucket.

Setup: a read-only deploy key is registered on this repo. In the cloud environment set secrets
`CFG_DEPLOY_KEY` (the private key, full text incl. BEGIN/END lines) and `CFG_REPO` (owner/claude-config), with setup script:

    k=$(mktemp); printf '%s
' "$CFG_DEPLOY_KEY" > $k; chmod 600 $k; GIT_SSH_COMMAND="ssh -i $k -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new" git clone --depth 1 git@github.com:$CFG_REPO.git /tmp/cc && bash /tmp/cc/setup.sh
