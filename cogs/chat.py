import sys

import cleverbotfree.cbfree
import discord
from discord.ext import commands
from selenium import webdriver

from bot import CTBot

driver = webdriver.Firefox(executable_path="/usr/local/bin/geckodriver")
driver.get("http://inventwithpython.com")

cb = cleverbotfree.cbfree.Cleverbot()


class Chat(commands.Cog):
    def __init__(self, bot: CTBot):
        self.bot = bot

    @commands.command(description="Enter chat")
    async def chat(self, ctx: commands.Context):
        try:
            cb.browser.get(cb.url)
        except:
            cb.browser.close()
            sys.exit()
        while True:
            try:
                cb.get_form()
            except:
                sys.exit()

            def check(m: discord.Message):
                return m.author.id == ctx.author.id and m.channel.id == ctx.channel.id

            msg = await self.bot.wait_for("message", check=check)
            input_text: object = msg.content
            user_input = str(input_text)
            if user_input == "quit":
                break
            cb.send_input(user_input)
            resp = cb.get_response()
            await ctx.send(str(resp))
        cb.browser.close()


def setup(bot: CTBot):
    bot.add_cog(Chat(bot))
