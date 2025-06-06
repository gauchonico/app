# Generated by Django 5.0.6 on 2024-11-05 15:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('production', '0124_productsaleitem'),
    ]

    operations = [
        migrations.AddField(
            model_name='servicesale',
            name='payment_mode',
            field=models.CharField(choices=[('cash', 'Cash'), ('mobile_money', 'Mobile Money'), ('visa', 'Visa'), ('mixed', 'Mixed')], default='cash', max_length=255),
        ),
        migrations.AddField(
            model_name='servicesale',
            name='payment_remarks',
            field=models.CharField(blank=True, max_length=150, null=True),
        ),
    ]
