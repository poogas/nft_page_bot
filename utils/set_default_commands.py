from aiogram import types


async def set_default_commands(dp):
    await dp.bot.set_my_commands(
        [
            types.BotCommand("start", "start bot and box menu"),
            types.BotCommand("set", "find a box at the specified price and below"),
            types.BotCommand("stop", "stops searching"),
            types.BotCommand("min", "find out the minimum price"),
            types.BotCommand("delay", "information about the time of the delay after the sale")
        ]
    )
