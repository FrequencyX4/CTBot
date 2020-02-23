import asyncio
import json
import traceback
from os import path

import discord
from discord.ext import commands

from utils import utils


class CTBot(commands.Bot):
    def __init__(self, log_func=None, **options):
        if log_func:
            self.log_func = log_func
        self.config = {}
        self._data = {}
        self._sema = {}
        for name in "appeal_ban", "coin", "core_commands", "levels":
            self._data[name] = {}
            self._sema[name] = asyncio.Semaphore()

        self.load()

        super().__init__(
            commands.when_mentioned_or(self.config["prefix"]),
            activity=discord.Game(name="Back Online"),
            **options,
        )

        self.remove_command("help")

    def __getattr__(self, item):
        if item in self._data:
            asyncio.create_task(self._sema[item].acquire())
            return self._data[item]
        else:
            raise AttributeError(f"CTBot has no attribute '{item}'")

    def load(self):
        try:
            asyncio.get_running_loop()
            for sema in self._sema.values():
                sema.release()
                asyncio.create_task(sema.acquire())
        except RuntimeError:
            pass

        with open("config/config.json") as f:
            old_config = self.config
            self.config = json.load(f)
            for k in old_config:  # To only add fields, not replace the existing ones
                self.config[k] = old_config[k]

        for name in self._data:
            if path.isfile(f"data/{name}.json"):
                with open(f"data/{name}.json") as f:
                    self._data[name] = json.load(f)
            else:
                with open(f"data/{name}.json", "w") as f:
                    json.dump(self._data[name], f, ensure_ascii=False)

        for sema in self._sema.values():
            sema.release()

    async def save(self):
        for sema in self._sema.values():
            sema.release()
            await sema.acquire()

        for name in self._data:
            with open(f"data/{name}.json", "w") as f:
                json.dump(self._data[name], f, ensure_ascii=False)

        for sema in self._sema.values():
            sema.release()

    def run(self):
        super().run(self.config["token"])

    async def reload(self):
        """Reloads all extensions."""
        await self.change_presence(
            status=discord.Status.dnd, activity=discord.Game(name="Reloading")
        )
        await self.save()
        self.load()
        self.command_prefix = self.config["prefix"]
        await self.log("Reload", "Reloaded config")
        errors = []
        for ext in self.extensions:
            try:
                self.reload_extension(ext)
                await self.log("Reload", f"Reloaded `{ext}`...")
            except commands.ExtensionError:
                errors.append((ext, str(traceback.format_exc())))
                await self.log("Reload", f"Failed to reload `{ext}`")
        for ext, error in errors:
            await self.log(
                f"Reload",
                f"Error reloading `{ext}`:\n```{error}```",
                utils.LogLevel.ERROR,
            )

        await self.change_presence(
            status=discord.Status.online, activity=discord.Game(name="Back Online")
        )

    async def log(
            self, title: str, description: str, level: utils.LogLevel = utils.LogLevel.INFO
    ):
        if self.log_func:
            self.log_func(title, description, level)
        if level.value >= self.config["log_level"]:
            e = discord.Embed(
                color=utils.get_color(self, level),
                title=title,
                description=description[:1997],
            )
            text = [
                description[i: i + 1991] for i in range(1997, len(description), 1991)
            ]
            code = description[:1997].count("```") % 2 == 1
            if code:
                e.description += "```"
            for group in text:
                g = group
                if code:
                    g = "```py\n" + g
                if group.count("```") % 2 == 1:
                    code = not code
                if code:
                    g += "```"
                e.add_field(name=".", value=g)
            await self.get_channel(self.config["ids"]["log_channel"]).send(embed=e)
