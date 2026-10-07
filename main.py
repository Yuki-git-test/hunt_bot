import asyncio
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
# LOAD & SAVE CONFIG
# ============================================================

def load_config():
    try:
        with open("config.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {
            "token": "YOUR_BOT_TOKEN",
            "channel_id": None,
            "role_id": None,
            "manager_role_id": None,
            "post_hour": 9,
            "post_minute": 30,
            "timezone": "Asia/Kolkata"
        }

def save_config(config_data):
    with open("config.json", "w", encoding="utf-8") as f:
        json.dump(config_data, f, indent=4)

config = load_config()


# ============================================================
# LOAD EXISTING IMAGES
# ============================================================

with open("images.json", "r", encoding="utf-8") as f:
    images = json.load(f)


# ============================================================
# SETTINGS
# ============================================================

TOKEN = os.getenv("DISCORD_TOKEN") or config.get("token")

# Global dynamic setting variables (populated via config or /set commands)
CHANNEL_ID = config.get("channel_id")
ROLE_ID = config.get("role_id")
MANAGER_ROLE_ID = config.get("manager_role_id")

# Daily hunt time settings
POST_HOUR = int(config.get("post_hour", 9))
POST_MINUTE = int(config.get("post_minute", 30))

# Timezone
TIMEZONE = ZoneInfo(
    config.get("timezone", "Asia/Kolkata")
)

# User who should be mentioned for proof
PROOF_USER_ID = 782892046952169492

# Cosmic purple / blue
EMBED_COLOR = 0x5B4BDB


# ============================================================
# SERVER EMOJIS
# ============================================================

POKECOIN_EMOJI = "<:vna_pokecoin:1173890257285042227>"
POKEBALL_EMOJI = "<:vna_pokeball:1102966128495566960>"
LEGENDARY_EMOJI = "<:vna_Legendary:1174392567123693578>"
TROPHY_EMOJI = "<:vna_trophy:1152272236007399504>"


# ============================================================
# POKEMON
# ============================================================

POKEMON = list(images.keys())

if not POKEMON:
    raise RuntimeError(
        "images.json is empty."
    )


# ============================================================
# DISCORD INTENTS & CLIENT
# ============================================================

intents = discord.Intents.default()
intents.members = True

client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)


# ============================================================
# CREATE HUNT EMBED
# ============================================================

def create_hunt_embed(pokemon, guild=None):
    image_url = images[pokemon]

    embed = discord.Embed(
        color=EMBED_COLOR
    )

    if guild and guild.icon:
        embed.set_author(
            name="VNA'S DAILY HUNT",
            icon_url=guild.icon.url
        )
    else:
        embed.set_author(
            name="VNA'S DAILY HUNT"
        )

    embed.description = (
        f"{POKEBALL_EMOJI} **Today's Pokémon is...**\n\n"
        f"# {LEGENDARY_EMOJI} **{pokemon}**\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{POKECOIN_EMOJI} **REWARD**\n"
        f"**500k Pokécoins**\n\n"
        f"{TROPHY_EMOJI} **FIRST TO CATCH**\n"
        f"**Mention <@{PROOF_USER_ID}> with proof**\n\n"
    )

    if image_url:
        embed.set_image(
            url=image_url
        )

    embed.set_footer(
        text="✨ Good luck everyone! Have fun grinding and be the first to catch it!"
    )

    return embed


# ============================================================
# GET CHANNEL
# ============================================================

async def get_hunt_channel():
    if not CHANNEL_ID:
        print("[CHANNEL ERROR] Daily hunt channel ID is not set. Use /set channel first.")
        return None

    channel = client.get_channel(int(CHANNEL_ID))
    if channel is not None:
        return channel

    try:
        channel = await client.fetch_channel(int(CHANNEL_ID))
        return channel
    except Exception as e:
        print(f"[CHANNEL ERROR] Could not find channel with ID {CHANNEL_ID}: {e}")
        return None


# ============================================================
# SEND HUNT
# ============================================================

