# Generated by Django 3.2.5 on 2024-05-16 11:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('production', '0018_manufactureproduct_labor_cost_per_unit'),
    ]

    operations = [
        migrations.CreateModel(
            name='UnitOfMeasurement',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50, unique=True)),
            ],
        ),
    ]
