import os
import subprocess
import requests

from functools import wraps

import discord
import scrapper
import deepl
import config


async def no_role_msg(message, args):
    """this function is to reply any messages that are not associated with
any commands.
Usage: <your message that doesn't start with a command.>
    """
    await message.reply('Command not authorized, please make sure' +
                        ' you have the required role for this command.')


def restrict_roles(roles):
    """Decorator to restrict the given command to a set of roles.
    """
    def wrapper(func):
        @wraps(func)
        async def actual_func(msg, args):
            user_roles= {r.name.lower() for r in msg.author.roles}
            if user_roles.intersection(roles) or is_admin(msg):
                return await func(msg, args)
            return await no_role_msg(msg, args)
        return actual_func
    return wrapper


def is_admin(message):
    is_admin = False
    if message.channel.guild.id in config.admin_guilds:
        is_admin = True

    user_roles= {r.name.lower() for r in message.author.roles}
    if user_roles.intersection(config.admin_roles):
        is_admin = True

    # bot's userID to be able to give itself admin command evereywhere.
    if message.author.id == config.BOT_ID:
        # if I want to test as non admin user then `B!` will work.
        if message.content[0] == 'B':
            is_admin = False
        else:
            is_admin = True
    return is_admin


def is_privileged(message):
    is_privileged = is_admin(message)

    user_roles= {r.name.lower() for r in message.author.roles}
    if user_roles.intersection(config.privileged_roles):
        is_privileged = True

    return (is_privileged or
            message.channel.guild.id in config.privileged_guilds)


def parse_novel(title, chapter):
    title = config.novels.get(title, title)
    return title, chapter


async def reply_file(message, filename, content=""):
    f = open(filename, 'rb')
    df = discord.File(fp=f)
    await message.reply(file=df, content=content)
    f.close()


async def from_ncode(novel, chapter, message, filename=None, upload_file=True):
    if filename is None:
        filename = os.path.join(config.root_path,
                                f'data/{novel}_{chapter}-jp.txt')
    if os.path.isfile(filename):
        if upload_file:
            await reply_file(message, filename)
        return filename
    url = scrapper.chap_url.substitute(novel=novel, chapter=chapter)
    await message.channel.send(f'Just a sec, I\'ll go visit ncode website.')
    try:
        filename = scrapper.save_chapter(novel, chapter, filename=filename)
        if upload_file:
            await reply_file(message, filename, "Here you go.")
        return filename
    except scrapper.NoChapterException:
        await message.reply('The requested chapter is not available.')
        return None
    except Exception as e:
        await channel.send('Something went wrong, message thevoidzero.')
        raise e


async def mtl_ncode(novel, chapter, message, outfile=None):
    rawfile = await from_ncode(novel, chapter, message,
                               filename=outfile, upload_file=False)
    if not rawfile:
        return
    if outfile:
        f, ext = os.path.splitext(outfile)
        if f.endswith('jp'):
            outfile = f[-2:] + 'en' + ext
        elif not f.endswith('en'):
            outfile = f + 'en' + ext
    else:
        outfile = os.path.join(config.root_path,
                               f'data/{novel}_{chapter}-en.txt')
    if not os.path.isfile(outfile):
        await message.reply("The translation might take a while, I'll upload when it's finished.")
        if deepl.web is None:
            await deepl.init_web()
        await deepl.translate(rawfile, outfile)
    await reply_file(message, outfile, "Here you go.")



def get_images(message):
    if not message:
        return
    for attch in message.attachments:
        if 'image' not in attch.content_type:
            yield None
        i = 0
        temp_img_file = f"{attch.filename}"
        while True:
            if not os.path.exists(f"/tmp/{temp_img_file}"):
                break
            temp_img_file = f"{i}_{attch.filename}"
            i += 1
        with open(f"/tmp/tm-{temp_img_file}", "wb") as w:
            r = requests.get(attch.url)
            w.write(r.content)
        subprocess.Popen(f'convert /tmp/tm-{temp_img_file} -bordercolor White -border 10x10 /tmp/{temp_img_file}',
                         shell=True).wait()
        os.remove(f'/tmp/tm-{temp_img_file}')
        yield temp_img_file
    if message.reference:
        yield from get_images(message.reference.resolved)