async def send_hunt():
    channel = await get_hunt_channel()

    if channel is None:
        print("[HUNT ERROR] Hunt channel could not be found. Please setup channel using /set channel.")
        return False

    pokemon = random.choice(POKEMON)

    guild = getattr(channel, "guild", None)
    embed = create_hunt_embed(pokemon, guild)

    ping = f"<@&{ROLE_ID}>" if ROLE_ID else ""

    retry_delays = [30, 60, 120, 300, 600, 1200]
    total_attempts = len(retry_delays) + 1

    for attempt in range(1, total_attempts + 1):
        try:
            await channel.send(
                content=ping,
                embed=embed,
                allowed_mentions=discord.AllowedMentions(
                    roles=True,
                    users=True
                )
            )
            print(f"[HUNT SUCCESS] Hunt sent: {pokemon}")
            return True

        except discord.HTTPException as e:
            status = getattr(e, "status", None)

            if status == 429:
                retry_after = getattr(e, "retry_after", None)
                if retry_after is None:
                    try:
                        retry_after = e.response.headers.get("Retry-After")
                    except Exception:
                        retry_after = None

                try:
                    if retry_after is not None:
                        retry_after = float(retry_after)
                    else:
                        retry_after = retry_delays[min(attempt - 1, len(retry_delays) - 1)]
                except (TypeError, ValueError):
                    retry_after = retry_delays[min(attempt - 1, len(retry_delays) - 1)]

                retry_after = max(retry_after, 10)
                retry_after = min(retry_after, 3600)

                if attempt >= total_attempts:
                    print("[HUNT FAILED] Discord is still rate limiting after all retry attempts.")
                    return False

                print(f"[RATE LIMITED] Discord returned 429 (attempt {attempt}/{total_attempts}). Waiting {retry_after:.0f}s...")
                await asyncio.sleep(retry_after)
                continue

            print(f"[DISCORD HTTP ERROR] Status {status}: {e}")
            return False

        except discord.Forbidden as e:
            print(f"[PERMISSION ERROR] Bot cannot send messages in the channel: {e}")
            return False

        except discord.NotFound as e:
            print(f"[NOT FOUND ERROR] Channel/message destination was not found: {e}")
            return False

        except Exception as e:
            print(f"[UNEXPECTED HUNT ERROR] {type(e).__name__}: {e}")
            return False

    return False


# ============================================================
# DAILY HUNT TASK
# ============================================================

@tasks.loop(
    time=dt_time(
        hour=POST_HOUR,
        minute=POST_MINUTE,
        tzinfo=TIMEZONE
    )
)
async def daily_hunt():
    print("[DAILY HUNT] Scheduled hunt triggered.")
    try:
        success = await send_hunt()
        if success:
            print("[DAILY HUNT] Completed successfully.")
        else:
            print("[DAILY HUNT] Could not send today's hunt.")
    except Exception as e:
        print(f"[DAILY HUNT ERROR] {type(e).__name__}: {e}")

@daily_hunt.before_loop
async def before_daily_hunt():
    await client.wait_until_ready()
    print("[DAILY HUNT] Scheduler is ready.")


# ============================================================
# SLASH COMMAND GROUP: /set (ADMIN ONLY)
# ============================================================

set_group = app_commands.Group(
    name="set",
    description="Configure bot settings for the daily hunt.",
    default_permissions=discord.Permissions(administrator=True)
)

@set_group.command(name="channel", description="Set the channel where daily hunts are posted.")
@app_commands.checks.has_permissions(administrator=True)
async def set_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    global CHANNEL_ID
    CHANNEL_ID = channel.id
    config["channel_id"] = channel.id
    save_config(config)

    await interaction.response.send_message(
        f"✅ Daily hunt channel has been set to {channel.mention} and saved to config.json.",
        ephemeral=True
    )

@set_group.command(name="manager", description="Set the role allowed to use /vnareroll.")
@app_commands.checks.has_permissions(administrator=True)
async def set_manager(interaction: discord.Interaction, role: discord.Role):
    global MANAGER_ROLE_ID
    MANAGER_ROLE_ID = role.id
    config["manager_role_id"] = role.id
    save_config(config)

    await interaction.response.send_message(
        f"✅ Manager role has been set to {role.mention} and saved to config.json.",
        ephemeral=True
    )

@set_group.command(name="ping", description="Set the role pinged when a hunt spawns.")
@app_commands.checks.has_permissions(administrator=True)
async def set_ping(interaction: discord.Interaction, role: discord.Role):
    global ROLE_ID
    ROLE_ID = role.id
    config["role_id"] = role.id
    save_config(config)

    await interaction.response.send_message(
        f"✅ Daily hunt ping role has been set to {role.mention} and saved to config.json.",
        ephemeral=True
    )

