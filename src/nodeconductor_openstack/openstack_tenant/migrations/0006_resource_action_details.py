# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import jsonfield.fields


class Migration(migrations.Migration):

    dependencies = [
        ('openstack_tenant', '0005_resources_actions'),
    ]

    operations = [
        migrations.AlterField(
            model_name='instance',
            name='action_details',
            field=jsonfield.fields.JSONField(default={}),
        ),
        migrations.AlterField(
            model_name='snapshot',
            name='action_details',
            field=jsonfield.fields.JSONField(default={}),
        ),
        migrations.AlterField(
            model_name='volume',
            name='action_details',
            field=jsonfield.fields.JSONField(default={}),
        ),
    ]
