# Generated by Django 5.0.6 on 2024-10-30 12:15

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('production', '0116_accessoryinventory_quantity'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='storetransferitem',
            name='approved_quantity',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='storetransfer',
            name='status',
            field=models.CharField(choices=[('Pending', 'Pending'), ('Approved', 'Approved'), ('Completed', 'Completed')], default='Pending', max_length=20),
        ),
        migrations.CreateModel(
            name='TransferApproval',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('approved_date', models.DateTimeField(auto_now_add=True)),
                ('approved_quantity', models.PositiveIntegerField()),
                ('approved_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('transfer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='production.storetransfer')),
            ],
        ),
    ]
