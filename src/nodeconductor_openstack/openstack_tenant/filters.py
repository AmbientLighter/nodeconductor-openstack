import django_filters

from nodeconductor.core import filters as core_filters
from nodeconductor.structure import filters as structure_filters

from . import models


class OpenStackTenantServiceProjectLinkFilter(structure_filters.BaseServiceProjectLinkFilter):
    service = core_filters.URLFilter(view_name='openstacktenant-detail', name='service__uuid')

    class Meta(object):
        model = models.OpenStackTenantServiceProjectLink


class FlavorFilter(structure_filters.ServicePropertySettingsFilter):

    o = django_filters.OrderingFilter(fields=('cores', 'ram', 'disk'))

    class Meta(structure_filters.ServicePropertySettingsFilter.Meta):
        model = models.Flavor
        fields = dict({
            'cores': ['exact', 'gte', 'lte'],
            'ram': ['exact', 'gte', 'lte'],
            'disk': ['exact', 'gte', 'lte'],
        }, **{field: ['exact'] for field in structure_filters.ServicePropertySettingsFilter.Meta.fields})


class NetworkFilter(structure_filters.ServicePropertySettingsFilter):

    class Meta(structure_filters.ServicePropertySettingsFilter.Meta):
        model = models.Network
        fields = structure_filters.ServicePropertySettingsFilter.Meta.fields + ('type', 'is_external')


class SubNetFilter(structure_filters.ServicePropertySettingsFilter):
    network = core_filters.URLFilter(view_name='openstacktenant-network-detail', name='network__uuid')
    network_uuid = django_filters.UUIDFilter(name='network__uuid')

    class Meta(structure_filters.ServicePropertySettingsFilter.Meta):
        model = models.SubNet
        fields = structure_filters.ServicePropertySettingsFilter.Meta.fields + ('ip_version', 'enable_dhcp')


class FloatingIPFilter(structure_filters.ServicePropertySettingsFilter):

    class Meta(structure_filters.ServicePropertySettingsFilter.Meta):
        model = models.FloatingIP
        fields = structure_filters.ServicePropertySettingsFilter.Meta.fields + ('runtime_state', 'is_booked')


class VolumeFilter(structure_filters.BaseResourceFilter):
    instance = core_filters.URLFilter(view_name='openstacktenant-instance-detail', name='instance__uuid')
    instance_uuid = django_filters.UUIDFilter(name='instance__uuid')

    snapshot = core_filters.URLFilter(
        view_name='openstacktenant-snapshot-detail', name='restoration__snapshot__uuid')
    snapshot_uuid = django_filters.UUIDFilter(name='restoration__snapshot__uuid')

    class Meta(structure_filters.BaseResourceFilter.Meta):
        model = models.Volume
        fields = structure_filters.BaseResourceFilter.Meta.fields + ('runtime_state',)


class SnapshotFilter(structure_filters.BaseResourceFilter):
    source_volume_uuid = django_filters.UUIDFilter(name='source_volume__uuid')
    source_volume = core_filters.URLFilter(view_name='openstacktenant-volume-detail', name='source_volume__uuid')

    snapshot_schedule = core_filters.URLFilter(
        view_name='openstacktenant-snapshot-schedule-detail', name='snapshot_schedule__uuid')
    snapshot_schedule_uuid = django_filters.UUIDFilter(name='snapshot_schedule__uuid')

    class Meta(structure_filters.BaseResourceFilter.Meta):
        model = models.Snapshot
        fields = structure_filters.BaseResourceFilter.Meta.fields + ('runtime_state',)


class InstanceFilter(structure_filters.BaseResourceFilter):
    tenant_uuid = django_filters.UUIDFilter(name='tenant__uuid')

    class Meta(structure_filters.BaseResourceFilter.Meta):
        model = models.Instance
        fields = structure_filters.BaseResourceFilter.Meta.fields + ('runtime_state',)


class BackupFilter(structure_filters.BaseResourceFilter):
    instance = core_filters.URLFilter(view_name='openstacktenant-instance-detail', name='instance__uuid')
    instance_uuid = django_filters.UUIDFilter(name='instance__uuid')
    backup_schedule = core_filters.URLFilter(
        view_name='openstacktenant-backup-schedule-detail', name='backup_schedule__uuid')
    backup_schedule_uuid = django_filters.UUIDFilter(name='backup_schedule__uuid')

    class Meta(structure_filters.BaseResourceFilter.Meta):
        model = models.Backup


class BackupScheduleFilter(structure_filters.BaseResourceFilter):
    instance = core_filters.URLFilter(view_name='openstacktenant-instance-detail', name='instance__uuid')
    instance_uuid = django_filters.UUIDFilter(name='instance__uuid')

    class Meta(object):
        model = models.BackupSchedule


class SnapshotScheduleFilter(structure_filters.BaseResourceFilter):
    source_volume = core_filters.URLFilter(view_name='openstacktenant-volume-detail', name='source_volume__uuid')
    source_volume_uuid = django_filters.UUIDFilter(name='source_volume__uuid')

    class Meta(structure_filters.BaseResourceFilter.Meta):
        model = models.SnapshotSchedule


class SecurityGroupFilter(structure_filters.ServicePropertySettingsFilter):
    class Meta(structure_filters.ServicePropertySettingsFilter.Meta):
        model = models.SecurityGroup


class ImageFilter(structure_filters.ServicePropertySettingsFilter):
    class Meta(structure_filters.ServicePropertySettingsFilter.Meta):
        model = models.Image
