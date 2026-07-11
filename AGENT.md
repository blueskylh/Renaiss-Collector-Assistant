# Agent Rules for Renaiss Collector Assistant

These rules are for agents that install or run the `renaiss-collector-assistant` skill.

## Existing installation update check

Before installing or using the skill, first check whether the agent already has a local copy installed.

1. Locate the local skill directory, usually:

   ```text
   <AGENT_SKILLS_DIR>/renaiss-collector-assistant/
   ```

2. Read the local version from:

   ```text
   <AGENT_SKILLS_DIR>/renaiss-collector-assistant/manifest.json
   ```

3. Read the GitHub version from the repository copy:

   ```text
   https://github.com/blueskylh/Renaiss-Collector-Assistant/blob/main/skills/renaiss-collector-assistant/manifest.json
   ```

   If running from a local clone, update the clone first:

   ```bash
   git pull --ff-only
   ```

4. Compare versions using semantic-version order.

   - If GitHub version is newer than the local installed skill, update the local skill from the GitHub repository.
   - If local version is newer than GitHub, do **not** overwrite it automatically; report that the local skill is ahead.
   - If versions are equal, do not reinstall unless the user asks for a clean reinstall.

5. Safe update command example:

   ```bash
   rsync -a --delete \
     --exclude '.env' \
     --exclude 'data/' \
     --exclude 'outputs/' \
     skills/renaiss-collector-assistant/ \
     <AGENT_SKILLS_DIR>/renaiss-collector-assistant/
   ```

6. Never overwrite or print local secrets:

   - `.env`
   - API keys
   - SSH private keys / deploy keys
   - generated `data/` and `outputs/`

7. After updating, run:

   ```bash
   cd <AGENT_SKILLS_DIR>/renaiss-collector-assistant
   bash scripts/install_check.sh
   ```

If the update check cannot be completed, tell the user exactly which path or command failed instead of silently reinstalling.
