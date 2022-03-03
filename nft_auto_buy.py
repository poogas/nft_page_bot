#!/usr/bin/env python3.9

import asyncio
import aiohttp
import config
import redis
import hashlib
from fake_useragent import UserAgent
from python3_anticaptcha import NoCaptchaTaskProxyless

base_url = 'https://www.binance.com'
order_url = f'{base_url}/bapi/nft/v1/private/nft/nft-trade/order-create'

ua = UserAgent()
db = redis.Redis()


async def solver(product_id):
    try:
        result = await NoCaptchaTaskProxyless.aioNoCaptchaTaskProxyless(
             anticaptcha_key=config.ANTI_CAPTCHA_KEY
        ).captcha_handler(
             websiteURL=(f'{base_url}/en/nft/goods/blindBox/detail?'
                         'productId={product_id}&isOpen=false&isProduct=1'),
             websiteKey=config.SITE_KEY)

        return result['solution']['gRecaptchaResponse']
    except Exception as err:
        print(err)


async def nft_get_amount(session, product_id):
    async with session.post(f'{base_url}/bapi/nft/v1/friendly/nft/nft-trade/'
                            'product-detail',
                            json={'productId': product_id}) as response:
        result_json = await response.json()

        assert response.status == 200

        try:
            return {'price': result_json['data']['productDetail']['amount']}
        except Exception:
            result_json['message']


async def nft_buy(session, product_id):
    get_amount = await nft_get_amount(session, product_id)

    payload = {"amount": get_amount['price'],
               "productId": product_id,
               "tradeType": 0}

    async with session.post(order_url, json=payload) as response:
        result_json = await response.json()
        assert response.status == 200

        return result_json


async def other_session(product_id):
    solution = await solver(product_id)

    csrftoken = db.get('csrfToken')
    cookie = db.get('cookie').decode("utf-8").split(';')[0]

    headers = {"clienttype": "web",
               "user-agent": ua.chrome,
               "device-info": config.DEVICE_INFO,
               "cookie": cookie,
               "csrftoken": hashlib.md5(csrftoken).hexdigest(),
               "x-nft-checkbot-sitekey": config.SITE_KEY,
               "x-nft-checkbot-token": solution}

    async with aiohttp.ClientSession(headers=headers) as session:
        result = await nft_buy(session, product_id)
        print(result)


if __name__ == "__main__":
    asyncio.run(other_session('9229887'))
