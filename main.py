import discord
from discord.ext import commands, tasks
from datetime import datetime, timedelta
import os
import pytz
import asyncio

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='/', intents=intents)
tree = bot.tree

# Store signup data
signup_active = False
registered_users = set()
SIGNUP_DURATION = 15  # minutes
MAX_REGISTRATIONS = 10

# Strike system
strikes = {}

# Define IST timezone globally
IST = pytz.timezone('Asia/Kolkata')

@tasks.loop(minutes=1)
async def check_time():
    now = datetime.now(IST)
    current_hour = now.hour
    # Check if it's the correct time (every hour at XX:55)
    if now.minute == 55 and not signup_active:
        channel = bot.get_channel(1378137911987404940)
        await start_signup(channel)
    # Close registration at XX:10
    elif now.minute == 10 and signup_active:
        channel = bot.get_channel(1378137911987404940)
        await close_signup(channel)

async def start_signup(channel):
    global signup_active

    if channel is None:
        print("Error: Channel not found. Bot may not be in the server or channel ID is incorrect.")
        return

    signup_active = True
    registered_users.clear()

    # Unlock channel for Informals - allow sending messages during registration
    informal_role = discord.utils.get(channel.guild.roles, name="İnformal")
    if informal_role:
        await channel.set_permissions(informal_role, send_messages=True, view_channel=True)
        ist = pytz.timezone('Asia/Kolkata')
        now = datetime.now(ist)

        header = f"Espada: <@&{informal_role.id}>\nEspada Informal\nDate: {now.strftime('%Y-%m-%d')}\nTime: {now.strftime('%H:%M')}\n\n"
        header += "First 10 people to write + are registered for this informal.\nParticipant list is updated every 1 second.\n\n"
        header += "Participant Count\n0/10\n\nParticipants"

        await channel.send(header)

async def close_signup(channel):
    global signup_active

    if channel is None:
        print("Error: Channel not found. Bot may not be in the server or channel ID is incorrect.")
        return

    if signup_active:
        signup_active = False
        ist = pytz.timezone('Asia/Kolkata')
        now = datetime.now(ist)
        informal_role = discord.utils.get(channel.guild.roles, name="İnformal")

        if informal_role is None:
            print("Error: İnformal role not found.")
            return

        header = f"Espada: <@&{informal_role.id}>\nEspada Informal\nDate: {now.strftime('%Y-%m-%d')}\nTime: {now.strftime('%H:%M')}\n\n"
        header += "**REGISTRATION CLOSED**\n\n"
        header += f"Participant Count\n{len(registered_users)}/10\n\nParticipants\n"
        numbered_list = '\n'.join([f"{idx+1}. {user.mention}" for idx, user in enumerate(registered_users)])
        await channel.send(f"{header}{numbered_list}")

        # Lock channel for Informals - view only when registration is closed
        informal_role = discord.utils.get(channel.guild.roles, name="İnformal")
        if informal_role:
            await channel.set_permissions(informal_role, send_messages=False, view_channel=True)
            await channel.send(f"Registration closed. {informal_role.mention} members can now only view messages.", delete_after=10)

