# This is a discord script to sneakily copy messages from one channel to another like a rat you are. The script will 
# only copy messages from the source channel to the destination channel

import discord
import os
from discord.ext import commands
import asyncio
import random

# Please, for the love of what is holy and pure, store your bot/account token in the windows system environment
# DO NOT HARD CODE YOUR TOKEN IN THIS FILE YOU DUMBFUCKS!!!!!! Because once this file is spread on the internet
# and someone gets a hold of your token, they can do whatever they want with your bot/account and you will have
# a very, very, very bad day
TOKEN = os.getenv('DISCORD_BOT_TOKEN')

# Define the bot and the command prefix, with default intents
bot = commands.Bot(command_prefix='!', intents=discord.Intents.default())

# Define the Source Channel, Destination Channel, and Specific User ID that can use the command
source_channel = 268196447667617803
destination_channel = 448575039676088350
specific_user_id = 231071537048846336

# Define the maximum number of messages to copy
max_messages = 100

# Event: When the bot is ready
@bot.event
async def on_ready():
    # log the action of the bot
    print(f'Logged in as {bot.user.name} ({bot.user.id})')
    print('Its ratting out time!')
    print('-----------------------')

# Command: rat_out, copy messages from source channel to destination channel. Define the start time as local time and is part of the command
@bot.command(name='rat_out', help='Copy messages from source channel to destination channel. Time must be in the format of MM/DD/YYYY HH:MM:SS and the timezone is EST')
async def rat_out(ctx, start_time: str):

    #check that the command is being called from a DM and only a specific user can use this command
    if isinstance(ctx.channel, discord.DMChannel) and ctx.author.id != 231071537048846336:
        await ctx.send('Fuck off, I don\'t know you')
        return
    
    # log to the requester the bot action
    await ctx.send('Verifying input parameters...')

    # verify that the source and destination channels are defined
    if source_channel is None or destination_channel is None:
        await ctx.send('Error: Source and Destination channels are not defined')
        return
   
    # verify that the time is in the format of MM/DD/YYYY HH:MM:SS
    if len(start_time) != 19:
        await ctx.send(f'Error: Start time is not in the format of MM/DD/YYYY HH:MM:SS, current length is {len(start_time)}')
        return
    else:
        # format the time in seconds
        start_time = f'{start_time} EST'

    # log to the requester the bot action
    await ctx.send('Starting to rat out...')

    # copy all messages from the source channel to the destination channel starting at the start time defined
    async for message in bot.get_channel(source_channel).history(limit=max_messages):
        # check if the message was created after the start time
        if message.created_at.strftime('%m/%d/%Y %H:%M:%S %Z') >= start_time:
            # create a random number between 1 and 5, integer only
            delay_in_seconds = random.randint(1, 5)
            # wait for the random number of seconds to prevent rate limiting or getting detected by discord for botting
            # a user account since this is techincally against the Discord TOS
            await asyncio.sleep(delay_in_seconds)
            # send the message to the destination channel with the author and content  
            await bot.get_channel(destination_channel).send(f'{message.author}: {message.content}')
    
    # log to the requester that the request has been fulfilled
    await ctx.send('Ratting out complete')

# Run the bot
print('Starting the bot...')
bot.run(TOKEN)

