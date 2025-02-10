# Portland Music Producers Discord Bot Scope
## Implementation:
### Data Storage
Potentially store user data in Google Sheets (same as the Form) or Firestore (more robust).
### Technology Stack
Written in Python (using a Discord library like discord.py forks, PyCord, or Nextcord).
### Hosting
Hosted somewhere it can stay online 24/7 (e.g., Replit, Railway.app).

## Features:
### Priority 1
All new members get an “Unverified” role automatically.

After specified days (time since unverified user joined) bot takes action:

Bot reminds them to complete two tasks:
Post an introduction in #introduce-yourself.
Fill out a Google Form (results of which go to Google Sheets).

Communication Method
DM if possible (it won’t go through for people who don’t allow DM’s from strangers), and tag them in a #verification channel.

### Priority 2
Once deadline has expired, ask admins for final approval to kick.

### Priority 3
Bot grants user verified “member” role if both requirements are done.

