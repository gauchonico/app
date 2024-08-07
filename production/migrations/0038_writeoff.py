# Generated by Django 5.0.6 on 2024-07-15 12:58

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('production', '0037_manufactureproduct_production_order'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='WriteOff',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', models.PositiveIntegerField()),
                ('reason', models.CharField(max_length=255)),
                ('date', models.DateField(auto_now_add=True)),
                ('initiated_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('manufactured_product_inventory', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='write_offs', to='production.manufacturedproductinventory')),
            ],
        ),
    ]
