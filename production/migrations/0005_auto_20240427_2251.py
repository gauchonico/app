# Generated by Django 3.2.5 on 2024-04-27 22:51

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('production', '0004_alter_rawmaterialinventory_raw_material'),
    ]

    operations = [
        migrations.CreateModel(
            name='StoreAlerts',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('message', models.TextField(blank=True, max_length=100)),
                ('alert_type', models.CharField(max_length=100)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('handled', models.BooleanField(default=False)),
                ('handled_at', models.DateTimeField(blank=True, null=True)),
            ],
        ),
        migrations.AddField(
            model_name='purchaseorder',
            name='fullfilled_qty',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='purchaseorder',
            name='quantity',
            field=models.PositiveIntegerField(default=0),
        ),
    ]
