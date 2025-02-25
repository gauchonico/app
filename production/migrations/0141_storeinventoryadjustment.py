# Generated by Django 5.0.6 on 2024-12-18 08:19

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('production', '0140_remove_rawmaterial_supplier'),
    ]

    operations = [
        migrations.CreateModel(
            name='StoreInventoryAdjustment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('adjustment_type', models.CharField(choices=[('requisition', 'Internal Requisition'), ('sale', 'Service Sale'), ('other', 'Other')], max_length=20)),
                ('quantity', models.IntegerField()),
                ('reason', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now=True)),
                ('accessory_inventory', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='adjustments', to='production.storeaccessoryinventory')),
            ],
        ),
    ]
