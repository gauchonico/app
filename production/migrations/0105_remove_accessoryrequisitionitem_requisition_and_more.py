# Generated by Django 5.0.6 on 2024-10-22 11:28

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('production', '0104_mainstoreaccessoryrequisitionitem_price'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='accessoryrequisitionitem',
            name='requisition',
        ),
        migrations.RemoveField(
            model_name='accessoryrequisitionitem',
            name='accessory',
        ),
        migrations.CreateModel(
            name='InternalAccessoryRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('request_date', models.DateField(auto_now_add=True)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected')], max_length=20)),
                ('comments', models.TextField(blank=True)),
                ('store', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='production.store')),
            ],
        ),
        migrations.CreateModel(
            name='InternalAccessoryRequestItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity_requested', models.PositiveIntegerField()),
                ('accessory', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='production.accessory')),
                ('request', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='items', to='production.internalaccessoryrequest')),
            ],
        ),
        migrations.DeleteModel(
            name='AccessoryRequisition',
        ),
        migrations.DeleteModel(
            name='AccessoryRequisitionItem',
        ),
    ]