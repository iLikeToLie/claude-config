# claude-config
User-level Claude Code config (skills, CLAUDE.md, rules, plugins) restored into cloud environments.
Excludes Orca skills/hooks and the local `synced` skill bucket.

Setup: push this repo (private), create a read-only fine-grained GitHub token (Contents: read, this repo only),
then in the cloud environment set secrets `CFG_TOKEN` and `CFG_REPO` (owner/claude-config) and set the setup script to:

    git clone https://x-access-token:$CFG_TOKEN@github.com/$CFG_REPO.git /tmp/cc && bash /tmp/cc/setup.sh