# Register command group
tree.add_command(set_group)


# ============================================================
# /VNAREROLL
# ============================================================

@tree.command(
    name="vnareroll",
    description="Reroll the current VNA Pokémon hunt."
)
async def vnareroll(interaction: discord.Interaction):
    if interaction.guild is None:
        await interaction.response.send_message(
            "❌ This command can only be used inside the server.",
            ephemeral=True
        )
        return

    # Check permission (Server Owner or Manager Role)
    try:
        member = await interaction.guild.fetch_member(interaction.user.id)
    except Exception:
        await interaction.response.send_message(
            "❌ Could not verify your server permissions.",
            ephemeral=True
        )
        return

    is_owner = (interaction.guild.owner_id == member.id)
    has_manager_role = (
        MANAGER_ROLE_ID is not None and
        any(role.id == int(MANAGER_ROLE_ID) for role in member.roles)
    )

    if not is_owner and not has_manager_role:
        await interaction.response.send_message(
            "❌ You don't have permission to use `/vnareroll`.",
            ephemeral=True
        )
        return

    # Check if target channel is configured
    target_channel = await get_hunt_channel()
    if target_channel is None:
        await interaction.response.send_message(
            "❌ Target daily hunt channel is not set up! Run `/set channel` first.",
            ephemeral=True
        )
        return

    # Process reroll and send to the target channel
    pokemon = random.choice(POKEMON)
    embed = create_hunt_embed(pokemon, interaction.guild)
    ping = f"<@&{ROLE_ID}>" if ROLE_ID else ""

    try:
        # Send embed into the set channel
        await target_channel.send(
            content=ping,
            embed=embed,
            allowed_mentions=discord.AllowedMentions(
                roles=True,
                users=True
            )
        )

        # Acknowledge user ephemerally where command was executed
        if interaction.channel_id == target_channel.id:
            await interaction.response.send_message(
                f"🎲 Rerolled hunt: **{pokemon}**",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"✅ Rerolled hunt (**{pokemon}**) and sent to {target_channel.mention}!",
                ephemeral=True
            )

        print(f"[REROLL SUCCESS] Used by {member} -> {pokemon} sent to #{target_channel.name}")

    except discord.Forbidden:
        await interaction.response.send_message(
            f"❌ Bot lacks permission to send messages in {target_channel.mention}.",
            ephemeral=True
        )
    except Exception as e:
        print(f"[REROLL ERROR] {type(e).__name__}: {e}")
        await interaction.response.send_message(
            "❌ Something went wrong while executing the reroll.",
            ephemeral=True
        )


# ============================================================
# BOT READY
# ============================================================

@client.event
async def on_ready():
    print(f"Logged in as {client.user} (ID: {client.user.id})")

    try:
        synced = await tree.sync()
        print(f"Synced {len(synced)} slash command(s).")
    except Exception as e:
        print(f"[SYNC ERROR] Failed to sync slash commands: {e}")

    if not daily_hunt.is_running():
        daily_hunt.start()
        print(
            f"[DAILY HUNT] Scheduled for {POST_HOUR:02d}:{POST_MINUTE:02d} "
            f"{config.get('timezone', 'Asia/Kolkata')}"
        )
    else:
        print("[DAILY HUNT] Scheduler is already running.")


# ============================================================
# DISCORD CONNECTION EVENTS
# ============================================================

@client.event
async def on_resumed():
    print("[DISCORD] Gateway connection successfully RESUMED.")

@client.event
async def on_disconnect():
    print("[DISCORD] Gateway connection disconnected. discord.py will attempt to reconnect.")


# ============================================================
# CONFIG VALIDATION
# ============================================================

if not TOKEN or TOKEN in ["PASTE_BOT_TOKEN_HERE", "YOUR_BOT_TOKEN", "YOUR_ACTUAL_BOT_TOKEN"]:
    raise RuntimeError("Put your Discord bot token in the DISCORD_TOKEN env var or config.json.")


# ============================================================
# START BOT
# ============================================================

print("[BOT] Starting VNA Daily Hunt Bot...")
client.run(TOKEN)