# Generated by Django 5.0.6 on 2024-11-07 08:53

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('production', '0125_servicesale_payment_mode_servicesale_payment_remarks'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='storeaccessoryinventory',
            options={'verbose_name_plural': 'Store Accessory Inventories'},
        ),
        migrations.AlterField(
            model_name='accessorysaleitem',
            name='sale',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='accessory_sale_items', to='production.servicesale'),
        ),
        migrations.AlterField(
            model_name='productsaleitem',
            name='sale',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='product_sale_items', to='production.servicesale'),
        ),
        migrations.AlterField(
            model_name='servicesaleitem',
            name='sale',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='service_sale_items', to='production.servicesale'),
        ),
    ]
