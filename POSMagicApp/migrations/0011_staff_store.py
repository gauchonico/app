# Generated by Django 5.0.6 on 2024-10-22 07:48

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('POSMagicApp', '0010_alter_product_category'),
        ('production', '0099_servicename_storeservice'),
    ]

    operations = [
        migrations.AddField(
            model_name='staff',
            name='store',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='production.store'),
        ),
    ]