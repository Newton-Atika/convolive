# Generated by Django 5.0.4 on 2025-07-12 02:35

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='ChatMessages',
            new_name='ChatMessage',
        ),
    ]
