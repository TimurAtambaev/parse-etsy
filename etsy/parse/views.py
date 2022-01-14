"""Модуль с классами парсинга."""
import csv
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from io import BytesIO

import requests
from django.core.paginator import Paginator
from django.shortcuts import render, redirect
from lxml import html

from .forms import LinkForm
from .models import Parse

logging.basicConfig(
        level=logging.ERROR,
        filename='parse_etsy.log',
        filemode='w',
        format='%(asctime)s, %(levelname)s, %(name)s, %(message)s'
    )


def results(request):
    results_list = Parse.objects.all()
    paginator = Paginator(results_list, 40)
    page_number = request.GET.get('page')
    page = paginator.get_page(page_number)
    return render(request, 'results.html', {'page': page,
                                            'paginator': paginator})


def add_link(request):
    links = LinkForm(request.POST or None)
    link_to_parse = request.POST.get('link', None)
    if link_to_parse:
        parse_link(link_to_parse)
    return render(request, 'enter_link_form.html', {'form': links})


def parse_link(link):
    count = 0
    start = time.time()
    shops = set()
    link_page = (str(link) + '&ref=pagination&page=') if '?' in str(link) else (str(link) + '?ref=pagination&page=')
    try:
        while count <= 5:
            count += 1
            resp = requests.get(f'{link_page}{count}', timeout=3)
            tree = html.fromstring(resp.text)
            res = tree.xpath(
                '//*[@id="content"]/div/div[1]/div/div[3]/div[2]/div[2]/div[5]'
                '/div/div/div/ul/li[*]/div/div/a/div[2]/div/div[1]/p')
            if not res:
                break
            shops.update(item.text.strip('\n   ') for item in res)

    except Exception as err:
        logging.error(f'{err}', exc_info=True)
        end = time.time()
        raise err

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
                    '//*[@id="content"]/div[1]/div[1]/div[2]/div/div/div/'
                    'div[1]/div[1]/div[2]/div[1]/h1')[
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
    parse = Parse.objects.create(parse_link=link, parse_file=file)
    parse.save()


def get_shop_info(shop):
    return requests.get(f'https://www.etsy.com/shop/{shop}', timeout=3)

