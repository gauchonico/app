# Generated by Django 5.0.6 on 2024-09-04 09:43

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('production', '0070_alter_replacenote_status'),
    ]

    operations = [
        migrations.AlterField(
            model_name='rawmaterialinventory',
            name='adjustment',
            field=models.DecimalField(decimal_places=5, default=0.0, max_digits=15),
        ),
    ]