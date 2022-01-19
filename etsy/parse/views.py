"""Модуль с представлениями парсинга."""
import csv
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import ThreadPoolExecutor as Thread
from datetime import datetime, timedelta
from pathlib import Path

import requests
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.urls import reverse
from lxml import html
from bs4 import BeautifulSoup

from .forms import LinkTokenForm
from .models import Parse

logging.basicConfig(
    level=logging.ERROR,
    filename='parse_etsy.log',
    filemode='w',
    format='%(asctime)s, %(levelname)s, %(name)s, %(message)s'
)

TOKEN = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE2NDI0MDE0ND'
BASE_DIR = Path(__file__).resolve().parent.parent
HEADERS = ({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                          'AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/90.0.4430.212 Safari/537.36'})


def results(request):
    """Вывод ссылок всех результатов парсинга с пагинацией."""
    results_list = Parse.objects.all()
    paginator = Paginator(results_list, 10)
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
    if (link.is_valid and link_to_parse and 'https://www.etsy.com' not in
            link_to_parse):
        return HttpResponse('Пожалуйста, введите ссылку на сайт '
                            'https://www.etsy.com.')
    if link.is_valid and link_to_parse:
        pool = ThreadPoolExecutor(max_workers=1)
        pool.submit(parse_link, link=link_to_parse)
        return redirect(reverse('parse:success'))
    return render(request, 'enter_link_form.html', {'form': link})


def success(request):
    """Редирект после завершения парсинга. ссылки"""
    return render(request, 'redirect_page.html')


