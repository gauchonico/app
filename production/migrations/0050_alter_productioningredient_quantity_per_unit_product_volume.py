# Generated by Django 5.0.6 on 2024-08-15 07:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('production', '0049_alter_purchaseorder_status'),
    ]

    operations = [
        migrations.AlterField(
            model_name='productioningredient',
            name='quantity_per_unit_product_volume',
            field=models.DecimalField(decimal_places=2, max_digits=4),
        ),
    ]
