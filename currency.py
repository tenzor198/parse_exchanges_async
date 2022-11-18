import regex
import json
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
import logging
from aiogram import Bot, Dispatcher, executor, types
import aiohttp
import asyncio
import pytz
import tzlocal
import os
from datetime import datetime
from aiogram.types import ReplyKeyboardRemove, \
    ReplyKeyboardMarkup, KeyboardButton, \
    InlineKeyboardMarkup, InlineKeyboardButton
from fp.fp import FreeProxy
API_TOKEN = '5411390712:AAHEDIw8x-B2nu5J89gPqFWMvJ7uNpjR-1I'# os.getenv('BOT_TOKEN')
logging.basicConfig(level=logging.INFO)
# proxy = FreeProxy(country_id=['RU']).get()
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)


def localtime_to_utc(dt):
    localzone = tzlocal.get_localzone()
    dt = localzone.localize(dt)
    return dt.astimezone(pytz.utc)


async def corona_curs(currency):
    if currency == 'KZT':
        currency_id = '398'
    else:
        currency_id = '840'
    params = {
        'sendingCountryId': 'RUS',
        'sendingCurrencyId': '810',
        'receivingCountryId': 'KAZ',
        'receivingCurrencyId': currency_id,
        'paymentMethod': 'debitCard',
        'receivingAmount': '100000',
        'receivingMethod': 'cash',
        'paidNotificationEnabled': 'true',
    }
    # headers = {
    #     'User-Agent': UserAgent().random,
    #     'Accept': 'application/vnd.cft-data.v2.86+json',
    #     'Accept-Language': 'en',
    #     'x-application': 'Qpay-Web/3.0',
    #     'x-csrf-token': '1fa0cd2ff26e77b9046d17f979af5655',
    #     'Connection': 'keep-alive',
    #     'Referer': 'https://koronapay.com/transfers/online/',
    #     'Sec-Fetch-Dest': 'empty',
    #     'Sec-Fetch-Mode': 'cors',
    #     'Sec-Fetch-Site': 'same-origin',
    # }
    async with aiohttp.ClientSession() as session:
        async with session.get('https://koronapay.com/transfers/online/api/transfers/tariffs', params=params) as resp:
                # , headers=headers) as resp:
            result = await resp.read() #(content_type='text/html')
            return json.loads(result)[0]['exchangeRate']


async def kurs_kz():
    # headers = {
    #     'User-Agent': UserAgent().random,
    #     'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    #     'Accept-Language': 'en-US,en;q=0.5',
    #     # 'Accept-Encoding': 'gzip, deflate, br',
    #     'Referer': 'https://kurs.kz/',
    #     'Connection': 'keep-alive',
    #     # Requests sorts cookies= alphabetically
    #     # 'Cookie': 'PHPSESSID=lm0occj10cm1l5nbn54mh6g2ma; __utma=155015202.585920995.1664831714.1664831714.1664831714.1; __utmb=155015202.2.10.1664831714; __utmc=155015202; __utmz=155015202.1664831714.1.1.utmcsr=google|utmccn=(organic)|utmcmd=organic|utmctr=(not%20provided); __utmt=1; _ym_uid=1664831714707133073; _ym_d=1664831714; _ym_isad=1; _zero_cc=f8996bd75cbf24; _zero_ss=633b50e2d5cb7.1664831715.1664832096.2; _ym_visorc=w',
    #     'Upgrade-Insecure-Requests': '1',
    #     'Sec-Fetch-Dest': 'document',
    #     'Sec-Fetch-Mode': 'navigate',
    #     'Sec-Fetch-Site': 'same-origin',
    #     'Sec-Fetch-User': '?1',
    #     # Requests doesn't support trailers
    #     # 'TE': 'trailers',
    # }
    async with aiohttp.ClientSession() as session:
        async with session.get('https://kurs.kz/') as resp:#, headers=headers) as resp:
            response_kurs = await resp.text()
            soup = BeautifulSoup(response_kurs, 'html.parser')
            scripts = soup.select('script')
            pattern = regex.compile(r'\{(?:[^{}]|(?R))*\}')
            result = []
            rub_currency = []
            for script in scripts:
                jsons_soup = pattern.findall(str(script))
                for exchanges in jsons_soup:
                    try:
                        json_cat = json.loads(exchanges)
                        result.append([json_cat['name'], json_cat['address'], json_cat['data']['RUB'][0]])
                        rub_currency.append(json_cat['data']['RUB'][0])
                    except:
                        pass
            rub_currency_max = max(rub_currency)
            exchanges = list(filter(lambda x: x[2] == rub_currency_max, result))
            output = []
            for exchange in exchanges:
                output.append(': '.join(str(x) for x in exchange) + '\n')
            return rub_currency_max, '\n'.join(output[:5])

