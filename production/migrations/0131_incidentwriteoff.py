# Generated by Django 5.0.6 on 2024-11-16 22:10

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('production', '0130_alter_rawmaterialinventory_adjustment'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='IncidentWriteOff',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', models.DecimalField(decimal_places=3, default=0, max_digits=5)),
                ('reason', models.TextField()),
                ('date', models.DateField(auto_now_add=True)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('approved', 'Approved')], default='pending', max_length=20)),
                ('raw_material', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='write_offs', to='production.rawmaterial')),
                ('written_off_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Incident Write-Off',
                'verbose_name_plural': 'Incident Write-Offs',
            },
        ),
    ]