def parse_link(link):
    """Парсинг ссылки, запись результатов в файл csv,
    внесение наименования файла в базу данных."""
    parse_time = str(datetime.now() + timedelta(hours=3))
    count = 0
    shops = set()
    link_page = ((link + '&ref=pagination&page=') if '?' in link else
                 (link + '?ref=pagination&page='))
    print(link_page)
    try:
        while count <= 10000:
            count += 1
            resp = requests.get(f'{link_page}{count}', headers=HEADERS,
                                timeout=10)
            tree = html.fromstring(resp.text)
            res = tree.xpath('//p[@class="wt-text-caption wt-text-truncate '
                             'wt-text-gray wt-mb-xs-1"]')
            if not res:
                break
            shops.update(item.text.strip('\n   ') for item in res)
    except Exception as err:
        logging.error(f'{err}', exc_info=True)
        raise err

    with Thread(max_workers=20) as pool:
        response_list = list(pool.map(get_shop_info, shops))

    shops_info = []
    try:
        for item in response_list:
            if not item.ok:
                continue
            tree = html.fromstring(item.text)
            soup = BeautifulSoup(item.text, 'lxml')
            try:
                shop = tree.xpath(
                    '//*[@id="content"]/div[1]/div[1]/div[2]/div/div/div/'
                    'div[1]/div[1]/div[2]/div[1]/h1')[0].text
            except Exception as err:
                logging.error(f'{err}', exc_info=True)
                shop = None
            if shop == None:
                try:
                    shop = tree.xpath('//h1[@class="wt-text-heading-01 wt-'
                                      'text-truncate"]')[0].text
                except Exception as err:
                    logging.error(f'{err}', exc_info=True)
            if shop == None:
                try:
                    shop = soup.select('#content > div.shop-home > div:nth-'
                                       'child(1) > div.wt-body-max-width.wt-'
                                       'pr-xs-2.wt-pr-md-4.wt-pl-xs-2.wt-pl-'
                                       'md-4 > div > div > div > div.wt-max-'
                                       'width-full.wt-grid.wt-pr-lg-5.wt-width'
                                       '-full > div.wt-grid__item-xs-12.wt-'
                                       'display-flex-xs.wt-grid__item-md-7.wt'
                                       '-br-md.wt-pr-md-4.wt-align-items-'
                                       'center > div.shop-home-header-info.'
                                       'shop-info.wt-pl-md-3.wt-pl-xs-2.wt-'
                                       'display-inline-block.wt-vertical-'
                                       'align-top.text-truncate-x > div.shop'
                                       '-name-and-title-container.wt-mb-xs-1 '
                                       '> h1')[0].text
                except Exception as err:
                    logging.error(f'{err}', exc_info=True)
                    continue
            shop_link = f'https://www.etsy.com/shop/{shop}'
            try:
                since = tree.xpath('//*[@id="about"]/div/div/div[1]/div/div/'
                                   'div[2]/span')[0].text
            except Exception as err:
                logging.error(f'{err}', exc_info=True)
                since = None
            if since == None:
                try:
                    since = soup.select('#about > div > div > div.shop-home-'
                                        'wider-sections.mr-lg-4 > div > div > '
                                        'div:nth-child(2) > span')[0].text
                except Exception as err:
                    logging.error(f'{err}', exc_info=True)
            if since == None:
                try:
                    since = tree.xpath('//span[@class="b text-title display'
                                       '-block"]')[1].text
                except Exception as err:
                    logging.error(f'{err}', exc_info=True)
            try:
                sales = soup.select('#content > div.shop-home > div.wt-body-max'
                                    '-width.wt-pr-xs-2.wt-pr-md-4.wt-pl-xs-2.wt'
                                    '-pl-md-4 > div:nth-child(2) > span > div.'
                                    'display-flex-lg > div.hide-xs.hide-sm.hide'
                                    '-md.pl-xs-0.shop-home-wider-sections.mr-lg'
                                    '-4.pr-xs-0 > div.mt-lg-5.pt-lg-2.bt-xs-1 >'
                                    ' div:nth-child(1)')[0].text
            except Exception as err:
                logging.error(f'{err}', exc_info=True)
                sales = '0'
            if sales == '0':
                try:
                    sales = soup.select('#about > div > div > div.shop-home-'
                                        'wider-sections.mr-lg-4 > div > div > '
                                        'div.mr-xs-6 > span')[0].text
                except Exception as err:
                    logging.error(f'{err}', exc_info=True)
            if sales == '0':
                try:
                    sales = soup.select('#content > div.shop-home > div:nth-'
                                        'child(1) > div.wt-body-max-width.wt-'
                                        'pr-xs-2.wt-pr-md-4.wt-pl-xs-2.wt-pl-'
                                        'md-4 > div > div > div > div.wt-max-'
                                        'width-full.wt-grid.wt-pr-lg-5.wt-'
                                        'width-full > div.wt-grid__item-xs-12'
                                        '.wt-display-flex-xs.wt-grid__item-md'
                                        '-7.wt-br-md.wt-pr-md-4.wt-align-items'
                                        '-center > div.shop-home-header-info'
                                        '.shop-info.wt-pl-md-3.wt-pl-xs-2.wt'
                                        '-display-inline-block.wt-vertical'
                                        '-align-top.text-truncate-x > div.'
                                        'shop-info > div.shop-sales-reviews.'
                                        'wt-display-flex-xs.wt-align-items-'
                                        'center > span.wt-text-caption.wt-no'
                                        '-wrap')[0].text
                except Exception as err:
                    logging.error(f'{err}', exc_info=True)
            sales = sales.strip('продажи').strip('Sales')
            shops_info.append((shop, shop_link, since, sales))
    except Exception as err:
        logging.error(f'{err}', exc_info=True)
        ...

    if not os.path.isdir('etsy/media'):
        os.mkdir('etsy/media')
    filename = f'etsy/media/{parse_time}.csv'
    file = open(filename, 'w', newline='')
    writer = csv.writer(file)
    writer.writerow(
        ['Магазин', 'Ссылка на магазин', 'Год основания', 'Продажи'])
    for shop in shops_info:
        writer.writerow(shop)
    file.close()
    parse = Parse.objects.create(parse_name=parse_time, link=link)
    parse.save()
    media_files = [file.strip('.csv') for file in os.listdir('etsy/media')]
    for link in Parse.objects.all():
        if link.parse_name not in media_files:
            link.delete()


def get_shop_info(shop):
    """Получение страницы магазина."""
    return requests.get(f'https://www.etsy.com/shop/{shop}', headers=HEADERS,
                        timeout=10)
