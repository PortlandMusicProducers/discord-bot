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
