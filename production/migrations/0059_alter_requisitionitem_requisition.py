# Generated by Django 5.0.6 on 2024-08-28 15:27

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('production', '0058_alter_requisitionitem_requisition'),
    ]

    operations = [
        migrations.AlterField(
            model_name='requisitionitem',
            name='requisition',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='production.requisition'),
        ),
    ]