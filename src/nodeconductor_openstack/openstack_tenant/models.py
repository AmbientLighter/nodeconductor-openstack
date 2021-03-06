from __future__ import unicode_literals

from urlparse import urlparse

from django.core.validators import RegexValidator
from django.db import models
from django.utils.encoding import python_2_unicode_compatible
from jsonfield import JSONField
from model_utils import FieldTracker
from model_utils.models import TimeStampedModel

from nodeconductor.core import models as core_models
from nodeconductor.logging.loggers import LoggableMixin
from nodeconductor.structure import models as structure_models, utils as structure_utils

from nodeconductor_openstack.openstack_base import models as openstack_base_models


class OpenStackTenantService(structure_models.Service):
    projects = models.ManyToManyField(
        structure_models.Project, related_name='openstack_tenant_services', through='OpenStackTenantServiceProjectLink')

    class Meta:
        unique_together = ('customer', 'settings')
        verbose_name = 'OpenStackTenant service'
        verbose_name_plural = 'OpenStackTenant services'

    @classmethod
    def get_url_name(cls):
        return 'openstacktenant'


class OpenStackTenantServiceProjectLink(structure_models.ServiceProjectLink):
    service = models.ForeignKey(OpenStackTenantService)

    class Meta(structure_models.ServiceProjectLink.Meta):
        verbose_name = 'OpenStackTenant service project link'
        verbose_name_plural = 'OpenStackTenant service project links'

    @classmethod
    def get_url_name(cls):
        return 'openstacktenant-spl'


class Flavor(LoggableMixin, structure_models.ServiceProperty):
    cores = models.PositiveSmallIntegerField(help_text='Number of cores in a VM')
    ram = models.PositiveIntegerField(help_text='Memory size in MiB')
    disk = models.PositiveIntegerField(help_text='Root disk size in MiB')

    @classmethod
    def get_url_name(cls):
        return 'openstacktenant-flavor'


class Image(structure_models.ServiceProperty):
    min_disk = models.PositiveIntegerField(default=0, help_text='Minimum disk size in MiB')
    min_ram = models.PositiveIntegerField(default=0, help_text='Minimum memory size in MiB')

    @classmethod
    def get_url_name(cls):
        return 'openstacktenant-image'


class SecurityGroup(core_models.DescribableMixin, structure_models.ServiceProperty):
    @classmethod
    def get_url_name(cls):
        return 'openstacktenant-sgp'


class SecurityGroupRule(openstack_base_models.BaseSecurityGroupRule):
    security_group = models.ForeignKey(SecurityGroup, related_name='rules')


@python_2_unicode_compatible
class FloatingIP(structure_models.ServiceProperty):
    address = models.GenericIPAddressField(protocol='IPv4', null=True)
    runtime_state = models.CharField(max_length=30)
    backend_network_id = models.CharField(max_length=255, editable=False)
    is_booked = models.BooleanField(default=False, help_text='Marks if floating IP has been booked for provisioning.')
    internal_ip = models.ForeignKey('InternalIP', related_name='floating_ips', null=True, on_delete=models.SET_NULL)

    class Meta:
        # It should be possible to create floating IP dynamically on instance creation
        # so floating IP with empty backend id can exist.
        unique_together = tuple()

    def __str__(self):
        return '%s:%s | %s' % (self.address, self.runtime_state, self.settings)

    @classmethod
    def get_url_name(cls):
        return 'openstacktenant-fip'

    def get_backend(self):
        return self.settings.get_backend()

    def increase_backend_quotas_usage(self, validate=True):
        self.settings.add_quota_usage(self.settings.Quotas.floating_ip_count, 1, validate=validate)


class Volume(structure_models.Storage):
    service_project_link = models.ForeignKey(
        OpenStackTenantServiceProjectLink, related_name='volumes', on_delete=models.PROTECT)
    instance = models.ForeignKey('Instance', related_name='volumes', blank=True, null=True)
    device = models.CharField(
        max_length=50, blank=True,
        validators=[RegexValidator('^/dev/[a-zA-Z0-9]+$', message='Device should match pattern "/dev/alphanumeric+"')],
        help_text='Name of volume as instance device e.g. /dev/vdb.')
    bootable = models.BooleanField(default=False)
    metadata = JSONField(blank=True)
    image = models.ForeignKey(Image, null=True)
    image_metadata = JSONField(blank=True)
    type = models.CharField(max_length=100, blank=True)
    source_snapshot = models.ForeignKey('Snapshot', related_name='volumes', null=True, on_delete=models.SET_NULL)
    # TODO: Move this fields to resource model.
    action = models.CharField(max_length=50, blank=True)
    action_details = JSONField(default={})

    tracker = FieldTracker()

    def increase_backend_quotas_usage(self, validate=True):
        settings = self.service_project_link.service.settings
        settings.add_quota_usage(settings.Quotas.volumes, 1, validate=validate)
        settings.add_quota_usage(settings.Quotas.storage, self.size, validate=validate)

    def decrease_backend_quotas_usage(self):
        settings = self.service_project_link.service.settings
        settings.add_quota_usage(settings.Quotas.volumes, -1)
        settings.add_quota_usage(settings.Quotas.storage, -self.size)

    @classmethod
    def get_url_name(cls):
        return 'openstacktenant-volume'


