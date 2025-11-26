# Boardgamebot

Discord bot that manages a board-game-night RSVP message using reactions.

## Features
- React to any announcement with 🎲 to spawn a pinned RSVP linked to that message.
- ✅ / ❌ track who is coming; 0️⃣-5️⃣ set per-user guest counts (only one digit allowed).
- Auto-updates totals and names, and unpins the prior RSVP when a new one is created.

## Setup

1. **Create a virtual environment (recommended)**
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```
2. **Install dependencies**
   ```powershell
   pip install -r requirements.txt
   ```
3. **Configure secrets**
   - Copy `.env.example` to `.env`.
   - Set `DISCORD_TOKEN` to your bot token.
   - Optional: set `CHANNEL_ID` if you only want the 🎲 trigger in one channel.
   - In the Discord Developer Portal, enable **Message Content Intent** and **Server Members Intent** for the bot.

## Running the bot

```powershell
python boardgamebot.py
```

React with 🎲 to an announcement to create the RSVP. People can then use ✅ / ❌ and 0️⃣-5️⃣ reactions to update attendance.

## Deploying on Railway
- Set environment variables in Railway: `DISCORD_TOKEN` (required) and optionally `CHANNEL_ID`.
- Railway should detect Python and install from `requirements.txt`.
- The included `Procfile` runs `python boardgamebot.py` as the start command.
