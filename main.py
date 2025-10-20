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



# Define IST timezone globally
IST = pytz.timezone('Asia/Kolkata')

@tasks.loop(minutes=1)
async def check_time():
    now = datetime.now(IST)
    current_hour = now.hour
    # Check if it's the correct time (every hour at XX:55)
    if now.minute == 55 and not signup_active:
        channel = bot.get_channel(1429128659167477883)
        await start_signup(channel)
    # Close registration at XX:10
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

    # Get roles
    informal_role = discord.utils.get(channel.guild.roles, name="Carnix Inc. Informal")
    turfer_role = discord.utils.get(channel.guild.roles, name="TURFER [5]")
    
    # Set permissions: İnformal can send messages, TURFER cannot
    if informal_role:
        await channel.set_permissions(informal_role, send_messages=True, view_channel=True)
    if turfer_role:
        await channel.set_permissions(turfer_role, send_messages=False, view_channel=True)
        
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.now(ist)

    # Build the header message
    header = f"Carnix Inc. Informal\n"
    header += f"Date: {now.strftime('%Y-%m-%d')}\n"
    header += f"Time: {now.strftime('%H:%M')}\n\n"
    header += "First 10 people to write + are registered for this informal.\n"
    header += "Participant list is updated every 1 second.\n\n"
    header += "Participant Count\n0/10\n\n"
    header += "Participants\nNo participants yet"

    # Send the header message
    await channel.send(header)
    print(f"✓ Registration opened at {now.strftime('%H:%M')}")

async def close_signup(channel):
    global signup_active

    if channel is None:
        print("Error: Channel not found. Bot may not be in the server or channel ID is incorrect.")
        return

    if signup_active:
        signup_active = False
        ist = pytz.timezone('Asia/Kolkata')
        now = datetime.now(ist)
        informal_role = discord.utils.get(channel.guild.roles, name="Carnix Inc. Informal")

        if informal_role is None:
            print("Error: İnformal role not found.")
            return

        header = f"Espada: <@&{informal_role.id}>\nEspada Informal\nDate: {now.strftime('%Y-%m-%d')}\nTime: {now.strftime('%H:%M')}\n\n"
        header += "**REGISTRATION CLOSED**\n\n"
        header += f"Participant Count\n{len(registered_users)}/10\n\nParticipants\n"
        numbered_list = '\n'.join([f"{idx+1}. {user.mention}" for idx, user in enumerate(registered_users)])
        await channel.send(f"{header}{numbered_list}")

        # Lock channel for İnformal - view only when registration is closed
        if informal_role:
            await channel.set_permissions(informal_role, send_messages=False, view_channel=True)

        # Tag TURFER [5] role and open channel for 15 minutes
        turfer_role = discord.utils.get(channel.guild.roles, name="TURFER [5]")
        if turfer_role:
            # Open channel for TURFER [5] role
            await channel.set_permissions(turfer_role, send_messages=True, view_channel=True)
            
            # Send message tagging TURFER [5] with participant list
            turfer_message = f"{turfer_role.mention}\n\n"
            turfer_message += f"**Espada Informal**\n"
            turfer_message += f"Date: {now.strftime('%Y-%m-%d')}\n"
            turfer_message += f"Time: {now.strftime('%H:%M')}\n\n"
            turfer_message += f"Registration is now closed. Channel is open for 15 minutes.\n\n"
            turfer_message += f"**Participant Count: {len(registered_users)}/10**\n\n"
            turfer_message += f"**Participants:**\n{numbered_list}"
            
            await channel.send(turfer_message)
            
            # Schedule channel closure for TURFER [5] after 15 minutes using a background task
            async def close_turfer_access():
                await asyncio.sleep(900)  # 900 seconds = 15 minutes
                await channel.set_permissions(turfer_role, send_messages=False, view_channel=True)
                await channel.send(f"Channel closed for {turfer_role.mention}. See you next time!", delete_after=10)
            
            # Run the closure task in the background
            bot.loop.create_task(close_turfer_access())




@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    
    # Debug: Check if bot can see the channel
    channel = bot.get_channel(1429128659167477883)
    if channel:
        print(f"✓ Bot can access channel: {channel.name} (ID: {channel.id})")
        print(f"  Server: {channel.guild.name}")
    else:
        print("✗ ERROR: Bot cannot find channel 1429128659167477883")
        print("  Available channels:")
        for guild in bot.guilds:
            print(f"  Server: {guild.name}")
            for ch in guild.text_channels:
                print(f"    - {ch.name} (ID: {ch.id})")
    
    check_time.start()
    await tree.sync()

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("You don't have permission to use this command!")
    elif isinstance(error, commands.errors.CommandNotFound):
        await ctx.send("Command not found. Available commands: /openreg, /closereg")

