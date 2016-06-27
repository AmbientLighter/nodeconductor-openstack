from nodeconductor.core import tasks

from .. import models


class SetBackupRestorationErredTask(tasks.ErrorStateTransitionTask):
    """ Mark DR backup restoration instance as erred and delete volumes that were not created. """

    def execute(self, backup_restoration):
        instance = backup_restoration.instance
        super(SetBackupRestorationErredTask, self).execute(instance)
        # delete volumes if they were not created on backend,
        # mark as erred if creation was started, but not ended,
        # leave as is, if they are OK.
        for volume in instance.volumes.all():
            if volume.state == models.Volume.States.CREATION_SCHEDULED:
                volume.delete()
            elif volume.state == models.Volume.States.OK:
                pass
            else:
                volume.set_erred()
                volume.save(update_fields=['state'])
