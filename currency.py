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

API_TOKEN = os.getenv('BOT_TOKEN')
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

    async with aiohttp.ClientSession() as session:
        async with session.get('https://koronapay.com/transfers/online/api/transfers/tariffs', params=params) as resp:
            result = await resp.read() #(content_type='text/html')
            return json.loads(result)[0]['exchangeRate']


async def kurs_kz():
    async with aiohttp.ClientSession() as session:
        async with session.get('https://kurs.kz/') as resp:
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
    data = {
        'senderBankId': '361934',
        'acceptedCurrency': 'RUB',
        'withdrawCurrency': currency,
        'amount': '100',
        'countryCode': 'KAZ',
    }

    # proxy = FreeProxy(country_id=['RU']).get()
    async with aiohttp.ClientSession() as session:
        async with session.post('https://api6.unistream.com/api/v1/transfer/calculate', data=data, proxy=proxy, timeout=20) as resp: #, headers=headers) as resp:
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
    # loop = asyncio.get_event_loop()
    # proxy = FreeProxy(country_id=['RU']).get()
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