@bot.event
async def on_message(message):
    # Don't process bot's own messages
    if message.author == bot.user:
        return

    # Delete non-plus messages in registration channel
    if message.channel.id == 1429128659167477883:
        # If registration is not active, delete all user messages
        if not signup_active:
            await message.delete()
            return

        # During registration, only allow '+' messages
        if message.content.strip() != '+':
            await message.delete()
            return

        if signup_active and message.content.strip() == '+':
            informal_role = discord.utils.get(message.guild.roles, name="Carnix Inc. Informal")

            # Check if user has Carnix Inc. Informal role
            if informal_role is None or informal_role not in message.author.roles:
                await message.delete()
                await message.channel.send(f"{message.author.mention} you need TURFER [5] role and Carnix Inc. Informal role to register!", delete_after=5)
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
            
            # Don't delete the + message immediately - let it stay briefly
            await asyncio.sleep(0.5)
            await message.delete()

            # Create formatted list of participants
            registered_list = '\n'.join([f"{idx+1}. {user.mention}" for idx, user in enumerate(registered_users)])

            # Update the registration message
            ist = pytz.timezone('Asia/Kolkata')
            now = datetime.now(ist)
            header = f"Carnix Inc. Informal\n"
            header += f"Date: {now.strftime('%Y-%m-%d')}\n"
            header += f"Time: {now.strftime('%H:%M')}\n\n"
            header += "First 10 people to write + are registered for this informal.\n"
            header += "Participant list is updated every 1 second.\n\n"
            header += f"Participant Count\n{len(registered_users)}/10\n\n"
            header += f"Participants\n{registered_list}"

            # Find and edit the first message in the channel
            async for msg in message.channel.history(limit=50):
                if msg.author == bot.user and "Carnix Inc. Informal" in msg.content:
                    await msg.edit(content=header)
                    break

            # Close registration if full
            if len(registered_users) >= MAX_REGISTRATIONS:
                await close_signup(message.channel)

    await bot.process_commands(message)

@bot.event
async def on_message_delete(message):
    # Check if deletion happened in registration channel
    if message.channel.id == 1429128659167477883:
        # Check if the deleted message was a '+' from a registered user
        if message.content == '+' and message.author in registered_users:
            # Remove user from registered list
            registered_users.discard(message.author)
            
            # If registration was closed and full, reopen it
            if not signup_active and len(registered_users) < MAX_REGISTRATIONS:
                await reopen_registration(message.channel)
            
            # Update the registration message if signup is still active
            if signup_active:
                await update_registration_message(message.channel)

async def reopen_registration(channel):
    global signup_active
    signup_active = True
    
    # Unlock channel for Carnix Inc. Informal
    informal_role = discord.utils.get(channel.guild.roles, name="Carnix Inc. Informal")
    if informal_role:
        await channel.set_permissions(informal_role, send_messages=True, view_channel=True)
    
    await channel.send("Registration has been reopened due to a participant leaving!", delete_after=10)
    await update_registration_message(channel)

async def update_registration_message(channel):
    informal_role = discord.utils.get(channel.guild.roles, name="Carnix Inc. Informal")
    if not informal_role:
        return
    
    # Create formatted list of participants
    registered_list = '\n'.join([f"{idx+1}. {user.mention}" for idx, user in enumerate(registered_users)])
    
    # Update the registration message
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.now(ist)
    header = f"Carnix Inc. Informal\n"
    header += f"Date: {now.strftime('%Y-%m-%d')}\n"
    header += f"Time: {now.strftime('%H:%M')}\n\n"
    header += "First 10 people to write + are registered for this informal.\n"
    header += "Participant list is updated every 1 second.\n\n"
    header += f"Participant Count\n{len(registered_users)}/10\n\n"
    header += f"Participants\n{registered_list}"
    
    # Find and edit the first message in the channel
    async for msg in channel.history(limit=50):
        if msg.author == bot.user and "Carnix Inc. Informal" in msg.content:
            await msg.edit(content=header)
            break



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

    channel = bot.get_channel(1429128659167477883)
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
