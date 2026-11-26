# Tests

From the repository root, use a Python 3.11 virtual environment and run:

```sh
python -m pip install -r requirements-test.txt
python -m unittest -v
```

The suite covers role assignment, onboarding, audio moderation, message export,
challenge summaries, YouTube playlists, and Supabase sync. It uses temporary files and mocks
for external services, so it runs without Discord, Google, or Supabase credentials.
GitHub Actions runs the same suite on pushes and pull requests.

# Supabase member-role sync

The bot mirrors the Portland Music Producers Discord server to Supabase every
night at midnight Pacific time (`America/Los_Angeles`). Discord is the source
of truth, so roles assigned by reactions, moderators, and other bots are all
included. The implicit `@everyone` role is excluded. The sync stores member IDs
and assigned role IDs and names. Each successful run reflects removed roles
and members who left the server.

1. In the Supabase project's **SQL Editor**, run [the member sync SQL](supabase/member_sync.sql).
   Leave the Data API enabled with `public` exposed.
2. Copy the **Project URL** from the project's **Connect** dialog and create a
   dedicated **Secret key** under **Settings → API Keys**. Put both values in
   the deployment host's `.env` file next to `docker-compose.yml`, or set them
   through your host's secret manager. The repository ignores `.env`. Keep the
   key on the bot host.

   ```dotenv
   SUPABASE_URL=https://<project-ref>.supabase.co
   SUPABASE_SECRET_KEY=<sb_secret_key>
   ```

3. Add these two entries under the Compose service's existing `environment:`
   list so the container receives the values. Recreate the container with
   `docker compose up -d --force-recreate redbot` after deploying the updated cog.

   ```yaml
   - SUPABASE_URL=${SUPABASE_URL}
   - SUPABASE_SECRET_KEY=${SUPABASE_SECRET_KEY}
   ```

4. Enable **Server Members Intent** for the bot in the Discord Developer Portal
   and in Red's active intents. Run `!supabasesync` as the bot owner to check
   the setup immediately, then inspect `pmp_discord_member_roles` in Supabase.
   If the bot is offline at midnight, run the same command to catch up.

`pmp_discord_member_roles` has one row per member and assigned role. Filter by
`role_id` to find everyone with a role, even if its name changes. The
`pmp_discord_members` table includes members with zero assigned roles and records
the snapshot time in `synced_at`. Both tables are restricted to server-side
access by the supplied SQL.

# Docker Stuff
# open a shell in the running container
docker compose exec redbot /bin/bash

# install to *this* bot’s venv, not system Python
/data/venv/bin/pip install --no-cache-dir google-auth-oauthlib google-api-python-client

The docker-compose.yml for this bot looks like this. You should put the token and owner in an .env file:
docker-compose.yml
```
version: "3.2"
services:
  redbot:
    container_name: redbot
    image: phasecorex/red-discordbot
    restart: unless-stopped
    volumes:
      - ./redbot:/data
    environment:
      - TOKEN=????
      - OWNER=????
      - PREFIX=!
      - TZ=America/Los_Angeles
      - PUID=1000
```

When you fire up the docker container, you'll need to complete the youtube api oauth workflow. Check `docker compose logs` for the URL. You can use this python 1-liner to execute the callback:

```python
docker compose exec redbot /bin/bash -c '
  source /data/venv/bin/activate
  python - <<PY
import urllib.request
resp = urllib.request.urlopen(
    "http://your_callback_url"
)
print("HTTP callback response:", resp.read().decode(errors="ignore"))
PY
'
```


# Notes
After pushing to github, to update the bot from the console:
!repo update
!cog update

# Youtube Playlist
Delete the token.json and restart the bot. Follow the URL to authenticate the youtube API. When you get the callback api in the browser, pass it in to docker:
  docker compose exec redbot /bin/bash -c '
    source /data/venv/bin/activate
    python - <<PY
import urllib.request
resp = urllib.request.urlopen(
  "YOUR-URL-HERE"
)
print("HTTP callback response:", resp.read().decode(errors="ignore"))
PY
'
