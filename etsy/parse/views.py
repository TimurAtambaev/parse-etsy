"""Модуль с представлениями парсинга."""
import csv
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from pathlib import Path

import requests
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.urls import reverse
from lxml import html

from .forms import LinkTokenForm
from .models import Parse

TOKEN = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE2NDI0MDE0ND'

logging.basicConfig(
    level=logging.ERROR,
    filename='parse_etsy.log',
    filemode='w',
    format='%(asctime)s, %(levelname)s, %(name)s, %(message)s'
)

BASE_DIR = Path(__file__).resolve().parent.parent


def results(request):
    """Вывод ссылок всех результатов парсинга с пагинацией."""
    results_list = Parse.objects.all()
    paginator = Paginator(results_list, 20)
    page_number = request.GET.get('page')
    page = paginator.get_page(page_number)
    return render(request, 'results.html', {'page': page,
                                            'paginator': paginator})


def add_link(request):
    """Ввод пользователем ссылки для парсинга."""
    link = LinkTokenForm(request.POST or None)
    link_to_parse = request.POST.get('link', None)
    if request.POST.get('token') and request.POST.get('token') != TOKEN:
        return HttpResponse('Пожалуйста, введите корректный токен доступа '
                            'чтобы начать парсинг.')
    if link.is_valid and link_to_parse:
        parse_link(link_to_parse)
        return redirect(reverse('parse:success'))
    return render(request, 'enter_link_form.html', {'form': link})


def success(request):
    """Редирект после завершения парсинга. ссылки"""
    return render(request, 'redirect_page.html')


def parse_link(link):
    """Парсинг ссылки, запись результатов в файл csv,
    внесение наименования файла в базу данных."""
    count = 0
    shops = set()
    link_page = ((link + '&ref=pagination&page=') if '?' in link else
                 (link + '?ref=pagination&page='))
    try:
        while count <= 5:
            count += 1
            resp = requests.get(f'{link_page}{count}', timeout=10)
            tree = html.fromstring(resp.text)
            res = tree.xpath(
                '//*[@id="content"]/div/div[1]/div/div[3]/div[2]/div[2]/div[5]'
                '/div/div/div/ul/li[*]/div/div/a/div[2]/div/div[1]/p')
            if not res:
                break
            shops.update(item.text.strip('\n   ') for item in res)

    except Exception as err:
        logging.error(f'{err}', exc_info=True)
        raise err

    with ThreadPoolExecutor(max_workers=20) as pool:
        response_list = list(pool.map(get_shop_info, shops))

    shops_info = []
    try:
        for item in response_list:
            if not item.ok:
                continue
            tree = html.fromstring(item.text)
            try:
                since = tree.xpath('//*[@id="about"]/div/div/div[1]/div/div/'
                                   'div[2]/span')[0].text
            except Exception as err:
                logging.error(f'{err}', exc_info=True)
                since = None
            try:
                sales = tree.xpath(
                    '//*[@id="content"]/div[1]/div[1]/div[2]/div/div/div/div'
                    '[1]/div/div[2]/div[2]/div[2]/span[1]/a')[0].text
            except Exception as err:
                logging.error(f'{err}', exc_info=True)
                sales = '0'
            try:
                sales = sales or tree.xpath(
                    '//*[@id="content"]/div[1]/div[2]/div[2]/span/div[2]/div'
                    '[1]/div[5]/div[1]')[0].text
            except Exception as err:
                logging.error(f'{err}', exc_info=True)
                sales = '0'
            try:
                sales = sales or tree.xpath(
                    '//*[@id="about"]/div/div/div[1]/div/div/div'
                    '[1]/span')[0].text
            except Exception as err:
                logging.error(f'{err}', exc_info=True)
                sales = '0'
            sales = sales.strip('Sales')
            try:
                shop = tree.xpath(
                    '//*[@id="content"]/div[1]/div[1]/div[2]/div/div/div/'
                    'div[1]/div[1]/div[2]/div[1]/h1')[
                    0].text
            except Exception as err:
                logging.error(f'{err}', exc_info=True)
                continue
            shop_link = f'https://www.etsy.com/shop/{shop}'
            shops_info.append((shop, shop_link, since, sales))
    except Exception:
        ...

    parse_time = str(datetime.now() + timedelta(hours=3))
    if not os.path.isdir('media'):
        os.mkdir('media')
    filename = f'{os.path.join(BASE_DIR, "media")}/{parse_time}.csv'
    file = open(filename, 'w', newline='')
    writer = csv.writer(file)
    writer.writerow(
        ['Магазин', 'Ссылка на магазин', 'Год основания', 'Продажи'])
    for shop in shops_info:
        writer.writerow(shop)
    file.close()
    parse = Parse.objects.create(parse_name=parse_time, link=link)
    parse.save()


def get_shop_info(shop):
    """Получение страницы магазина."""
    return requests.get(f'https://www.etsy.com/shop/{shop}', timeout=10)
