"""Модуль с моделями."""
from django.db import models


class Parse(models.Model):
    parse_name = models.CharField(max_length=200, default='no-time')
    parse_date = models.DateTimeField('parse date', auto_now_add=True)

    def __str__(self):
        return self.parse_name

    class Meta:
        ordering = ['-parse_date']


class Link(models.Model):
    link = models.URLField(max_length=500, verbose_name='Ссылка')