async def tinkoff(currency='KZT'):
    # headers = {
    #     'User-Agent': UserAgent().random,
    #     'Accept': '*/*',
    #     'Accept-Language': 'en-US,en;q=0.5',
    #     # 'Accept-Encoding': 'gzip, deflate, br',
    #     'Content-type': 'application/x-www-form-urlencoded',
    #     'Origin': 'https://www.tinkoff.ru',
    #     'Sec-Fetch-Dest': 'empty',
    #     'Sec-Fetch-Mode': 'cors',
    #     'Sec-Fetch-Site': 'same-site',
    #     'Referer': 'https://www.tinkoff.ru/',
    #     'Connection': 'keep-alive',
    #     # Requests doesn't support trailers
    #     # 'TE': 'trailers',
    # }
    params = {
        'from': 'RUB',
        'to': currency,
    }
    async with aiohttp.ClientSession() as session:
        async with session.get('https://api.tinkoff.ru/v1/currency_rates', params=params) as resp:#, headers=headers) as resp:
            response_kurs = await resp.json(content_type=None)
            rates = response_kurs['payload']['rates']
            for rate in rates:
                if rate['category'] == 'DepositPayments':
                    return rate['buy']


async def unistream_post(proxy, currency='KZT'):
    cookies = {
        '_ym_uid': '1667811927399695118',
        '_ym_d': '1667811927',
        'tmr_reqNum': '90',
        'tmr_lvid': '7ade19053a92eb2fba61a9c1a3d8bbb7',
        'tmr_lvidTS': '1667811927534',
        'uni_c2c_source': 'https://www.google.com/',
        '_ym_isad': '1',
        '__lhash_': '27797737c3d71f94dc60e669efb0ecb0',
        'PHPSESSID': 'akhi1p87k2iru6i70nvlcv9v9p',
        '__hash_': 'bd03af247650909101bedc2c05948914',
        'tmr_detect': '1%7C1668762862487',
    }

    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:106.0) Gecko/20100101 Firefox/106.0',
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Accept-Language': 'en-US,en;q=0.5',
        # 'Accept-Encoding': 'gzip, deflate, br',
        'X-Requested-With': 'XMLHttpRequest',
        'Connection': 'keep-alive',
        'Referer': 'https://online.unistream.ru/card2cash/?country=KAZ&amount=1000&currency=KZT&utm_source=offline_calc',
        # Requests sorts cookies= alphabetically
        # 'Cookie': '_ym_uid=1667811927399695118; _ym_d=1667811927; tmr_reqNum=90; tmr_lvid=7ade19053a92eb2fba61a9c1a3d8bbb7; tmr_lvidTS=1667811927534; uni_c2c_source=https://www.google.com/; _ym_isad=1; __lhash_=27797737c3d71f94dc60e669efb0ecb0; PHPSESSID=akhi1p87k2iru6i70nvlcv9v9p; __hash_=bd03af247650909101bedc2c05948914; tmr_detect=1%7C1668762862487',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-origin',
        # Requests doesn't support trailers
        # 'TE': 'trailers',
    }
    data = {
        'senderBankId': '361934',
        'acceptedCurrency': 'RUB',
        'withdrawCurrency': currency,
        'amount': '100',
        'countryCode': 'KAZ',
    }
    params = {
        'payout_type': 'cash',
        'destination': 'KAZ',
        'amount': '1000',
        'currency': currency,
        'accepted_currency': 'RUB',
        'profile': 'unistream',
    }
    headers = {
        'authority': 'online.unistream.ru',
        'accept': 'application/json, text/javascript, */*; q=0.01',
        'accept-language': 'ru',
        'origin': 'https://unistream.ru',
        'referer': 'https://unistream.ru/',
        'sec-ch-ua': '"Chromium";v="107", "Not=A?Brand";v="24"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Linux"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-site',
        'user-agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 9_1 like Mac OS X) AppleWebKit/601.1.46 (KHTML, like Gecko) Version/9.0 Mobile/13B137 Safari/601.1',
    }

    params = {
        'destination': 'KAZ',
        'amount': '1000',
        'currency': 'KZT',
        'accepted_currency': 'RUB',
        'profile': 'unistream',
    }

