import json
import os
import random
from datetime import time as dt_time
from zoneinfo import ZoneInfo

import discord
from discord import app_commands
from discord.ext import tasks
from dotenv import load_dotenv

load_dotenv()

# ============================================================
# LOAD CONFIG (env vars take priority; config.json is optional)
# ============================================================

config = {}
if os.path.exists("config.json"):
    with open("config.json", "r", encoding="utf-8") as f:
        config = json.load(f)


def cfg(key, default=None):
    """Read a setting from the environment first, then config.json."""
    return os.getenv(key.upper()) or config.get(key, default)


# ============================================================
# LOAD EXISTING IMAGES
# ============================================================

with open("images.json", "r", encoding="utf-8") as f:
    images = json.load(f)


# ============================================================
# SETTINGS
# ============================================================

TOKEN = os.getenv("DISCORD_TOKEN") or config.get("token")

CHANNEL_ID = int(cfg("channel_id"))

# Role that gets pinged for every hunt
ROLE_ID = int(cfg("role_id"))

# Role allowed to use /vnareroll
MANAGER_ROLE_ID = int(cfg("manager_role_id"))

# Daily hunt time
POST_HOUR = int(cfg("post_hour", 9))
POST_MINUTE = int(cfg("post_minute", 30))

# Timezone
TIMEZONE = ZoneInfo(
    cfg("timezone", "Asia/Kolkata")
)

# User who should be mentioned for proof
PROOF_USER_ID = 782892046952169492

# Cosmic purple / blue
EMBED_COLOR = 0x5B4BDB


# ============================================================
# POKEMON
# ============================================================

POKEMON = list(images.keys())

if not POKEMON:
    raise RuntimeError(
        "images.json is empty."
    )


# ============================================================
# DISCORD INTENTS
# ============================================================

intents = discord.Intents.default()

intents.members = True


# ============================================================
# DISCORD CLIENT
# ============================================================

client = discord.Client(
    intents=intents
)

tree = app_commands.CommandTree(client)


# ============================================================
# CREATE HUNT EMBED
# ============================================================

def create_hunt_embed(pokemon):

    image_url = images[pokemon]

    embed = discord.Embed(
        title="🌌 VNA'S DAILY HUNT",
        color=EMBED_COLOR
    )

    # --------------------------------------------------------
    # INTRO
    # --------------------------------------------------------

    embed.description = (
        "✨ **Today's Pokémon is...**\n\n"
        f"# **{pokemon}**\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "💰 **REWARD**\n"
        "`500k 🪙 Pokécoins`\n\n"
        "🏆 **FIRST TO CATCH**\n"
        f"<@{PROOF_USER_ID}> **with proof**\n\n"
    )

    # --------------------------------------------------------
    # POKEMON IMAGE
    # --------------------------------------------------------

    if image_url:
        embed.set_image(
            url=image_url
        )

    # --------------------------------------------------------
    # FOOTER
    # --------------------------------------------------------

    embed.set_footer(
        text="✨ Good luck everyone! Have fun grinding and be the first to catch it!"
    )

    return embed


# ============================================================
# SEND HUNT
# ============================================================

async def send_hunt():

    channel = client.get_channel(
        CHANNEL_ID
    )

    # Fetch channel if not cached
    if channel is None:

        try:

            channel = await client.fetch_channel(
                CHANNEL_ID
            )

        except Exception as e:

            print(
                f"Could not find channel: {e}"
            )

            return

    # --------------------------------------------------------
    # RANDOM POKEMON
    # --------------------------------------------------------
    # Completely random.
    # Consecutive repeats are allowed.

    pokemon = random.choice(
        POKEMON
    )

    embed = create_hunt_embed(
        pokemon
    )

    # --------------------------------------------------------
    # HUNT ROLE ONLY
    # --------------------------------------------------------
    # The proof user is mentioned inside the embed instead,
    # so they are NOT pinged twice.

    ping = f"<@&{ROLE_ID}>"

    await channel.send(

        content=ping,

        embed=embed,

        allowed_mentions=discord.AllowedMentions(
            roles=True,
            users=True
        )
    )

    print(
        f"Hunt sent: {pokemon}"
    )


# ============================================================
# DAILY HUNT
# ============================================================

@tasks.loop(
    time=dt_time(
        hour=POST_HOUR,
        minute=POST_MINUTE,
        tzinfo=TIMEZONE
    )
)
async def daily_hunt():

    await send_hunt()


@daily_hunt.before_loop
async def before_daily_hunt():

    await client.wait_until_ready()


# ============================================================
# /VNAREROLL
# ============================================================

