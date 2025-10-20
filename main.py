import discord
from discord.ext import commands, tasks
from datetime import datetime
import os
import pytz
import asyncio
from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "Bot is alive!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='/', intents=intents)
tree = bot.tree

signup_active = False
registered_users = set()
SIGNUP_DURATION = 15
MAX_REGISTRATIONS = 10

IST = pytz.timezone('Asia/Kolkata')

@tasks.loop(minutes=1)
async def check_time():
    now = datetime.now(IST)
    if now.minute == 55 and not signup_active:
        channel = bot.get_channel(1429128659167477883)
        await start_signup(channel)
    elif now.minute == 10 and signup_active:
        channel = bot.get_channel(1429128659167477883)
        await close_signup(channel)

async def start_signup(channel):
    global signup_active
    if channel is None:
        print("Error: Channel not found. Bot may not be in the server or channel ID is incorrect.")
        return

    signup_active = True
    registered_users.clear()

    turfer_role = discord.utils.get(channel.guild.roles, name="TURFER [5]")
    
    if turfer_role:
        await channel.set_permissions(turfer_role, send_messages=True, view_channel=True)
        
    now = datetime.now(IST)

    header = f"{turfer_role.mention if turfer_role else '@TURFER [5]'}\n\n"
    header += f"**TURFER [5] REGISTRATION OPEN**\n\n"
    header += f"Date: {now.strftime('%Y-%m-%d')}\n"
    header += f"Time: {now.strftime('%H:%M')}\n\n"
    header += "First 10 people to write + are registered for this informal.\n"
    header += "Participant list is updated every 1 second.\n\n"
    header += "Participant Count\n0/10\n\n"
    header += "Participants\nNo participants yet"

    await channel.send(header)
    print(f"✓ Registration opened at {now.strftime('%H:%M')}")

async def close_signup(channel):
    global signup_active
    if channel is None:
        print("Error: Channel not found. Bot may not be in the server or channel ID is incorrect.")
        return

    if signup_active:
        signup_active = False
        now = datetime.now(IST)

        turfer_role = discord.utils.get(channel.guild.roles, name="TURFER [5]")
        
        numbered_list = '\n'.join([f"{idx+1}. {user.mention}" for idx, user in enumerate(registered_users)])
        
        message = f"{turfer_role.mention if turfer_role else '@TURFER [5]'}\n\n"
        message += f"**TURFER [5] REGISTRATION CLOSED**\n\n"
        message += f"Date: {now.strftime('%Y-%m-%d')}\n"
        message += f"Time: {now.strftime('%H:%M')}\n\n"
        message += f"Participant Count: {len(registered_users)}/10\n\n"
        message += f"**Final Registered Members:**\n"
        message += f"{numbered_list if numbered_list else 'No participants'}"
        
        await channel.send(message)
        print(f"✓ Registration closed at {now.strftime('%H:%M')} with {len(registered_users)} participants")

        if turfer_role:
            await channel.set_permissions(turfer_role, send_messages=False, view_channel=True)

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    channel = bot.get_channel(1429128659167477883)
    if channel:
        print(f"✓ Bot can access channel: {channel.name} (ID: {channel.id})")
        print(f"  Server: {channel.guild.name}")
    else:
        print("✗ ERROR: Bot cannot find channel 1429128659167477883")
    
    check_time.start()
    await tree.sync()

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if message.channel.id == 1429128659167477883:
        if not signup_active:
            await message.delete()
            return

        if message.content.strip() != '+':
            await message.delete()
            return

        if signup_active and message.content.strip() == '+':
            turfer_role = discord.utils.get(message.guild.roles, name="TURFER [5]")
            
            if turfer_role is None or turfer_role not in message.author.roles:
                await message.delete()
                await message.channel.send(f"{message.author.mention} you need TURFER [5] role to register!", delete_after=5)
                return

            if message.author in registered_users:
                await message.delete()
                await message.channel.send(f"{message.author.mention} you are already registered!", delete_after=5)
                return

            if len(registered_users) >= MAX_REGISTRATIONS:
                await message.delete()
                await message.channel.send(f"{message.author.mention} registration is full, try next hour", delete_after=5)
                return

            registered_users.add(message.author)

            await asyncio.sleep(0.5)
            await message.delete()

            registered_list = '\n'.join([f"{idx+1}. {user.mention}" for idx, user in enumerate(registered_users)])

            now = datetime.now(IST)
            header = f"{turfer_role.mention if turfer_role else '@TURFER [5]'}\n\n"
            header += f"**TURFER [5] REGISTRATION OPEN**\n\n"
            header += f"Date: {now.strftime('%Y-%m-%d')}\n"
            header += f"Time: {now.strftime('%H:%M')}\n\n"
            header += "First 10 people to write + are registered for this informal.\n"
            header += "Participant list is updated every 1 second.\n\n"
            header += f"Participant Count\n{len(registered_users)}/10\n\n"
            header += f"Participants\n{registered_list}"

            async for msg in message.channel.history(limit=50):
                if msg.author == bot.user and "TURFER [5] REGISTRATION" in msg.content:
                    await msg.edit(content=header)
                    break

            if len(registered_users) >= MAX_REGISTRATIONS:
                await close_signup(message.channel)

    await bot.process_commands(message)

@tree.command()
@commands.has_permissions(administrator=True)
async def openreg(interaction: discord.Interaction):
    """Manually open registration (Admin only)"""
    global signup_active
    if signup_active:
        await interaction.response.send_message("Registration is already open!", ephemeral=True)
        return

    channel = bot.get_channel(1429128659167477883)
    if channel is None:
        await interaction.response.send_message("Error: Cannot find the registration channel.", ephemeral=True)
        return

    await start_signup(channel)
    await interaction.response.send_message("Registration has been opened manually.", ephemeral=True)

@tree.command()
@commands.has_permissions(administrator=True)
async def closereg(interaction: discord.Interaction):
    """Manually close registration (Admin only)"""
    global signup_active
    if not signup_active:
        await interaction.response.send_message("Registration is already closed!", ephemeral=True)
        return

    channel = bot.get_channel(1429128659167477883)
    if channel is None:
        await interaction.response.send_message("Error: Cannot find the registration channel.", ephemeral=True)
        return

    await close_signup(channel)
    await interaction.response.send_message("Registration has been closed manually.", ephemeral=True)

if __name__ == "__main__":
    TOKEN = os.getenv('DISCORD_TOKEN')
    if not TOKEN:
        raise ValueError("Please set DISCORD_TOKEN in the Secrets tab")
    keep_alive()
    bot.run(TOKEN)
