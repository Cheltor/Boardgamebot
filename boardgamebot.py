import os

import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

# --- CONFIG: EDIT THESE VALUES OR USE .env ---
TOKEN = os.getenv("DISCORD_TOKEN") or "YOUR_BOT_TOKEN_HERE"
CHANNEL_ID_ENV = os.getenv("CHANNEL_ID")
CHANNEL_ID = int(CHANNEL_ID_ENV) if CHANNEL_ID_ENV else 0  # optional: restrict to a single channel
if not TOKEN or TOKEN == "YOUR_BOT_TOKEN_HERE":
    raise ValueError("Missing DISCORD_TOKEN. Set it in .env or edit TOKEN in boardgamebot.py.")


# --- DISCORD SETUP ---

intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

current_rsvp_message_id: int | None = None
current_rsvp_channel_id: int | None = None

yes_list: set[int] = set()
no_list: set[int] = set()
guest_counts: dict[int, int] = {}
rsvp_header = ""

DIGIT_EMOJIS = {
    "0️⃣": 0,
    "1️⃣": 1,
    "2️⃣": 2,
    "3️⃣": 3,
    "4️⃣": 4,
    "5️⃣": 5,
}


async def create_rsvp_message(channel: discord.TextChannel, original_msg: discord.Message):
    """
    Create a new RSVP message tied to the original announcement.
    Auto-pins this RSVP and unpins the previous one if it exists.
    """
    global current_rsvp_message_id, current_rsvp_channel_id, rsvp_header

    # Clear previous state
    yes_list.clear()
    no_list.clear()
    guest_counts.clear()

    # Try to unpin previous RSVP message if we had one
    if current_rsvp_message_id and current_rsvp_channel_id:
        try:
            old_channel = bot.get_channel(current_rsvp_channel_id)
            if old_channel is not None:
                old_msg = await old_channel.fetch_message(current_rsvp_message_id)
                if old_msg.pinned:
                    await old_msg.unpin(reason="Replacing with new board game RSVP")
        except Exception:
            # If unpin fails, just ignore
            pass

    # Use the first line as short description
    first_line = (original_msg.content.split("\n")[0][:200] or "Board game night").strip()

    rsvp_header = (
        "🎲 **Board Game Night RSVP** 🎲\n"
        f"From message: {original_msg.jump_url}\n"
        f"Details: _{first_line}_\n\n"
        "React with:\n"
        "  ✅ if you're coming\n"
        "  ❌ if you can't make it\n"
        "  0️⃣-5️⃣ to show how many **extra guests** you'll bring\n"
    ).rstrip()

    # Initial RSVP text
    rsvp_body = (
        "Current RSVPs:\n"
        "✅ Yes (0 RSVPs, 0 total incl. guests):\n"
        "❌ No (0):\n"
    )

    full_text = rsvp_header + "\n\n" + rsvp_body

    msg = await channel.send(full_text)

    # Add reactions for users
    await msg.add_reaction("✅")
    await msg.add_reaction("❌")
    for emoji in DIGIT_EMOJIS.keys():
        await msg.add_reaction(emoji)

    # Pin this message
    try:
        await msg.pin(reason="Board game night RSVP")
    except Exception:
        pass

    current_rsvp_message_id = msg.id
    current_rsvp_channel_id = msg.channel.id


async def update_rsvp_message():
    """Update the RSVP message with who said yes/no and guest counts."""
    global current_rsvp_message_id, current_rsvp_channel_id

    if not current_rsvp_message_id or not current_rsvp_channel_id:
        return

    channel = bot.get_channel(current_rsvp_channel_id)
    if channel is None:
        return

    msg = await channel.fetch_message(current_rsvp_message_id)
    guild = msg.guild

    # Build Yes list with guest info
    yes_entries = []
    total_guests = 0

    for uid in yes_list:
        member = guild.get_member(uid) if guild else None
        name = member.display_name if member else f"User {uid}"
        guests = guest_counts.get(uid, 0)
        total_guests += guests
        if guests > 0:
            yes_entries.append(f"- {name} (+{guests})")
        else:
            yes_entries.append(f"- {name}")

    # Build No list
    no_entries = []
    for uid in no_list:
        if uid in yes_list:
            continue
        member = guild.get_member(uid) if guild else None
        name = member.display_name if member else f"User {uid}"
        no_entries.append(f"- {name}")

    rsvp_count = len(yes_entries)
    total_people = rsvp_count + total_guests

    yes_block = (
        f"✅ Yes ({rsvp_count} RSVPs, {total_people} total incl. guests):\n"
        + ("\n".join(yes_entries) if yes_entries else "(none)")
    )

    no_block = (
        f"❌ No ({len(no_entries)}):\n"
        + ("\n".join(no_entries) if no_entries else "(none)")
    )

    new_body = "Current RSVPs:\n" + yes_block + "\n\n" + no_block
    new_text = rsvp_header + "\n\n" + new_body

    await msg.edit(content=new_text)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    print("------")


@bot.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    """Handle 🎲 trigger, yes/no, and guest count reactions."""
    global yes_list, no_list, guest_counts

    emoji_str = str(payload.emoji)

    # 1) 🎲 on any message -> create a new RSVP
    if emoji_str == "🎲":
        channel = bot.get_channel(payload.channel_id)
        if channel is None:
            return

        # Optional: restrict to specific channel
        if CHANNEL_ID and channel.id != CHANNEL_ID:
            return

        original_msg = await channel.fetch_message(payload.message_id)
        await create_rsvp_message(channel, original_msg)
        return

    # 2) Everything below is only for the active RSVP message
    if payload.message_id != current_rsvp_message_id:
        return

    if bot.user and payload.user_id == bot.user.id:
        return  # ignore bot's own reactions

    # Fetch the RSVP message & member for managing digit reactions
    channel = bot.get_channel(payload.channel_id)
    if channel is None:
        return
    msg = await channel.fetch_message(payload.message_id)
    guild = msg.guild
    member = guild.get_member(payload.user_id) if guild else None
    reaction_user = member or discord.Object(id=payload.user_id)

    # Yes / No reactions
    if emoji_str == "✅":
        yes_list.add(payload.user_id)
        no_list.discard(payload.user_id)
    elif emoji_str == "❌":
        no_list.add(payload.user_id)
        yes_list.discard(payload.user_id)

    # Guest count reactions 0–5
    if emoji_str in DIGIT_EMOJIS:
        guest_counts[payload.user_id] = DIGIT_EMOJIS[emoji_str]

        # Ensure they only have one digit reaction: remove others
        for other_emoji in DIGIT_EMOJIS.keys():
            if other_emoji == emoji_str:
                continue
            try:
                await msg.remove_reaction(other_emoji, reaction_user)
            except Exception:
                pass

    await update_rsvp_message()


@bot.event
async def on_raw_reaction_remove(payload: discord.RawReactionActionEvent):
    """Keep state in sync when reactions are removed."""
    global yes_list, no_list, guest_counts

    emoji_str = str(payload.emoji)

    if payload.message_id != current_rsvp_message_id:
        return

    if emoji_str == "✅":
        yes_list.discard(payload.user_id)
    elif emoji_str == "❌":
        no_list.discard(payload.user_id)
    elif emoji_str in DIGIT_EMOJIS:
        guest_counts.pop(payload.user_id, None)

    await update_rsvp_message()


bot.run(TOKEN)
