# Generated by Django 5.0.6 on 2024-10-30 12:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('production', '0118_remove_storetransferitem_approved_quantity_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='restockrequest',
            name='liv_store_transfer_number',
            field=models.CharField(blank=True, max_length=50, unique=True),
        ),
    ]
