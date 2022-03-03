#!/usr/bin/env python3.9

import asyncio
import aiohttp
from aiogram.utils import executor
from aiogram.dispatcher import FSMContext

from utils.set_default_commands import set_default_commands
from loader import dp, bot
import keyboard

dont_repeat = {}

bapi_url = 'https://www.binance.com/bapi/nft/v1'


async def get_box_info(session, product_id):
    url = f'{bapi_url}/friendly/nft/nft-trade/product-detail'

    async with session.post(f'{url}',
                            json={'productId': product_id}) as response:
        result_json = await response.json()

        assert response.status == 200

        try:
            product_detail = result_json['data']['productDetail']

            if product_detail['status'] == 1 and \
               product_detail['tradeType'] == 0:

                return {'productId': product_detail['id'],
                        'title': product_detail['title'],
                        'price': product_detail['amount'],
                        'token': product_detail['currency'],
                        'count': product_detail['batchNum']}
            else:
                dont_repeat['dont_repeat'].append(product_id)
        except Exception:
            result_json['message']


async def get_need_productId(productId, amount_page, msg):
    if not dont_repeat.setdefault(msg.from_user.id, []) and \
           dont_repeat.setdefault('dont_repeat', []):

        return [productId
                for productId in range(productId, productId + amount_page)]
    else:
        dont_repeat_united = [*dont_repeat[msg.from_user.id],
                              *dont_repeat['dont_repeat']]

        return [productId
                for productId in range(productId, productId + amount_page)
                if productId not in dont_repeat_united]


async def async_get_box_info_all(productId, amount_page, msg):
    product_id = await get_need_productId(productId, amount_page, msg)

    async with aiohttp.ClientSession() as session:
        tasks = [asyncio.create_task(get_box_info(session, id))
                 for id in product_id]

        return await asyncio.gather(*tasks)


async def select_need_box(productId, name, amount_page, want_price, msg):
    result = await async_get_box_info_all(productId, amount_page, msg)
    avail = [item for item in result if type(item) == dict]

    for item in avail:
        product_id = item['productId']

        if item['title'] == name and \
           item['token'] == 'BUSD' and \
           (float(item['price']) / item['count']) <= want_price:

            dont_repeate_united = [*dont_repeat[msg.from_user.id],
                                   *dont_repeat['dont_repeat']]

            if product_id not in dont_repeate_united:
                dont_repeat[msg.from_user.id].append(product_id)
                await keyboard.send_inline_url(msg,
                                               name,
                                               item['price'],
                                               product_id)


async def get_box_market_info(session, page, size, serialsNo):
    payload = {
        "page": page,
        "size": size,
        "params": {
            "nftType": "null",
            "orderBy": "list_time",
            "orderType": "-1",
            "serialNo": [f"{serialsNo}"],
            "tradeType": "0"
        }
    }

    async with session.post(f'{bapi_url}'
                            '/public/nft/market-mystery/mystery-list',
                            json=payload) as response:

        result_json = await response.json()
        assert response.status == 200

        return result_json


async def get_box_min_price_info(page, size, serialsNo):
    async with aiohttp.ClientSession() as session:
        result_json = await get_box_market_info(session, page, size, serialsNo)

        return {item['amount']: [item['currency'],
                item['title']] for item in result_json['data']['data']}


async def get_box_last_productId(serialsNo):
    async with aiohttp.ClientSession() as session:
        result_json = await get_box_market_info(session, 1, 1, serialsNo)

        return [item['productId'] for item in result_json['data']['data']][0]


async def get_box_min_currency(serialsNo, name):
    get_list = await get_box_min_price_info(1, 100, serialsNo)
    get_currency = [amount
                    for amount in get_list
                    if get_list[amount][0] == 'BUSD' and
                    get_list[amount][1] == name]

    return min(get_currency, key=lambda i: float(i))


async def get_box_sale_info(page):
    async with aiohttp.ClientSession() as session:
        url = f'{bapi_url}/public/nft/mystery-box/list?page={page}&size=10'

        async with session.get(url) as response:

            result_json = await response.json()
            assert response.status == 200

            return result_json