# proxy = FreeProxy(country_id=['RU']).get()
    async with aiohttp.ClientSession() as session:
        async with session.post('https://online.unistream.ru/card2cash/calculate', headers=headers, params=params, timeout=20) as resp:#, data=data) as resp: #, proxy=proxy, timeout=20) as resp: #, headers=headers) as resp:
            response_kurs = await resp.read()
            return resp.status, response_kurs #rates


async def get_status(proxy, currency):
    try:
        resp_status, resp = await unistream_post(proxy, currency)
    except:
        resp_status, resp = 403, []
    return resp_status, resp


async def unistream(currency='KZT'):
    with open('proxy.txt') as f:
        proxy = f.read()
    loop = asyncio.get_event_loop()
    proxy = FreeProxy(country_id=['RU']).get()
    resp_status, resp = await get_status(proxy, currency)
    while resp_status != 200:
        print('iff')
        proxy = FreeProxy(rand=True).get() #country_id=['RU'] , country_id=['RU'], https=True
        resp_status, resp = await get_status(proxy, currency)
        print(proxy)
        print(resp_status, resp)
    with open('proxy.txt', 'w') as w:
        w.write(proxy)
    resp_kurs = json.loads(resp)
    return resp_kurs['fees'][0]['rate']


async def output_data(message, currency):
    user = message.from_user.id
    users = json.load(open('users.json'))
    if user not in users:
        new_users = users+[user]
        json.dump(new_users, open('users.json', 'w'))
        print('New:', message.from_user.username)
        print('count_users:', len(new_users))

    now_date = str(localtime_to_utc(message.date))
    old_res = json.load(open(f'result_{currency}.json'))
    date_diff = datetime.fromisoformat(now_date) - datetime.fromisoformat(old_res['old_date'])

    if date_diff.total_seconds() / 60 < 10:
        output_message = old_res['result']
    else:
        corona = await corona_curs(currency)
        exchanges_max, exchanges = await kurs_kz()
        tink = await tinkoff(currency)
        unistr = await unistream(currency)
        if currency == 'USD':
            corona = round(corona, 3)
            unistr = round(1 / unistr, 3)
            contact = round(unistr - 0.03, 3)
            tink = round(1 / tink, 3)
            output_message = f"""
            <u>Курс рубля к доллару:</u>\n
            <i><b>Золотая корона: {corona}</b></i>
            <b>Контакт:≈ {contact}</b>
            <b>Тинькофф: {tink}</b>
            <b>Юнистрим: {unistr}</b>
            """.replace('           ', ' ')
        else:
            corona = round(1 / corona, 3)
            unistr = round(unistr, 3)
            contact = round(unistr-0.01, 3)
            output_message = f"""
                <u>Курс рубля к тенге:</u>\n
                <i><b>Золотая корона: {corona}</b></i>
                <b>Контакт:≈ {contact}</b>
                <b>Тинькофф: {tink}</b>
                <b>Юнистрим: {unistr}</b>
                <b>В обменниках: {exchanges_max}</b>\n
                {exchanges}
                """.replace('           ', ' ')
        json.dump({'old_date': now_date, 'result': output_message}, open(f'result_{currency}.json', 'w'))

    await message.answer(output_message, parse_mode='html')


@dp.message_handler(commands=['start'])
async def echo(message: types.Message):
    button_hi = KeyboardButton('Тенге 🇰🇿')
    add_button = KeyboardButton('Доллар 💰')
    items = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True).add(button_hi, add_button)
    await message.answer('Выберите валюту для перевода рублей', parse_mode='html', reply_markup=items)


@dp.message_handler(lambda message: message.text == "Тенге 🇰🇿")
async def with_puree(message: types.Message):
    await output_data(message, 'KZT')


@dp.message_handler(lambda message: message.text == "Доллар 💰")
async def with_puree(message: types.Message):
    await output_data(message, 'USD')


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)#, skip_updstore_rating_quantityates=True)
