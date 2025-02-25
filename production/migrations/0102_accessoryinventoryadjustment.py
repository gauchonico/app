# Generated by Django 5.0.6 on 2024-10-22 08:55

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('production', '0101_mainstoreaccessoryrequisition_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='AccessoryInventoryAdjustment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity_adjusted', models.IntegerField()),
                ('adjustment_date', models.DateTimeField(auto_now_add=True)),
                ('reason', models.TextField(blank=True)),
                ('accessory', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='adjustments', to='production.accessory')),
            ],
        ),
    ]
