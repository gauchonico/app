# Generated by Django 5.0.6 on 2024-09-19 12:22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('production', '0082_paymentvoucher'),
    ]

    operations = [
        migrations.AddField(
            model_name='paymentvoucher',
            name='voucher_number',
            field=models.CharField(blank=True, max_length=50, unique=True),
        ),
    ]