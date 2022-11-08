import regex
import json
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
import logging
from aiogram import Bot, Dispatcher, executor, types
import aiohttp
import pytz
import tzlocal
import os
from datetime import datetime
from aiogram.types import ReplyKeyboardRemove, \
    ReplyKeyboardMarkup, KeyboardButton, \
    InlineKeyboardMarkup, InlineKeyboardButton
from fp.fp import FreeProxy
API_TOKEN = os.getenv('BOT_TOKEN')
logging.basicConfig(level=logging.INFO)
proxy = FreeProxy(country_id=['RU']).get()
bot = Bot(token=API_TOKEN, proxy=proxy)
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
    headers = {
        'User-Agent': UserAgent().random,
        'Accept': 'application/vnd.cft-data.v2.86+json',
        'Accept-Language': 'en',
        'x-application': 'Qpay-Web/3.0',
        'x-csrf-token': '1fa0cd2ff26e77b9046d17f979af5655',
        'Connection': 'keep-alive',
        'Referer': 'https://koronapay.com/transfers/online/',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-origin',
    }
    async with aiohttp.ClientSession() as session:
        async with session.get('https://koronapay.com/transfers/online/api/transfers/tariffs', params=params, headers=headers) as resp:
            result = await resp.json(content_type=None)
            return result[0]['exchangeRate']


async def kurs_kz():
    headers = {
        'User-Agent': UserAgent().random,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        # 'Accept-Encoding': 'gzip, deflate, br',
        'Referer': 'https://kurs.kz/',
        'Connection': 'keep-alive',
        # Requests sorts cookies= alphabetically
        # 'Cookie': 'PHPSESSID=lm0occj10cm1l5nbn54mh6g2ma; __utma=155015202.585920995.1664831714.1664831714.1664831714.1; __utmb=155015202.2.10.1664831714; __utmc=155015202; __utmz=155015202.1664831714.1.1.utmcsr=google|utmccn=(organic)|utmcmd=organic|utmctr=(not%20provided); __utmt=1; _ym_uid=1664831714707133073; _ym_d=1664831714; _ym_isad=1; _zero_cc=f8996bd75cbf24; _zero_ss=633b50e2d5cb7.1664831715.1664832096.2; _ym_visorc=w',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'same-origin',
        'Sec-Fetch-User': '?1',
        # Requests doesn't support trailers
        # 'TE': 'trailers',
    }
    async with aiohttp.ClientSession() as session:
        async with session.get('https://kurs.kz/', headers=headers) as resp:
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
            return rub_currency_max, '\n'.join(output[:10])

async def tinkoff(currency='KZT'):
    headers = {
        'User-Agent': UserAgent().random,
        'Accept': '*/*',
        'Accept-Language': 'en-US,en;q=0.5',
        # 'Accept-Encoding': 'gzip, deflate, br',
        'Content-type': 'application/x-www-form-urlencoded',
        'Origin': 'https://www.tinkoff.ru',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-site',
        'Referer': 'https://www.tinkoff.ru/',
        'Connection': 'keep-alive',
        # Requests doesn't support trailers
        # 'TE': 'trailers',
    }
    params = {
        'from': 'RUB',
        'to': currency,
    }
    async with aiohttp.ClientSession() as session:
        async with session.get('https://api.tinkoff.ru/v1/currency_rates', params=params, headers=headers) as resp:
            response_kurs = await resp.json(content_type=None)
            rates = response_kurs['payload']['rates']
            for rate in rates:
                if rate['category'] == 'DepositPayments':
                    return rate['buy']

async def unistream(currency='KZT'):
    with open('proxy.txt') as f:
        proxy = f.read()
    resp_status, resp = await unistream_post(proxy, currency)
    if resp_status != 200:
        proxy = await FreeProxy(country_id=['RU']).get()
        with open('proxy.txt', 'w') as w:
            w.write(proxy)
        resp_status, resp = await unistream_post(proxy, currency)
    resp_kurs = json.loads(resp)
    return resp_kurs['fees'][0]['rate']


async def unistream_post(proxy, currency='KZT'):
    headers = {
        'User-Agent': UserAgent().random,
        'Accept': '*/*',
        'Accept-Language': 'ru',
        # 'Accept-Encoding': 'gzip, deflate, br',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'Origin': 'https://unistream.ru',
        'Connection': 'keep-alive',
        'Referer': 'https://unistream.ru/',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'cross-site',
    }
    data = {
        'senderBankId': '361934',
        'acceptedCurrency': 'RUB',
        'withdrawCurrency': currency,
        'amount': '100',
        'countryCode': 'KAZ',
    }
    async with aiohttp.ClientSession() as session:
        async with session.post('https://api6.unistream.com/api/v1/transfer/calculate', data=data, proxy=proxy) as resp: #, headers=headers) as resp:
            response_kurs = await resp.read()
            return resp.status, response_kurs #rates

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

    if date_diff.total_seconds() / 60 < 5:
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
        else:
            corona = round(1 / corona, 3)
            contact = round(unistr-0.01, 3)
        if currency == 'USD':
            output_message = f"""
            <u>Курс рубля в тенге:</u>\n
            <i><b>Золотая корона: {corona}</b></i>
            <b>Контакт:≈ {contact}</b>
            <b>Тинькофф: {tink}</b>
            <b>Юнистрим: {unistr}</b>
            """.replace('           ', ' ')
        else:
            output_message = f"""
                <u>Курс рубля в тенге:</u>\n
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
    add_button = KeyboardButton('Доллары 💰')
    items = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True).add(button_hi, add_button)
    await message.answer('Выберите валюту для перевода рублей', parse_mode='html', reply_markup=items)


@dp.message_handler(lambda message: message.text == "Тенге 🇰🇿")
async def with_puree(message: types.Message):
    await output_data(message, 'KZT')


@dp.message_handler(lambda message: message.text == "Доллары 💰")
async def with_puree(message: types.Message):
    await output_data(message, 'USD')


if __name__ == '__main__':
    executor.start_polling(dp)#, skip_updstore_rating_quantityates=True)
