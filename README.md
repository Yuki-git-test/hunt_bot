# VNA Daily Pokémon Hunt Bot

Minimal Discord bot: every day at **9:30 AM IST**, it randomly selects one Pokémon and sends one cosmic purple/blue embed.

## Embed
**VNA HUNT**

**Pokémon name**

**Reward:** 500k 🪙 Pokécoins

**First to catch:** <@782892046952169492> with proof

Then the Pokémon image.

## Edit channel
Open `config.json` and replace `PASTE_CHANNEL_ID_HERE` with the numeric ID of your Discord channel.

## Edit images
Open `images.json`. Each Pokémon has its own entry. Replace `PASTE_IMAGE_URL_HERE` with a direct image URL.

Example:
`"Entei": "https://example.com/entei.png"`

## Run
Install Python 3.10+ and run:
`pip install -r requirements.txt`

Set your bot token as `DISCORD_TOKEN` (never put the token in the files or upload it publicly), then:

Windows PowerShell:
`$env:DISCORD_TOKEN="YOUR_BOT_TOKEN"`
`python bot.py`

Linux/macOS:
`export DISCORD_TOKEN="YOUR_BOT_TOKEN"`
`python bot.py`

The bot needs permission to View Channel, Send Messages and Embed Links.

## Random behavior
Pure random selection is used. The same Pokémon can be selected on consecutive days.
