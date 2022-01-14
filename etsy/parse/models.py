"""Модуль с моделями."""
from django.db import models


class Parse(models.Model):
    link = models.URLField(verbose_name='Ссылка', help_text=
                           'Ссылка для паргинга')
    parse_date = models.DateTimeField('parse date', auto_now_add=True)
    parse_file = models.FileField(upload_to='results/', blank=True, null=True)

    def __str__(self):
        return self.link

    class Meta:
        ordering = ['-parse_date']
