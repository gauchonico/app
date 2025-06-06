# Generated by Django 5.0.6 on 2024-12-02 17:00

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('production', '0137_remove_rawmaterial_supplier_rawmaterial_supplier'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='rawmaterial',
            name='supplier',
        ),
        migrations.AddField(
            model_name='rawmaterial',
            name='supplier',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='raw_materials', to='production.supplier'),
        ),
    ]