async def get_box_serialNo(page, name):
    result_json = await get_box_sale_info(page)

    return [item['serialsNo']
            for item in result_json['data']
            if item['name'] == name]


async def get_box_delay(page, name):
    result_json = await get_box_sale_info(page)

    return [item['secondMarketSellingDelay']
            for item in result_json['data']
            if item['name'] == name]


async def callback_inline_name(call, state: FSMContext):
    box_name = call.data.split('_')[1]

    await call.answer()

    async with state.proxy() as data:
        data['box_name'] = box_name
        data['serialNo'] = await get_box_serialNo(1, box_name)
        try:
            serial_no = data['serialNo'][0]
            data['productId'] = await get_box_last_productId(serial_no)

            msg = ('/set here need enter price in BUSD, example: /set 100,'
                   '/min info of min price in current lots')

            await bot.send_message(call.from_user.id, msg)
        except IndexError:
            msg = (f'{box_name} is not yet available,'
                   '/delay info about the time of the delay after the sale')

            await bot.send_message(call.from_user.id, msg)


async def send_msg(msg, state: FSMContext):
    async with state.proxy() as data:
        try:
            box_name = data['box_name']
            serialNo = data['serialNo'][0]

            if 'min' in msg.text:
                min_currency = await get_box_min_currency(serialNo, box_name)
                msg_min = f'{min_currency} BUSD'

                await bot.send_message(msg.from_user.id, msg_min)
            elif 'set' in msg.text:
                tasks = [task.get_name() for task in asyncio.all_tasks()]

                if f'finder_{msg.from_user.id}' not in tasks:
                    asyncio.create_task(finder(box_name, serialNo, msg),
                                        name=f'finder_{msg.from_user.id}')
                else:
                    msg_set = 'first enter /stop'

                    await bot.send_message(msg.from_user.id, msg_set)
            elif 'stop' in msg.text:
                tasks = [task
                         for task in asyncio.all_tasks()
                         if task.get_name() == f'finder_{msg.from_user.id}']

                for task in tasks:
                    task.cancel()

                msg_stop = 'stopped'

                await bot.send_message(msg.from_user.id, msg_stop)
            elif 'delay' in msg.text:
                box_delay_info = await get_box_delay(1, box_name)
                msg_delay = f'delay of {box_delay_info[0]} hours'

                await bot.send_message(msg.from_user.id, msg_delay)
        except KeyError:
            msg_err = 'first enter /start and select box'

            await bot.send_message(msg.from_user.id, msg_err)


def balancer(limit):
    tasks = [task.get_name().split('_')[0] for task in asyncio.all_tasks()]
    get_need_tasks = [task for task in tasks if task == 'finder']
    count = len(get_need_tasks)

    return limit // count


async def finder(box_name, serialNo, msg):
    while True:
        try:
            productId = await get_box_last_productId(f'{serialNo}')
            set_argument = msg.text.split()[1]

            await select_need_box(int(productId),
                                  box_name, balancer(99),
                                  float(set_argument),
                                  msg)

            await asyncio.sleep(14.88)
        except aiohttp.ContentTypeError:
            print('Лимит запросов')
            await asyncio.sleep(14.88)
            continue


async def on_startup(dispatcher):
    await set_default_commands(dispatcher)
    await register_handlers(dispatcher)


async def register_handlers(dispatcher):
    dispatcher.register_message_handler(keyboard.send_inline_keyboard,
                                        commands=['start'])

    dispatcher.register_message_handler(send_msg,
                                        commands=['min',
                                                  'set',
                                                  'stop',
                                                  'delay'])

    dispatcher.register_callback_query_handler(callback_inline_name,
                                               lambda call:
                                               call.data.startswith('name_'))

    dispatcher.register_callback_query_handler(keyboard.callback_inline_nav,
                                               lambda call:
                                               call.data.startswith('nav_'))


if __name__ == '__main__':
    executor.start_polling(dp, on_startup=on_startup)
