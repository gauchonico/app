# Generated by Django 5.0.6 on 2025-01-22 23:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('production', '0148_storesalereceipt'),
    ]

    operations = [
        migrations.AlterField(
            model_name='servicesale',
            name='payment_mode',
            field=models.CharField(choices=[('cash', 'Cash'), ('mobile_money', 'Mobile Money'), ('airtel_money', 'Airtel Money'), ('visa', 'Visa'), ('mixed', 'Mixed')], default='cash', max_length=255),
        ),
    ]
