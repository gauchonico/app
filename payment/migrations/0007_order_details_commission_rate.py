# Generated by Django 3.2.5 on 2024-05-24 08:09

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('payment', '0006_commissionrate'),
    ]

    operations = [
        migrations.AddField(
            model_name='order_details',
            name='commission_rate',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='payment.commissionrate'),
        ),
    ]