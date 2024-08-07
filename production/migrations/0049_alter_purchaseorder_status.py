# Generated by Django 5.0.6 on 2024-07-30 13:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('production', '0048_store_manager'),
    ]

    operations = [
        migrations.AlterField(
            model_name='purchaseorder',
            name='status',
            field=models.CharField(choices=[('pending', 'Pending'), ('approved', 'Approved'), ('fulfilled', 'Fulfilled'), ('rejected', 'Rejected')], default='pending', max_length=255),
        ),
    ]
