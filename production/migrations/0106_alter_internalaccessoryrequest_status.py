# Generated by Django 5.0.6 on 2024-10-22 12:36

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('production', '0105_remove_accessoryrequisitionitem_requisition_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='internalaccessoryrequest',
            name='status',
            field=models.CharField(choices=[('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected')], default='pending', max_length=20),
        ),
    ]