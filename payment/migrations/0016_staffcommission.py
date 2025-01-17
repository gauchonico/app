# Generated by Django 3.2.5 on 2024-05-27 08:51

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('POSMagicApp', '0010_alter_product_category'),
        ('payment', '0015_auto_20240524_1107'),
    ]

    operations = [
        migrations.CreateModel(
            name='StaffCommission',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('commission_amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('date', models.DateTimeField(auto_now_add=True)),
                ('staff', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='POSMagicApp.staff')),
                ('transaction', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='payment.transaction')),
            ],
        ),
    ]
