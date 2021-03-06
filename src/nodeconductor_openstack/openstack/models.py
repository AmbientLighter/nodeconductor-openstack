from __future__ import unicode_literals

from django.db import models
from django.utils.encoding import python_2_unicode_compatible
from jsonfield import JSONField
from model_utils import FieldTracker

from nodeconductor.core import models as core_models
from nodeconductor.logging.loggers import LoggableMixin
from nodeconductor.quotas.fields import QuotaField, UsageAggregatorQuotaField, CounterQuotaField
from nodeconductor.quotas.models import QuotaModelMixin
from nodeconductor.structure import models as structure_models

from nodeconductor_openstack.openstack_base import models as openstack_base_models


class ServiceUsageAggregatorQuotaField(UsageAggregatorQuotaField):
    def __init__(self, **kwargs):
        super(ServiceUsageAggregatorQuotaField, self).__init__(
            get_children=lambda service: Tenant.objects.filter(
                service_project_link__service=service
            ), **kwargs)


class OpenStackService(structure_models.Service):
    projects = models.ManyToManyField(
        structure_models.Project, related_name='openstack_services', through='OpenStackServiceProjectLink')

    class Meta:
        unique_together = ('customer', 'settings')
        verbose_name = 'OpenStack service'
        verbose_name_plural = 'OpenStack services'

    class Quotas(QuotaModelMixin.Quotas):
        tenant_count = CounterQuotaField(
            target_models=lambda: [Tenant],
            path_to_scope='service_project_link.service'
        )
        vcpu = ServiceUsageAggregatorQuotaField()
        ram = ServiceUsageAggregatorQuotaField()
        storage = ServiceUsageAggregatorQuotaField()
        instances = ServiceUsageAggregatorQuotaField()
        security_group_count = ServiceUsageAggregatorQuotaField()
        security_group_rule_count = ServiceUsageAggregatorQuotaField()
        floating_ip_count = ServiceUsageAggregatorQuotaField()
        volumes = ServiceUsageAggregatorQuotaField()
        snapshots = ServiceUsageAggregatorQuotaField()

    @classmethod
    def get_url_name(cls):
        return 'openstack'

    def is_admin_tenant(self):
        return self.settings.get_option('is_admin')


class OpenStackServiceProjectLink(structure_models.ServiceProjectLink):

    service = models.ForeignKey(OpenStackService)

    class Meta(structure_models.ServiceProjectLink.Meta):
        verbose_name = 'OpenStack service project link'
        verbose_name_plural = 'OpenStack service project links'

    @classmethod
    def get_url_name(cls):
        return 'openstack-spl'

    # XXX: Hack for statistics: return quotas of tenants as quotas of SPLs.
    @classmethod
    def get_sum_of_quotas_as_dict(cls, spls, quota_names=None, fields=['usage', 'limit']):
        tenants = Tenant.objects.filter(service_project_link__in=spls)
        return Tenant.get_sum_of_quotas_as_dict(tenants, quota_names=quota_names, fields=fields)


class Flavor(LoggableMixin, structure_models.ServiceProperty):
    cores = models.PositiveSmallIntegerField(help_text='Number of cores in a VM')
    ram = models.PositiveIntegerField(help_text='Memory size in MiB')
    disk = models.PositiveIntegerField(help_text='Root disk size in MiB')

    @classmethod
    def get_url_name(cls):
        return 'openstack-flavor'


class Image(structure_models.ServiceProperty):
    min_disk = models.PositiveIntegerField(default=0, help_text='Minimum disk size in MiB')
    min_ram = models.PositiveIntegerField(default=0, help_text='Minimum memory size in MiB')

    @classmethod
    def get_url_name(cls):
        return 'openstack-image'


class SecurityGroup(structure_models.NewResource):
    service_project_link = models.ForeignKey(
        OpenStackServiceProjectLink, related_name='security_groups')
    tenant = models.ForeignKey('Tenant', related_name='security_groups')

    def get_backend(self):
        return self.tenant.get_backend()

    @classmethod
    def get_url_name(cls):
        return 'openstack-sgp'

    def increase_backend_quotas_usage(self, validate=True):
        self.tenant.add_quota_usage(self.tenant.Quotas.security_group_count, 1, validate=validate)
        self.tenant.add_quota_usage(self.tenant.Quotas.security_group_rule_count, self.rules.count(), validate=validate)

    def decrease_backend_quotas_usage(self):
        self.tenant.add_quota_usage(self.tenant.Quotas.security_group_count, -1)
        self.tenant.add_quota_usage(self.tenant.Quotas.security_group_rule_count, -self.rules.count())

    def change_backend_quotas_usage_on_rules_update(self, old_rules_count, validate=True):
        count = self.rules.count() - old_rules_count
        self.tenant.add_quota_usage(self.tenant.Quotas.security_group_rule_count, count, validate=validate)


class SecurityGroupRule(openstack_base_models.BaseSecurityGroupRule):
    security_group = models.ForeignKey(SecurityGroup, related_name='rules')


class IpMapping(core_models.UuidMixin):

    class Permissions(object):
        project_path = 'project'
        customer_path = 'project__customer'

    public_ip = models.GenericIPAddressField(protocol='IPv4')
    private_ip = models.GenericIPAddressField(protocol='IPv4')
    project = models.ForeignKey(structure_models.Project, related_name='+')

    @classmethod
    def get_url_name(cls):
        return 'openstack-ip-mapping'


