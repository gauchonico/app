# Generated by Django 5.0.6 on 2024-10-23 09:30

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('production', '0106_alter_internalaccessoryrequest_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='accessoryinventoryadjustment',
            name='store',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='adjustments', to='production.store'),
        ),
    ]