@tree.command(
    name="vnareroll",
    description="Reroll the current VNA Pokémon hunt."
)
async def vnareroll(
    interaction: discord.Interaction
):

    # --------------------------------------------------------
    # SERVER CHECK
    # --------------------------------------------------------

    if interaction.guild is None:

        await interaction.response.send_message(
            "❌ This command can only be used inside the server.",
            ephemeral=True
        )

        return

    # --------------------------------------------------------
    # FETCH MEMBER
    # --------------------------------------------------------

    try:

        member = await interaction.guild.fetch_member(
            interaction.user.id
        )

    except discord.NotFound:

        await interaction.response.send_message(
            "❌ Could not find your server membership.",
            ephemeral=True
        )

        return

    except discord.HTTPException as e:

        print(
            f"Failed to fetch member: {e}"
        )

        await interaction.response.send_message(
            "❌ Could not verify your server roles. Try again.",
            ephemeral=True
        )

        return

    # --------------------------------------------------------
    # OWNER CHECK
    # --------------------------------------------------------

    is_owner = (
        interaction.guild.owner_id
        == member.id
    )

    # --------------------------------------------------------
    # MANAGER ROLE CHECK
    # --------------------------------------------------------

    has_manager_role = any(
        role.id == MANAGER_ROLE_ID
        for role in member.roles
    )

    # --------------------------------------------------------
    # DEBUG
    # --------------------------------------------------------

    print(
        "Reroll permission check:"
    )

    print(
        f"User: {member}"
    )

    print(
        f"User ID: {member.id}"
    )

    print(
        f"Server Owner ID: "
        f"{interaction.guild.owner_id}"
    )

    print(
        f"Is Owner: {is_owner}"
    )

    print(
        f"Manager Role ID: "
        f"{MANAGER_ROLE_ID}"
    )

    print(
        "User Roles:"
    )

    print(
        [
            f"{role.name} ({role.id})"
            for role in member.roles
        ]
    )

    print(
        f"Has Manager Role: "
        f"{has_manager_role}"
    )

    # --------------------------------------------------------
    # PERMISSION
    # --------------------------------------------------------

    if not is_owner and not has_manager_role:

        await interaction.response.send_message(
            "❌ You don't have permission to use `/vnareroll`.",
            ephemeral=True
        )

        return

    # --------------------------------------------------------
    # REROLL
    # --------------------------------------------------------

    await interaction.response.defer()

    pokemon = random.choice(
        POKEMON
    )

    embed = create_hunt_embed(
        pokemon
    )

    # Only ping the hunt role
    ping = f"<@&{ROLE_ID}>"

    await interaction.followup.send(

        content=ping,

        embed=embed,

        allowed_mentions=discord.AllowedMentions(
            roles=True,
            users=True
        )
    )

    print(
        f"Reroll used by "
        f"{member} -> {pokemon}"
    )


# ============================================================
# BOT READY
# ============================================================

@client.event
async def on_ready():

    print(
        f"Logged in as {client.user} "
        f"(ID: {client.user.id})"
    )

    # --------------------------------------------------------
    # SYNC SLASH COMMAND
    # --------------------------------------------------------

    try:

        synced = await tree.sync()

        print(
            f"Synced {len(synced)} slash command(s)."
        )

    except Exception as e:

        print(
            f"Failed to sync slash commands: {e}"
        )

    # --------------------------------------------------------
    # START DAILY SCHEDULER
    # --------------------------------------------------------

    if not daily_hunt.is_running():

        daily_hunt.start()

        print(
            f"Daily hunt scheduled for "
            f"{POST_HOUR:02d}:"
            f"{POST_MINUTE:02d} "
            f"{config.get('timezone', 'Asia/Kolkata')}"
        )


# ============================================================
# CONFIG VALIDATION
# ============================================================

if (
    not TOKEN
    or TOKEN == "PASTE_BOT_TOKEN_HERE"
    or TOKEN == "YOUR_BOT_TOKEN"
):

    raise RuntimeError(
        "Put your Discord bot token in config.json."
    )


if (
    config["channel_id"]
    in [
        "PASTE_CHANNEL_ID_HERE",
        "YOUR_CHANNEL_ID"
    ]
):

    raise RuntimeError(
        "Put your Discord channel ID in config.json."
    )


if (
    config["role_id"]
    in [
        "PASTE_HUNT_ROLE_ID_HERE",
        "YOUR_HUNT_ROLE_ID"
    ]
):

    raise RuntimeError(
        "Put your hunt role ID in config.json."
    )


if (
    config["manager_role_id"]
    in [
        "PASTE_MANAGER_ROLE_ID_HERE",
        "YOUR_MANAGER_ROLE_ID"
    ]
):

    raise RuntimeError(
        "Put your manager role ID in config.json."
    )


# ============================================================
# START BOT
# ============================================================

client.run(TOKEN)