# Generated by Django 3.2.7 on 2021-09-18 18:07

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('app_base', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='CustomerModel',
            fields=[
                ('baseuser_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='app_base.baseuser')),
                ('points', models.IntegerField(default=100)),
            ],
            options={
                'abstract': False,
            },
            bases=('app_base.baseuser',),
        ),
    ]