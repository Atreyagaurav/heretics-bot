import os
import sys
import re
import asyncio
import discord
import commands
import admin_commands
import privilege_commands
import config
import time
import scrapper
import utilities


if __name__ == "__main__":
    # delay just in case internet isn't connected at startup.
    if len(sys.argv) == 1 or sys.argv[1] != "-nd":
        time.sleep(60)

client = discord.Client()


@client.event
async def on_ready():
    print(f'{client.user} has connected to Discord.')
    for g in client.guilds:
        print(f'Connected to: {g.name} :id={g.id}')


@client.event
async def on_message(message):
    # if message.author == client.user:
    #     return
    # just a hack to make itself give command to self.
    m = config.bot_pattern.match(message.content.lower())
    if not m:
        return
    cmd = m.group(1)
    args = m.group(2)
    print(f'User: {message.author} Command: {cmd} Args: {args}')

    if args.strip() == 'help':
        # If `command help` is used convert it to `help command`
        cmd, args = 'help', cmd
    
    with open(config.log_file, 'a') as lf:
        lf.write(f'{cmd}: {args}\n')

    if '-m' in sys.argv:
        # Get the reply from terminal if run on the manual mode
        rep = input("Enter reply<default>: ")
        if rep.strip():
            await message.reply(rep)
            return

    # Finding the appropriate function to call
    if utilities.is_admin(message):
        try:
            cmd_func = getattr(admin_commands, f'cmd_{cmd.lower()}')
        except AttributeError:
            cmd_func = admin_commands.cmd_message
    elif utilities.is_privileged(message):
        try:
            cmd_func = getattr(privilege_commands, f'cmd_{cmd.lower()}')
        except AttributeError:
            cmd_func = privilege_commands.cmd_message
    else:
        try:
            cmd_func = getattr(commands, f'cmd_{cmd.lower()}')
        except AttributeError:
            cmd_func = commands.cmd_message

    # Calling the function
    try:
        await cmd_func(message, args)
    except Exception as e:
        with open(config.log_file, 'a') as lf:
            lf.write(f'{e}\n')
        print(f"Error logged to {config.log_file}")
    

        # lf.write(str(e.__traceback__)+'\n')


@client.event
async def on_reaction_add(reaction, user):
    print(f'Reaction:{reaction.emoji} User:{user}')
    if reaction.emoji == '❌':
        if utilities.is_admin(reaction.message):
            await reaction.message.delete()
            return
        if reaction.message.reference:
            parent = reaction.message.reference.resolved
            if parent:
                if parent.author == user:
                    await reaction.message.delete()


def get_new_chapter_no():
    with open(config.temp_file, 'r') as r:
        url = r.read().strip()
    m = config.ncode_pattern.match(url)
    novel = m.group(3)
    chapter = int(m.group(4)) + 1
    try:
        next_chap = scrapper.chap_url.substitute(novel=novel, chapter=chapter)
        raw_file = os.path.join(config.root_path,
                                f'data/{novel}_{chapter}-jp.txt')
        scrapper.save_chapter(novel, chapter, filename=raw_file)
    except scrapper.NoChapterException:
        return None, None
    with open(config.temp_file, 'w') as w:
        w.write(next_chap)

    # the chapter number for arc7 starts from 503
    if chapter < 516:
        return chapter - 502, next_chap
    # EX chapter on 516, that's why
    return chapter - 503, next_chap


async def send_chapter_alert(chap_num, chap_url):
    servers = filter(lambda g: g.id in config.inform_guilds, client.guilds)
    for g in servers:
        channel = filter(lambda c: c.name in ['general'], g.channels)
        for c in channel:
            await c.send(config.inform_guilds[g.id] + " chapter-" +
                         f"{chap_num} has been released. ")
            code = "/".join(chap_url.split("/")[-3:-1])
            await c.send(f"b! mtl {code}")
            print(f'msg sent to:{c.name} of {g.name}')


async def check_new_chapter():
    await client.wait_until_ready()
    while True:
        try:
            chap, url = get_new_chapter_no()
            if chap:
                await send_chapter_alert(chap, url)
            else:
                await asyncio.sleep(120)  # checks every 2 minutes
        except KeyboardInterrupt:
            break


if __name__ == '__main__':
    client.loop.create_task(check_new_chapter())
    client.run(config.token)
