# Generated by Django 5.0.6 on 2024-10-01 11:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('production', '0089_alter_lpo_is_paid'),
    ]

    operations = [
        migrations.AddField(
            model_name='storetransfer',
            name='delivery_document',
            field=models.FileField(blank=True, null=True, upload_to='uploads/products/'),
        ),
        migrations.AddField(
            model_name='storetransfer',
            name='liv_main_transfer_number',
            field=models.CharField(blank=True, max_length=20, null=True, unique=True),
        ),
    ]