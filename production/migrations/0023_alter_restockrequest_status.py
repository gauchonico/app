# Generated by Django 3.2.5 on 2024-05-30 08:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('production', '0022_restockrequest_stocktransfer_store_storeinventory'),
    ]

    operations = [
        migrations.AlterField(
            model_name='restockrequest',
            name='status',
            field=models.CharField(choices=[('pending', 'Pending'), ('approved', 'Approved'), ('delivered', 'Delivered'), ('rejected', 'Rejected')], default='pending', max_length=255),
        ),
    ]