async def add_strike(member, guild):
    strikes[member.id] = strikes.get(member.id, 0) + 1
    strike_count = strikes[member.id]

    # Remove old strike roles
    for i in range(1, 6):
        role = discord.utils.get(guild.roles, name=f"⚠️ {i} Strikes")
        if role and role in member.roles:
            await member.remove_roles(role)

    # Add new strike role
    if strike_count <= 5:
        role = discord.utils.get(guild.roles, name=f"⚠️ {strike_count} Strikes")
        if role:
            await member.add_roles(role)

    # Handle 5 strikes
    if strike_count >= 5:
        informal_role = discord.utils.get(guild.roles, name="İnformal")
        if informal_role and informal_role in member.roles:
            await member.remove_roles(informal_role)
            await asyncio.sleep(5 * 3600)  # Wait 5 hours
            await member.add_roles(informal_role)

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    check_time.start()
    await tree.sync()

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("You don't have permission to use this command!")
    elif isinstance(error, commands.errors.CommandNotFound):
        await ctx.send("Command not found. Available commands: /openreg, /closereg, /removestrike")

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    # Delete non-plus messages in registration channel
    if message.channel.id == 1378137911987404940:
        if not signup_active:
            await message.delete()
            if message.author != bot.user:
                strike_channel = bot.get_channel(1395256424715522098)
                strike_count = strikes.get(message.author.id, 0) + 1
                strike_msg = f"🚨 Strike Issued\nUser: {message.author.mention}\nReason: Sending message after registration closed\nStrike Count: {strike_count}/5\nIssued by: Espada Signup Bot"
                await strike_channel.send(strike_msg)
                await add_strike(message.author, message.guild)
            return

        if message.content != '+' and message.author != bot.user:
            await message.delete()
            strike_channel = bot.get_channel(1395256424715522098)
            strike_count = strikes.get(message.author.id, 0) + 1
            strike_msg = f"🚨 Strike Issued\nUser: {message.author.mention}\nReason: Sending inappropriate message during registration\nStrike Count: {strike_count}/5\nIssued by: Espada Signup Bot"
            await strike_channel.send(strike_msg)
            await add_strike(message.author, message.guild)
            return

        if signup_active and message.content.strip() == '+':
            informal_role = discord.utils.get(message.guild.roles, name="İnformal")

            # Check if user has Informals role
            if informal_role not in message.author.roles:
                await message.delete()
                strike_channel = bot.get_channel(1395256424715522098)
                strike_count = strikes.get(message.author.id, 0) + 1
                strike_msg = f"🚨 Strike Issued\nUser: {message.author.mention}\nReason: Tried to register without Informals role\nStrike Count: {strike_count}/5\nIssued by: Espada Signup Bot"
                await strike_channel.send(strike_msg)
                await add_strike(message.author, message.guild)
                return

            # Check if already registered
            if message.author in registered_users:
                await message.delete()
                await message.channel.send(f"{message.author.mention} you are already registered!", delete_after=5)
                return

            # Check if registration is full
            if len(registered_users) >= MAX_REGISTRATIONS:
                await message.delete()
                await message.channel.send(f"{message.author.mention} registration is full, try next hour", delete_after=5)
                return

            # Add user to registered list
            registered_users.add(message.author)

            # Create formatted list of participants
            registered_list = '\n'.join([f"{idx+1}. {user.mention}" for idx, user in enumerate(registered_users)])

            # Update the registration message
            ist = pytz.timezone('Asia/Kolkata')
            now = datetime.now(ist)
            header = f"Espada: <@&{informal_role.id}>\nEspada Informal\nDate: {now.strftime('%Y-%m-%d')}\nTime: {now.strftime('%H:%M')}\n\n"
            header += "First 10 people to write + are registered for this informal.\nParticipant list is updated every 1 second.\n\n"
            header += f"Participant Count\n{len(registered_users)}/10\n\nParticipants\n{registered_list}"

            # Find and edit the first message in the channel
            async for msg in message.channel.history(limit=50):
                if msg.author == bot.user and "Espada:" in msg.content:
                    await msg.edit(content=header)
                    break

            # Close registration if full
            if len(registered_users) >= MAX_REGISTRATIONS:
                await close_signup(message.channel)
        else:
            await message.delete()
            strike_channel = bot.get_channel(1395256424715522098)
            strike_count = strikes.get(message.author.id, 0) + 1
            strike_msg = f"🚨 Strike Issued\nUser: {message.author.mention}\nReason: Sending inappropriate message during registration\nStrike Count: {strike_count}/5\nIssued by: Espada Signup Bot"
            await strike_channel.send(strike_msg)
            await add_strike(message.author, message.guild)

    await bot.process_commands(message)

@tree.command()
@commands.has_permissions(administrator=True)
async def removestrike(interaction: discord.Interaction, member: discord.Member = None, amount: int = 1):
    if member is None:
        await interaction.response.send_message("Please specify a member to remove strikes from.", ephemeral=True)
        return
    """Remove strikes from a member (Admin only)"""
    if member.id not in strikes or strikes[member.id] <= 0:
        await interaction.response.send_message(f"{member.mention} has no strikes to remove.", ephemeral=True)
        return

    strikes[member.id] = max(0, strikes[member.id] - amount)
    current_strikes = strikes[member.id]

    # Remove all strike roles
    for i in range(1, 6):
        role = discord.utils.get(interaction.guild.roles, name=f"⚠️ {i} Strikes")
        if role and role in member.roles:
            await member.remove_roles(role)

    # Add new strike role if strikes > 0
    if current_strikes > 0:
        new_role = discord.utils.get(interaction.guild.roles, name=f"⚠️ {current_strikes} Strikes")
        if new_role:
            await member.add_roles(new_role)

    await interaction.response.send_message(f"Removed {amount} strike(s) from {member.mention}. Current strikes: {current_strikes}", ephemeral=True)

@tree.command()
@commands.has_permissions(administrator=True)
async def openreg(interaction: discord.Interaction):
    """Manually open registration (Admin only)"""
    global signup_active
    if signup_active:
        await interaction.response.send_message("Registration is already open!", ephemeral=True)
        return

    channel = bot.get_channel(1378137911987404940)
    if channel is None:
        await interaction.response.send_message("Error: Cannot find the registration channel. Make sure the bot is in the server and has proper permissions.", ephemeral=True)
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

    channel = bot.get_channel(1378137911987404940)
    if channel is None:
        await interaction.response.send_message("Error: Cannot find the registration channel. Make sure the bot is in the server and has proper permissions.", ephemeral=True)
        return

    await close_signup(channel)
    await interaction.response.send_message("Registration has been closed manually.", ephemeral=True)

if __name__ == "__main__":
    TOKEN = os.getenv('DISCORD_TOKEN')
    if not TOKEN:
        raise ValueError("Please set DISCORD_TOKEN in the Secrets tab")
    bot.run(TOKEN)