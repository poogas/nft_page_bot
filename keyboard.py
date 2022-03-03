from aiogram import types
from loader import bot
from app import get_box_sale_info

base_url = 'https://www.binance.com/ru/nft'
last_page = {'last_page': 0}


async def send_inline_url(msg, name, price, product_id):
    url = ('/goods/blindBox/detail?'
           f'productId={product_id}&isOpen=false&isProduct=1')

    button = types.InlineKeyboardButton(text=f'{price} BUSD',
                                        url=f'{base_url}{url}')

    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(button)

    await bot.send_message(msg.from_user.id, f'{name}', reply_markup=keyboard)


async def kb(page):
    box_info_json = await get_box_sale_info(page)
    box_name_list = [item['name'] for item in box_info_json['data']]

    buttons = [types.InlineKeyboardButton(text=f"{box_name}",
               callback_data=f"name_{box_name}")
               for box_name in box_name_list]

    keyboard = types.InlineKeyboardMarkup(row_width=2)

    button_next = types.InlineKeyboardButton(text='next',
                                             callback_data=f"nav_next_{page}")

    button_past = types.InlineKeyboardButton(text='past',
                                             callback_data=f"nav_past_{page}")

    keyboard.add(*buttons)

    if page == 1:
        keyboard.add(button_next)
    elif box_name_list:
        if last_page['last_page'] == page:
            keyboard.add(button_past)
        else:
            keyboard.add(button_past, button_next)
    else:
        return 'last_page'

    return keyboard


async def get_last_page(page):
    while True:
        result = await kb(page)

        if 'last_page' in result:
            return page - 1
            break

        page += 1


async def send_inline_keyboard(msg):
    last_page['last_page'] = await get_last_page(1)

    keyboard = await kb(1)

    await bot.send_message(msg.from_user.id,
                           'Please select one of Mystery box:',
                           reply_markup=keyboard)


async def callback_inline_nav(call):
    data = call.data.split('_')
    page = data[2]
    action = data[1]

    await call.answer()

    if 'next' in action:
        keyboard = await kb(int(page) + 1)
        await call.message.edit_reply_markup(keyboard)
    else:
        keyboard = await kb(int(page) - 1)
        await call.message.edit_reply_markup(keyboard)