class Snapshot(structure_models.Storage):
    service_project_link = models.ForeignKey(
        OpenStackTenantServiceProjectLink, related_name='snapshots', on_delete=models.PROTECT)
    source_volume = models.ForeignKey(Volume, related_name='snapshots', null=True, on_delete=models.PROTECT)
    metadata = JSONField(blank=True)
    # TODO: Move this fields to resource model.
    action = models.CharField(max_length=50, blank=True)
    action_details = JSONField(default={})
    snapshot_schedule = models.ForeignKey('SnapshotSchedule',
                                          blank=True,
                                          null=True,
                                          on_delete=models.SET_NULL,
                                          related_name='snapshots')

    tracker = FieldTracker()

    kept_until = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Guaranteed time of snapshot retention. If null - keep forever.')

    @classmethod
    def get_url_name(cls):
        return 'openstacktenant-snapshot'

    def increase_backend_quotas_usage(self, validate=True):
        settings = self.service_project_link.service.settings
        settings.add_quota_usage(settings.Quotas.snapshots, 1, validate=validate)
        settings.add_quota_usage(settings.Quotas.storage, self.size, validate=validate)

    def decrease_backend_quotas_usage(self):
        settings = self.service_project_link.service.settings
        settings.add_quota_usage(settings.Quotas.snapshots, -1)
        settings.add_quota_usage(settings.Quotas.storage, -self.size)


class SnapshotRestoration(core_models.UuidMixin, TimeStampedModel):
    snapshot = models.ForeignKey(Snapshot, related_name='restorations')
    volume = models.OneToOneField(Volume, related_name='restoration')

    class Permissions(object):
        customer_path = 'snapshot__service_project_link__project__customer'
        project_path = 'snapshot__service_project_link__project'


class Instance(structure_models.VirtualMachineMixin, core_models.RuntimeStateMixin, structure_models.NewResource):

    class RuntimeStates(object):
        # All possible OpenStack Instance states on backend.
        # See http://developer.openstack.org/api-ref-compute-v2.html
        ACTIVE = 'ACTIVE'
        BUILDING = 'BUILDING'
        DELETED = 'DELETED'
        SOFT_DELETED = 'SOFT_DELETED'
        ERROR = 'ERROR'
        UNKNOWN = 'UNKNOWN'
        HARD_REBOOT = 'HARD_REBOOT'
        REBOOT = 'REBOOT'
        REBUILD = 'REBUILD'
        PASSWORD = 'PASSWORD'
        PAUSED = 'PAUSED'
        RESCUED = 'RESCUED'
        RESIZED = 'RESIZED'
        REVERT_RESIZE = 'REVERT_RESIZE'
        SHUTOFF = 'SHUTOFF'
        STOPPED = 'STOPPED'
        SUSPENDED = 'SUSPENDED'
        VERIFY_RESIZE = 'VERIFY_RESIZE'

    service_project_link = models.ForeignKey(
        OpenStackTenantServiceProjectLink, related_name='instances', on_delete=models.PROTECT)

    flavor_name = models.CharField(max_length=255, blank=True)
    flavor_disk = models.PositiveIntegerField(default=0, help_text='Flavor disk size in MiB')
    security_groups = models.ManyToManyField(SecurityGroup, related_name='instances')
    # TODO: Move this fields to resource model.
    action = models.CharField(max_length=50, blank=True)
    action_details = JSONField(default={})
    subnets = models.ManyToManyField('SubNet', through='InternalIP')

    tracker = FieldTracker()

    @property
    def external_ips(self):
        return self.floating_ips.values_list('address', flat=True)

    @property
    def internal_ips(self):
        return self.internal_ips_set.values_list('ip4_address', flat=True)

    @property
    def size(self):
        return self.volumes.aggregate(models.Sum('size'))['size']

    @classmethod
    def get_url_name(cls):
        return 'openstacktenant-instance'

    def get_log_fields(self):
        return ('uuid', 'name', 'type', 'service_project_link', 'ram', 'cores',)

    def detect_coordinates(self):
        settings = self.service_project_link.service.settings
        options = settings.options or {}
        if 'latitude' in options and 'longitude' in options:
            return structure_utils.Coordinates(latitude=settings['latitude'], longitude=settings['longitude'])
        else:
            hostname = urlparse(settings.backend_url).hostname
            if hostname:
                return structure_utils.get_coordinates_by_ip(hostname)

    def increase_backend_quotas_usage(self, validate=True):
        settings = self.service_project_link.service.settings
        settings.add_quota_usage(settings.Quotas.instances, 1, validate=validate)
        settings.add_quota_usage(settings.Quotas.ram, self.ram, validate=validate)
        settings.add_quota_usage(settings.Quotas.vcpu, self.cores, validate=validate)

    def decrease_backend_quotas_usage(self):
        settings = self.service_project_link.service.settings
        settings.add_quota_usage(settings.Quotas.instances, -1)
        settings.add_quota_usage(settings.Quotas.ram, -self.ram)
        settings.add_quota_usage(settings.Quotas.vcpu, -self.cores)

    @property
    def floating_ips(self):
        return FloatingIP.objects.filter(internal_ip__instance=self)


