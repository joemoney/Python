Are locked out from a private channel in a discord server?

Do you want to know if they talk shit about you in that channel?

Do you have a friend or in that private channel that can be your personal rat?

Then this script will be your ticket, your friend will be able to rat them out to you sneakily without the other users noticing.

## REQUIREMENTS
- A private discord channel that you want to spy on. Get the channel ID and this will be the source channel
- A discord channel you want to copy the message to. Get the channel ID and this will be the destination channel
- A friend in the private discord channel that can rat them out for you
- Python must be installed on the friend's PC
- Discord.py python module must be installed on the friend's PC after installing Python


## INSTALLATION INSTRUCTION
- Download Python from https://www.python.org/downloads/ and install it
- Once python is installed, install the discord.py python module by typing the following command in the command prompt
`> python.exe -M pip install discord`
- Add the token of the bot/account you want to use as the rat to the system environment variables by typing the following command
`> set DISCORD_BOT_TOKEN="<insert token here>"`
- Get the source and destination channel IDs and update the python script with the values
- <b>OPTIONAL :</b> Get your own User ID if you want the bot command to only activate on your account

## USAGE
Run the script in command prompt inside the folder the script is located. There are two ways to use the script. <b>Script Execution or Bot Command</b>
### Script Execution
When running in Script Execution, it will immediately copy from the source channel to the destination channel starting from the time you use as the parameter and will immediately close the script

<b>Command Prompt:</b>
`python.exe joeBot.py -mode SE -startTime "MM/DD/YYYY HH:MM:SS"`

### Bot Command

When running in Bot Command, the script will continously run waiting for the trigger command. Once the trigger command is received via DM of the account running the script. There is an option if you want the command to only activate on your discord account

<b>Command Prompt:</b>
`python.exe joeBot.py -mode BC -Resticted <Yes/No>`




