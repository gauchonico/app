# Generated by Django 5.0.6 on 2024-07-15 22:03

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('production', '0042_alter_saleitem_product'),
    ]

    operations = [
        migrations.AlterField(
            model_name='saleitem',
            name='product',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='production.livaramainstore'),
        ),
    ]