# Generated by Django 5.0.6 on 2024-06-25 20:14

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('production', '0035_alter_saleitem_quantity_alter_saleitem_total_price'),
    ]

    operations = [
        migrations.AlterField(
            model_name='storesale',
            name='due_date',
            field=models.DateField(blank=True, null=True),
        ),
    ]
