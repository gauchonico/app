# Generated by Django 5.0.6 on 2024-10-09 06:12

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('production', '0095_storeinventory_previous_quantity'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='livaramainstore',
            name='adjustment_date',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='livaramainstore',
            name='adjustment_reason',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='livaramainstore',
            name='previous_quantity',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.CreateModel(
            name='LivaraInventoryAdjustment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('adjusted_quantity', models.IntegerField()),
                ('adjustment_date', models.DateTimeField(auto_now_add=True)),
                ('adjustment_reason', models.CharField(max_length=255)),
                ('adjusted_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('store_inventory', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='adjustments', to='production.livaramainstore')),
            ],
        ),
    ]