# Generated by Django 5.0.6 on 2024-10-09 06:35

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('production', '0096_livaramainstore_adjustment_date_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='inventoryadjustment',
            name='transfer_date',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='inventoryadjustment',
            name='transfer_to_store',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='production.store'),
        ),
    ]
