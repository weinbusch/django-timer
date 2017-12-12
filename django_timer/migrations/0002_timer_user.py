# -*- coding: utf-8 -*-
# Generated by Django 1.11.4 on 2017-12-12 11:24
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('django_timer', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='timer',
            name='user',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
    ]