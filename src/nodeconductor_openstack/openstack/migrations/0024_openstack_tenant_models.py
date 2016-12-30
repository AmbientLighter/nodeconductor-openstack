# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('openstack', '0023_instance_state'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='backup',
            name='backup_schedule',
        ),
        migrations.RemoveField(
            model_name='backup',
            name='instance',
        ),
        migrations.RemoveField(
            model_name='backup',
            name='snapshots',
        ),
        migrations.RemoveField(
            model_name='backup',
            name='tenant',
        ),
        migrations.RemoveField(
            model_name='backuprestoration',
            name='backup',
        ),
        migrations.RemoveField(
            model_name='backuprestoration',
            name='flavor',
        ),
        migrations.RemoveField(
            model_name='backuprestoration',
            name='instance',
        ),
        migrations.RemoveField(
            model_name='backupschedule',
            name='instance',
        ),
        migrations.RemoveField(
            model_name='drbackup',
            name='backup_schedule',
        ),
        migrations.RemoveField(
            model_name='drbackup',
            name='service_project_link',
        ),
        migrations.RemoveField(
            model_name='drbackup',
            name='source_instance',
        ),
        migrations.RemoveField(
            model_name='drbackup',
            name='tags',
        ),
        migrations.RemoveField(
            model_name='drbackup',
            name='temporary_snapshots',
        ),
        migrations.RemoveField(
            model_name='drbackup',
            name='temporary_volumes',
        ),
        migrations.RemoveField(
            model_name='drbackup',
            name='tenant',
        ),
        migrations.RemoveField(
            model_name='drbackup',
            name='volume_backups',
        ),
        migrations.RemoveField(
            model_name='drbackuprestoration',
            name='backup',
        ),
        migrations.RemoveField(
            model_name='drbackuprestoration',
            name='flavor',
        ),
        migrations.RemoveField(
            model_name='drbackuprestoration',
            name='instance',
        ),
        migrations.RemoveField(
            model_name='drbackuprestoration',
            name='tenant',
        ),
        migrations.RemoveField(
            model_name='drbackuprestoration',
            name='volume_backup_restorations',
        ),
        migrations.RemoveField(
            model_name='instance',
            name='security_groups',
        ),
        migrations.RemoveField(
            model_name='instance',
            name='service_project_link',
        ),
        migrations.RemoveField(
            model_name='instance',
            name='tags',
        ),
        migrations.RemoveField(
            model_name='instance',
            name='tenant',
        ),
        migrations.RemoveField(
            model_name='snapshot',
            name='service_project_link',
        ),
        migrations.RemoveField(
            model_name='snapshot',
            name='source_volume',
        ),
        migrations.RemoveField(
            model_name='snapshot',
            name='tags',
        ),
        migrations.RemoveField(
            model_name='snapshot',
            name='tenant',
        ),
        migrations.RemoveField(
            model_name='volume',
            name='image',
        ),
        migrations.RemoveField(
            model_name='volume',
            name='instance',
        ),
        migrations.RemoveField(
            model_name='volume',
            name='service_project_link',
        ),
        migrations.RemoveField(
            model_name='volume',
            name='source_snapshot',
        ),
        migrations.RemoveField(
            model_name='volume',
            name='tags',
        ),
        migrations.RemoveField(
            model_name='volume',
            name='tenant',
        ),
        migrations.RemoveField(
            model_name='volumebackup',
            name='record',
        ),
        migrations.RemoveField(
            model_name='volumebackup',
            name='service_project_link',
        ),
        migrations.RemoveField(
            model_name='volumebackup',
            name='source_volume',
        ),
        migrations.RemoveField(
            model_name='volumebackup',
            name='tags',
        ),
        migrations.RemoveField(
            model_name='volumebackup',
            name='tenant',
        ),
        migrations.RemoveField(
            model_name='volumebackuprestoration',
            name='mirorred_volume_backup',
        ),
        migrations.RemoveField(
            model_name='volumebackuprestoration',
            name='tenant',
        ),
        migrations.RemoveField(
            model_name='volumebackuprestoration',
            name='volume',
        ),
        migrations.RemoveField(
            model_name='volumebackuprestoration',
            name='volume_backup',
        ),
        migrations.DeleteModel(
            name='Backup',
        ),
        migrations.DeleteModel(
            name='BackupRestoration',
        ),
        migrations.DeleteModel(
            name='BackupSchedule',
        ),
        migrations.DeleteModel(
            name='DRBackup',
        ),
        migrations.DeleteModel(
            name='DRBackupRestoration',
        ),
        migrations.DeleteModel(
            name='Instance',
        ),
        migrations.DeleteModel(
            name='Snapshot',
        ),
        migrations.DeleteModel(
            name='Volume',
        ),
        migrations.DeleteModel(
            name='VolumeBackup',
        ),
        migrations.DeleteModel(
            name='VolumeBackupRecord',
        ),
        migrations.DeleteModel(
            name='VolumeBackupRestoration',
        ),
    ]
