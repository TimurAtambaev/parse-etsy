"""Модуль с моделями."""
from django.db import models


class Parse(models.Model):
    parse_link = models.CharField(max_length=200, verbose_name='Ссылка',
                                  help_text='Ссылка для парсинга')
    parse_date = models.DateTimeField('parse date', auto_now_add=True)
    parse_file = models.FileField(upload_to='.')

    def __str__(self):
        return self.parse_link

    class Meta:
        ordering = ['-parse_date']


class Link(models.Model):
    link = models.URLField(verbose_name='Ссылка', help_text=
                           'Ссылка для парсинга')
