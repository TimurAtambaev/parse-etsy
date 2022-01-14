"""Модуль с классами парсинга."""
import csv
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

import requests
from django.contrib.auth.admin import UserAdmin
from django.core.paginator import Paginator
from django.forms import forms, widgets
from django.shortcuts import render
from django.urls import path
from lxml import html

from etsy.parse.models import Parse

logging.basicConfig(
        level=logging.ERROR,
        filename='parse_etsy.log',
        filemode='w',
        format='%(asctime)s, %(levelname)s, %(name)s, %(message)s'
    )


def results(request):
    results_list = Parse.objects.all()
    paginator = Paginator(results_list, 10)
    page_number = request.GET.get('page')
    page = paginator.get_page(page_number)
    return render(request, 'results.html', {'page': page,
                                            'paginator': paginator})


def parse_link():
    count = 0
    start = time.time()
    shops = set()
    try:
        while count <= 10000:
            count += 1
            resp = requests.get(
                f'https://www.etsy.com/c?locationQuery=473247&explicit=1&item_type='
                f'handmade&ref=pagination&page={count}', timeout=3)
            tree = html.fromstring(resp.text)
            res = tree.xpath(
                '//*[@id="content"]/div/div[1]/div/div[3]/div[2]/div[2]/div[5]/div/'
                'div/div/ul/li[*]/div/div/a/div[2]/div/div[1]/p')
            if not res:
                break
            shops.update(item.text.strip('\n   ') for item in res)

    except Exception as err:
        logging.error(f'{err}', exc_info=True)
        end = time.time()
        raise err

    def get_shop_info(shop):
        return requests.get(f'https://www.etsy.com/shop/{shop}', timeout=3)

    start = time.time()
    with ThreadPoolExecutor(max_workers=20) as pool:
        response_list = list(pool.map(get_shop_info, shops))

    shops_info = []
    try:
        for item in response_list:
            if not item.ok:
                continue
            tree = html.fromstring(item.text)
            try:
                since = \
                tree.xpath('//*[@id="about"]/div/div/div[1]/div/div/div[2]'
                           '/span')[0].text
            except Exception as err:
                logging.error(f'{err}', exc_info=True)
                since = None
            try:
                sales = \
                tree.xpath('//*[@id="about"]/div/div/div[1]/div/div/div[1]'
                           '/span')[0].text
            except Exception as err:
                logging.error(f'{err}', exc_info=True)
                sales = 0
            try:
                shop = tree.xpath(
                    '//*[@id="content"]/div[1]/div[1]/div[2]/div/div/div/div[1]/'
                    'div[1]/div[2]/div[1]/h1')[
                    0].text
            except Exception:
                continue
            shop_link = f'https://www.etsy.com/shop/{shop}'
            shops_info.append((shop, shop_link, since, sales))
    except Exception:
        ...

    filename = f'parse_etsy_{str(datetime.now())}.csv'
    file = open(filename, 'w', newline='')
    writer = csv.writer(file)
    writer.writerow(
        ['Магазин', 'Ссылка на магазин', 'Год основания', 'Продажи'])
    for shop in shops_info:
        writer.writerow(shop)
    file.close()
