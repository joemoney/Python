# This is a discord script to sneakily copy messages from one channel to another like a rat you are. The script will 
# only copy messages from the source channel to the destination channel

import discord
import os
from discord.ext import commands
import asyncio
import random
import argparse
import re
import asyncio

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

######################################################################
# check that the start time is in the format of MM/DD/YYYY HH:MM:SS 
######################################################################
def verify_time_format(startTime: str) -> bool:

    # define the regex pattern for the date and time format
    pattern = r'^(0[1-9]|1[0-2])/([0-2][0-9]|3[01])/([1-9][0-9]{3}) ([0-1][0-9]|2[0-3]):([0-5][0-9]):([0-5][0-9])$'
    
    # match the pattern with the startTime
    if re.match(pattern, startTime):
        return True
    return False

######################################################################
# function to copy the messages from the source channel to the destination channel
######################################################################
async def copy_messages(startTime: str):

        # copy all messages from the source channel to the destination channel starting at the start time defined
        async for message in bot.get_channel(source_channel).history(limit=max_messages):
            # check if the message was created after the start time
            if message.created_at.strftime('%m/%d/%Y %H:%M:%S %Z') >= startTime:
                # create a random number between 1 and 5, integer only
                delay_in_seconds = random.randint(1, 5)
                # wait for the random number of seconds to prevent rate limiting or getting detected by discord for botting
                # a user account since this is techincally against the Discord TOS
                await asyncio.sleep(delay_in_seconds)
                # send the message to the destination channel with the author and content  
                await bot.get_channel(destination_channel).send(f'{message.author}: {message.content}')

######################################################################
# Event: When the bot is ready
######################################################################
@bot.event
async def on_ready():
    # log the action of the bot
    print(f'Logged in as {bot.user.name} ({bot.user.id})')
    print('Its ratting out time!')
    print('-----------------------')
    
    # if mode is SE, then start copying the messages
    if args.mode == 'SE':
        print('Verifying time format...')
        # verify that the start time is in the correct format
        if verify_time_format(args.startTime):
            print('Starting to rat out...')
            # start copying the messages
            try:
                await copy_messages(args.startTime)
                print('Ratting out complete')
            except Exception as e:
                print(f'Error encountered: {e}. Check that the channel IDs are correct')
        else:
            print('Error: Start time is not in the format of MM/DD/YYYY HH:MM:SS')

    # exiting the script, this will generate a runtime error but that is fine since the script is done
    await bot.close()


######################################################################
# Command: rat_out, copy messages from source channel to destination channel. Define the start time as local time and is part of the command
######################################################################
@bot.command(name='rat_out', help='Copy messages from source channel to destination channel. Time must be in the format of MM/DD/YYYY HH:MM:SS and the timezone is EST')
async def rat_out(ctx, start_time: str):

    # only continue if mode is BC
    if args.mode != 'BC':
        return
    
    print('Verifying time format...')
    # verify that the start time is in the correct format
    if not verify_time_format(start_time):
        await ctx.send('Error: Start time is not in the format of MM/DD/YYYY HH:MM:SS')
        return
    
    # log to the requester the bot action
    await ctx.send('Starting to rat out...')

    # start copying the messages
    try:
        await copy_messages(bot, start_time)
    except Exception as e:
        await ctx.send(f'Error encountered: {e}. Check that the channel IDs are correct')

    # log to the requester that the request has been fulfilled
    await ctx.send('Ratting out complete')

######################################################################
# main function to parse the command line arguments and run the bot, this is the entry point of the script
######################################################################
def main():
    # parse the command line arguments
    parser = argparse.ArgumentParser(description='Copy messages from source channel to destination channel')
    # mode type argument, required, choices are 'SE' for Script Execution or 'BC' for Bot Command
    parser.add_argument('--mode', type=str, help='Mode type, SE for Script Execution or BC for Bot Command')
    # start time argument, required if mode is SE
    parser.add_argument('--startTime', type=str, default='', help='Start time in the format of MM/DD/YYYY HH:MM:SS')
    # restricted argument, required if mode is BC, choices are 'Yes' or 'No'
    parser.add_argument('--restricted', type=str, default='No', help='Restricted mode, Yes or No')

    # parse the arguments
    global args
    args = parser.parse_args()
    # Run the bot
    print('Starting the bot...')
    bot.run(TOKEN)


######################################################################
# run the main function
######################################################################
if __name__ == '__main__':
    main()