class Backup(structure_models.NewResource):
    service_project_link = models.ForeignKey(
        OpenStackTenantServiceProjectLink, related_name='backups', on_delete=models.PROTECT)
    instance = models.ForeignKey(Instance, related_name='backups', on_delete=models.PROTECT)
    backup_schedule = models.ForeignKey('BackupSchedule', blank=True, null=True,
                                        on_delete=models.SET_NULL,
                                        related_name='backups')
    kept_until = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Guaranteed time of backup retention. If null - keep forever.')
    metadata = JSONField(
        blank=True,
        help_text='Additional information about backup, can be used for backup restoration or deletion',
    )
    snapshots = models.ManyToManyField('Snapshot', related_name='backups')

    @classmethod
    def get_url_name(cls):
        return 'openstacktenant-backup'


class BackupRestoration(core_models.UuidMixin, TimeStampedModel):
    """ This model corresponds to instance restoration from backup. """
    backup = models.ForeignKey(Backup, related_name='restorations')
    instance = models.OneToOneField(Instance, related_name='+')
    flavor = models.ForeignKey(Flavor, related_name='+', null=True, blank=True, on_delete=models.SET_NULL)

    class Permissions(object):
        customer_path = 'backup__service_project_link__project__customer'
        project_path = 'backup__service_project_link__project'


class BaseSchedule(structure_models.NewResource, core_models.ScheduleMixin):
    retention_time = models.PositiveIntegerField(
        help_text='Retention time in days, if 0 - resource will be kept forever')
    maximal_number_of_resources = models.PositiveSmallIntegerField()
    call_count = models.PositiveSmallIntegerField(default=0, help_text="How many times a resource schedule was called.")

    class Meta(object):
        abstract = True


class BackupSchedule(BaseSchedule):
    service_project_link = models.ForeignKey(
        OpenStackTenantServiceProjectLink, related_name='backup_schedules', on_delete=models.PROTECT)
    instance = models.ForeignKey(Instance, related_name='backup_schedules')

    tracker = FieldTracker()

    def __str__(self):
        return 'BackupSchedule of %s. Active: %s' % (self.instance, self.is_active)

    @classmethod
    def get_url_name(cls):
        return 'openstacktenant-backup-schedule'


class SnapshotSchedule(BaseSchedule):
    service_project_link = models.ForeignKey(
        OpenStackTenantServiceProjectLink, related_name='snapshot_schedules', on_delete=models.PROTECT)
    source_volume = models.ForeignKey(Volume, related_name='snapshot_schedules')

    tracker = FieldTracker()

    def __str__(self):
        return 'SnapshotSchedule of %s. Active: %s' % (self.source_volume, self.is_active)

    @classmethod
    def get_url_name(cls):
        return 'openstacktenant-snapshot-schedule'


@python_2_unicode_compatible
class Network(core_models.DescribableMixin, structure_models.ServiceProperty):
    is_external = models.BooleanField(default=False)
    type = models.CharField(max_length=50, blank=True)
    segmentation_id = models.IntegerField(null=True)

    def __str__(self):
        return self.name

    @classmethod
    def get_url_name(cls):
        return 'openstacktenant-network'


@python_2_unicode_compatible
class SubNet(core_models.DescribableMixin, structure_models.ServiceProperty):
    network = models.ForeignKey(Network, related_name='subnets')
    cidr = models.CharField(max_length=32, blank=True)
    gateway_ip = models.GenericIPAddressField(protocol='IPv4', null=True)
    allocation_pools = JSONField(default={})
    ip_version = models.SmallIntegerField(default=4)
    enable_dhcp = models.BooleanField(default=True)
    dns_nameservers = JSONField(default=[], help_text='List of DNS name servers associated with the subnet.')

    def __str__(self):
        return '%s (%s)' % (self.name, self.cidr)

    @classmethod
    def get_url_name(cls):
        return 'openstacktenant-subnet'


class InternalIP(openstack_base_models.Port):
    # Name "internal_ips" is reserved by virtual machine mixin and corresponds to list of internal IPs.
    # So another related name should be used.
    instance = models.ForeignKey(Instance, related_name='internal_ips_set')
    subnet = models.ForeignKey(SubNet, related_name='internal_ips')
