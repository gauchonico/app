# Generated by Django 5.0.6 on 2024-10-28 07:18

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('production', '0113_production_price'),
    ]

    operations = [
        migrations.CreateModel(
            name='ManufacturedProductIngredient',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity_used', models.DecimalField(decimal_places=2, max_digits=10)),
                ('manufactured_product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='used_ingredients', to='production.manufactureproduct')),
                ('raw_material', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='production.rawmaterial')),
            ],
        ),
    ]
