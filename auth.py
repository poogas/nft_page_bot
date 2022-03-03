#!/usr/bin/env python3.9

import asyncio
import aiohttp
import hashlib
import config
import redis
from time import time
from fake_useragent import UserAgent
from python3_anticaptcha import GeeTestTaskProxyless


ua = UserAgent()
db = redis.Redis()

url_account = 'https://accounts.binance.com'
url_gt_code = (f'{url_account}/bapi/'
               'composite/v1/public/common/security/gt-code?t=')
url_base_login = (f'{url_account}'
                  '/ru/login')
url_auth = (f'{url_account}/bapi/'
            'accounts/v2/public/authcenter/login')
url_auth_2fa = (f'{url_account}/bapi/'
                'accounts/v1/protect/account/mobile/sendMobileVerifyCode')
url_auth_confirm = (f'{url_account}/bapi/'
                    'accounts/v1/public/authcenter/auth')


async def get_gt_code(session):
    time_stamp = int(time() * 1000)
    url = f'{url_gt_code}{time_stamp}'

    async with session.get(url) as response:
        result_json = await response.json()
        assert response.status == 200

        return result_json


async def auth(session, challenge, validate, seccode, email, password):
    encode_password = f"{password}{email}".encode('utf-8')
    encode_safe_password = f"{password}".encode('utf-8')
    hash_password = hashlib.md5(encode_password).hexdigest()
    hash_safe_password = hashlib.sha512(encode_safe_password).hexdigest()

    payload = {"email": f"{email}",
               "password": hash_password,
               "safePassword": hash_safe_password,
               "validateCodeType": "gt",
               "geetestChallenge": challenge,
               "geetestValidate": validate,
               "geetestSeccode": seccode,
               "challenge": "",
               "gt": "",
               "gtId": "",
               "deviceInfo": config.DEVICE_INFO,
               "isNewLoginProcess": "true"}

    async with session.post(url_auth, json=payload) as response:
        result_json = await response.json()
        assert response.status == 200

        return result_json


async def send_mobile_code(session):
    payload = {"bizScene": "LOGIN",
               "msgType": "TEXT",
               "resend": "false"}

    async with session.post(url_auth_2fa, json=payload) as response:
        result_json = await response.json()
        assert response.status == 200

        return result_json


async def confirm_mobile_code(session, email, code):
    payload = {"email": f"{email}",
               "mobileVerifyCode": f"{code}",
               "isNewLoginProcess": "true"}

    async with session.post(url_auth, json=payload) as response:
        result_json = await response.json()
        assert response.status == 200
        cookie_p20t = response.cookies['p20t']
        cookie_p20t_to = str(cookie_p20t).split()[1:-2][0]

        return {"result_json": result_json, "cookie_p20t": cookie_p20t_to}


async def other_logic(session):
    result_gt_code = await get_gt_code(session)
    gt = result_gt_code['data']['gt']
    challenge = result_gt_code['data']['challenge']
    result_solution = await GeeTestTaskProxyless.aioGeeTestTaskProxyless(
                  anticaptcha_key=config.ANTI_CAPTCHA_KEY,
                  websiteURL=url_base_login,
                  gt=gt).captcha_handler(challenge=challenge)
    challenge = result_solution['solution']['challenge']
    validate = result_solution['solution']['validate']
    seccode = result_solution['solution']['seccode']
    quest_email = input('email:')
    quest_password = input('password:')
    result_auth = await auth(
              session,
              challenge,
              validate,
              seccode,
              quest_email,
              quest_password)

    if result_auth['data']['mobileSecurity']:
        await send_mobile_code(session)
        quest_code = input('CODE:')
        confirm_2fa = await confirm_mobile_code(session,
                                                quest_email,
                                                quest_code)

        return {'csrfToken': confirm_2fa['result_json']['data']['csrfToken'],
                'cookie': confirm_2fa['cookie_p20t']}


async def other_session():
    headers = {"clienttype": "web",
               "user-agent": ua.chrome,
               "device-info": config.DEVICE_INFO}

    async with aiohttp.ClientSession(headers=headers) as session:
        result = await other_logic(session)

        return result


async def confirm_auth():
    result = await other_session()
    csrftoken = result['csrfToken']
    headers = {"clienttype": "web",
               "cookie": result['cookie'].split(';')[0],
               "csrftoken": hashlib.md5(csrftoken.encode('utf-8')).hexdigest(),
               "user-agent": ua.chrome,
               "device-info": config.DEVICE_INFO}

    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.post(url_auth_confirm) as response:
            result_json = await response.json()
            if result_json['success']:
                db.mset({'csrfToken': result['csrfToken'],
                         'cookie': result['cookie'].split(';')[0]})


async def login():
    csrftoken = db.get('csrfToken')
    cookie = db.get('cookie').decode("utf-8").split(';')[0]

    headers = {"clienttype": "web",
               "cookie": cookie,
               "csrftoken": hashlib.md5(csrftoken).hexdigest(),
               "user-agent": ua.chrome,
               "device-info": config.DEVICE_INFO}

    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.post(url_auth_confirm) as response:
            result_json = await response.json()
            if not result_json['success']:
                await confirm_auth()
            else:
                print(result_json['success'])


async def test():
    result_json = await confirm_auth()
    print(result_json)

if __name__ == "__main__":
    asyncio.run(login())