@python_2_unicode_compatible
class FloatingIP(core_models.RuntimeStateMixin, structure_models.NewResource):
    service_project_link = models.ForeignKey(
        OpenStackServiceProjectLink, related_name='floating_ips')
    tenant = models.ForeignKey('Tenant', related_name='floating_ips')
    address = models.GenericIPAddressField(null=True, blank=True, protocol='IPv4')
    backend_network_id = models.CharField(max_length=255, editable=False)

    tracker = FieldTracker()

    def get_backend(self):
        return self.tenant.get_backend()

    @classmethod
    def get_url_name(cls):
        return 'openstack-fip'

    def __str__(self):
        return '%s:%s (%s)' % (self.address, self.runtime_state, self.service_project_link)

    def increase_backend_quotas_usage(self, validate=True):
        self.tenant.add_quota_usage(self.tenant.Quotas.floating_ip_count, 1, validate=validate)

    def decrease_backend_quotas_usage(self):
        self.tenant.add_quota_usage(self.tenant.Quotas.floating_ip_count, -1)


class Tenant(structure_models.PrivateCloud):

    class Quotas(QuotaModelMixin.Quotas):
        vcpu = QuotaField(default_limit=20, is_backend=True)
        ram = QuotaField(default_limit=51200, is_backend=True)
        storage = QuotaField(default_limit=1024000, is_backend=True)
        instances = QuotaField(default_limit=30, is_backend=True)
        security_group_count = QuotaField(default_limit=100, is_backend=True)
        security_group_rule_count = QuotaField(default_limit=100, is_backend=True)
        floating_ip_count = QuotaField(default_limit=50, is_backend=True)
        volumes = QuotaField(default_limit=50, is_backend=True)
        snapshots = QuotaField(default_limit=50, is_backend=True)
        network_count = QuotaField(default_limit=10, is_backend=True)
        subnet_count = QuotaField(default_limit=10, is_backend=True)

    service_project_link = models.ForeignKey(
        OpenStackServiceProjectLink, related_name='tenants', on_delete=models.PROTECT)

    internal_network_id = models.CharField(max_length=64, blank=True)
    external_network_id = models.CharField(max_length=64, blank=True)
    availability_zone = models.CharField(
        max_length=100, blank=True,
        help_text='Optional availability group. Will be used for all instances provisioned in this tenant'
    )
    user_username = models.CharField(max_length=50, blank=True)
    user_password = models.CharField(max_length=50, blank=True)

    tracker = FieldTracker()

    def get_backend(self):
        return self.service_project_link.service.get_backend(tenant_id=self.backend_id)

    def get_log_fields(self):
        return super(Tenant, self).get_log_fields() + ('extra_configuration',)

    def create_service(self, name):
        """
        Create non-admin service from this tenant.
        """
        admin_settings = self.service_project_link.service.settings
        customer = self.service_project_link.project.customer
        new_settings = structure_models.ServiceSettings.objects.create(
            name=name,
            scope=self,
            customer=customer,
            type=admin_settings.type,
            backend_url=admin_settings.backend_url,
            username=self.user_username,
            password=self.user_password,
            options={
                'tenant_name': self.name,
                'is_admin': False,
                'availability_zone': self.availability_zone,
                'external_network_id': self.external_network_id
            }
        )
        return OpenStackService.objects.create(
            settings=new_settings,
            customer=customer
        )


class Network(core_models.RuntimeStateMixin, structure_models.NewResource):
    service_project_link = models.ForeignKey(
        OpenStackServiceProjectLink, related_name='networks', on_delete=models.PROTECT)
    tenant = models.ForeignKey(Tenant, related_name='networks')
    is_external = models.BooleanField(default=False)
    type = models.CharField(max_length=50, blank=True)
    segmentation_id = models.IntegerField(null=True)

    def get_backend(self):
        return self.tenant.get_backend()

    @classmethod
    def get_url_name(cls):
        return 'openstack-network'

    def increase_backend_quotas_usage(self, validate=True):
        self.tenant.add_quota_usage(self.tenant.Quotas.network_count, 1, validate=validate)

    def decrease_backend_quotas_usage(self):
        self.tenant.add_quota_usage(self.tenant.Quotas.network_count, -1)


class SubNet(structure_models.NewResource):
    service_project_link = models.ForeignKey(
        OpenStackServiceProjectLink, related_name='subnets', on_delete=models.PROTECT)
    network = models.ForeignKey(Network, related_name='subnets')
    cidr = models.CharField(max_length=32, blank=True)
    gateway_ip = models.GenericIPAddressField(protocol='IPv4', null=True)
    allocation_pools = JSONField(default={})
    ip_version = models.SmallIntegerField(default=4)
    enable_dhcp = models.BooleanField(default=True)
    dns_nameservers = JSONField(default=[], help_text='List of DNS name servers associated with the subnet.')

    def get_backend(self):
        return self.network.get_backend()

    @classmethod
    def get_url_name(cls):
        return 'openstack-subnet'

    def increase_backend_quotas_usage(self, validate=True):
        self.network.tenant.add_quota_usage(self.network.tenant.Quotas.subnet_count, 1, validate=validate)

    def decrease_backend_quotas_usage(self):
        self.network.tenant.add_quota_usage(self.network.tenant.Quotas.subnet_count, -1)
