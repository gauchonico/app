# Generated by Django 5.0.6 on 2024-08-24 06:49

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('production', '0055_requisitionitem_delivered_quantity'),
    ]

    operations = [
        migrations.CreateModel(
            name='GoodsReceivedNote',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('reason', models.CharField(blank=True, max_length=255, null=True)),
                ('comment', models.TextField(blank=True, null=True)),
                ('lpo', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='production.lpo')),
                ('requisition', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='production.requisition')),
            ],
        ),
    ]