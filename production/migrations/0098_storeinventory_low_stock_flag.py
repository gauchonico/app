# Generated by Django 5.0.6 on 2024-10-10 21:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('production', '0097_inventoryadjustment_transfer_date_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='storeinventory',
            name='low_stock_flag',
            field=models.BooleanField(default=False),
        ),
    ]
