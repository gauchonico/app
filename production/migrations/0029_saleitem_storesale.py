# Generated by Django 3.2.5 on 2024-06-15 15:37

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('POSMagicApp', '0010_alter_product_category'),
        ('production', '0028_auto_20240614_0715'),
    ]

    operations = [
        migrations.CreateModel(
            name='StoreSale',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sale_date', models.DateTimeField(default=0)),
                ('payment_status', models.CharField(choices=[('pending', 'Pending'), ('paid', 'Paid'), ('overdue', 'Overdue')], default='pending', max_length=255)),
                ('due_date', models.DateField(blank=True, null=True)),
                ('status', models.CharField(choices=[('ordered', 'Ordered'), ('delivered', 'Delivered')], default='ordered', max_length=255)),
                ('withhold_tax', models.BooleanField(default=False)),
                ('vat', models.BooleanField(default=False)),
                ('total_amount', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('customer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='POSMagicApp.customer')),
            ],
        ),
        migrations.CreateModel(
            name='SaleItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', models.PositiveIntegerField()),
                ('unit_price', models.DecimalField(decimal_places=2, max_digits=10)),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='production.production')),
                ('sale', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='production.storesale')),
            ],
        ),
    ]
