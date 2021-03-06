import uuid

from django.utils import six
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, decorators, response, permissions, status, serializers as rf_serializers
from rest_framework.exceptions import ValidationError

from nodeconductor.core import validators as core_validators, exceptions as core_exceptions
from nodeconductor.structure import (
    views as structure_views, SupportedServices, executors as structure_executors,
    filters as structure_filters, permissions as structure_permissions)
from nodeconductor.structure.managers import filter_queryset_for_user

from . import models, filters, serializers, executors


class GenericImportMixin(object):
    """
    This mixin selects serializer class by matching resource_type query parameter
    against model name using import_serializers mapping.
    """
    import_serializers = {}

    def _can_import(self):
        return self.import_serializers != {}

    def get_serializer_class(self):
        if self.request.method == 'POST' and self.action == 'link':
            resource_type = self.request.data.get('resource_type') or self.request.query_params.get('resource_type')

            items = self.import_serializers.items()
            if len(items) == 1:
                model_cls, serializer_cls = items[0]
                return serializer_cls

            for model_cls, serializer_cls in items:
                if resource_type == SupportedServices.get_name_for_model(model_cls):
                    return serializer_cls

        return super(GenericImportMixin, self).get_serializer_class()


class OpenStackServiceViewSet(GenericImportMixin, structure_views.BaseServiceViewSet):
    queryset = models.OpenStackService.objects.all()
    serializer_class = serializers.ServiceSerializer
    import_serializer_class = serializers.TenantImportSerializer
    import_serializers = {
        models.Tenant: serializers.TenantImportSerializer,
    }

    def list(self, request, *args, **kwargs):
        """
        To create a service, issue a **POST** to */api/openstack/* as a customer owner.

        You can create service based on shared service settings. Example:

        .. code-block:: http

            POST /api/openstack/ HTTP/1.1
            Content-Type: application/json
            Accept: application/json
            Authorization: Token c84d653b9ec92c6cbac41c706593e66f567a7fa4
            Host: example.com

            {
                "name": "Common OpenStack",
                "customer": "http://example.com/api/customers/1040561ca9e046d2b74268600c7e1105/",
                "settings": "http://example.com/api/service-settings/93ba615d6111466ebe3f792669059cb4/"
            }

        Or provide your own credentials. Example:

        .. code-block:: http

            POST /api/openstack/ HTTP/1.1
            Content-Type: application/json
            Accept: application/json
            Authorization: Token c84d653b9ec92c6cbac41c706593e66f567a7fa4
            Host: example.com

            {
                "name": "My OpenStack",
                "customer": "http://example.com/api/customers/1040561ca9e046d2b74268600c7e1105/",
                "backend_url": "http://keystone.example.com:5000/v2.0",
                "username": "admin",
                "password": "secret"
            }
        """

        return super(OpenStackServiceViewSet, self).list(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        """
        To update OpenStack service issue **PUT** or **PATCH** against */api/openstack/<service_uuid>/*
        as a customer owner. You can update service's `name` and `available_for_all` fields.

        Example of a request:

        .. code-block:: http

            PUT /api/openstack/c6526bac12b343a9a65c4cd6710666ee/ HTTP/1.1
            Content-Type: application/json
            Accept: application/json
            Authorization: Token c84d653b9ec92c6cbac41c706593e66f567a7fa4
            Host: example.com

            {
                "name": "My OpenStack2"
            }

        To remove OpenStack service, issue **DELETE** against */api/openstack/<service_uuid>/* as
        staff user or customer owner.
        """
        return super(OpenStackServiceViewSet, self).retrieve(request, *args, **kwargs)

    def get_import_context(self):
        context = {'resource_type': self.request.query_params.get('resource_type')}
        tenant_uuid = self.request.query_params.get('tenant_uuid')
        if tenant_uuid:
            try:
                uuid.UUID(tenant_uuid)
            except ValueError:
                raise ValidationError('Invalid tenant UUID')
            queryset = filter_queryset_for_user(models.Tenant.objects.all(), self.request.user)
            tenant = queryset.filter(service_project_link__service=self.get_object(),
                                     uuid=tenant_uuid).first()
            context['tenant'] = tenant
        return context


class OpenStackServiceProjectLinkViewSet(structure_views.BaseServiceProjectLinkViewSet):
    queryset = models.OpenStackServiceProjectLink.objects.all()
    serializer_class = serializers.ServiceProjectLinkSerializer
    filter_class = filters.OpenStackServiceProjectLinkFilter

    def list(self, request, *args, **kwargs):
        """
        In order to be able to provision OpenStack resources, it must first be linked to a project. To do that,
        **POST** a connection between project and a service to */api/openstack-service-project-link/*
        as stuff user or customer owner.

        Example of a request:

        .. code-block:: http

            POST /api/openstack-service-project-link/ HTTP/1.1
            Content-Type: application/json
            Accept: application/json
            Authorization: Token c84d653b9ec92c6cbac41c706593e66f567a7fa4
            Host: example.com

            {
                "project": "http://example.com/api/projects/e5f973af2eb14d2d8c38d62bcbaccb33/",
                "service": "http://example.com/api/openstack/b0e8a4cbd47c4f9ca01642b7ec033db4/"
            }

        To remove a link, issue DELETE to URL of the corresponding connection as stuff user or customer owner.
        """
        return super(OpenStackServiceProjectLinkViewSet, self).list(request, *args, **kwargs)


class FlavorViewSet(structure_views.BaseServicePropertyViewSet):
    """
    VM instance flavor is a pre-defined set of virtual hardware parameters that the instance will use:
    CPU, memory, disk size etc. VM instance flavor is not to be confused with VM template -- flavor is a set of virtual
    hardware parameters whereas template is a definition of a system to be installed on this instance.
    """
    queryset = models.Flavor.objects.all().order_by('settings', 'cores', 'ram', 'disk')
    serializer_class = serializers.FlavorSerializer
    lookup_field = 'uuid'
    filter_class = filters.FlavorFilter


class ImageViewSet(structure_views.BaseServicePropertyViewSet):
    queryset = models.Image.objects.all()
    serializer_class = serializers.ImageSerializer
    lookup_field = 'uuid'
    filter_class = filters.ImageFilter


class SecurityGroupViewSet(six.with_metaclass(structure_views.ResourceViewMetaclass, structure_views.ResourceViewSet)):
    queryset = models.SecurityGroup.objects.all()
    serializer_class = serializers.SecurityGroupSerializer
    filter_class = filters.SecurityGroupFilter
    disabled_actions = ['create', 'pull']  # pull operation should be implemented in WAL-323

    update_executor = executors.SecurityGroupUpdateExecutor
    delete_executor = executors.SecurityGroupDeleteExecutor

    @decorators.detail_route(methods=['POST'])
    def set_rules(self, request, uuid=None):
        """ WARNING! Auto-generated HTML form is wrong for this endpoint. List should be defined as input.

            Example:
            [
                {
                    "protocol": "tcp",
                    "from_port": 1,
                    "to_port": 10,
                    "cidr": "10.1.1.0/24"
                }
            ]
        """
        # XXX: DRF does not support forms generation for list serializers.
        #      Thats why we use different serializer in view.
        serializer = serializers.SecurityGroupRuleListUpdateSerializer(
            data=request.data, context=self.get_serializer_context())
        serializer.is_valid(raise_exception=True)
        serializer.save()

        executors.PushSecurityGroupRulesExecutor().execute(self.get_object())
        return response.Response(
            {'status': 'Rules update was successfully scheduled.'}, status=status.HTTP_202_ACCEPTED)

    set_rules_validators = [core_validators.StateValidator(models.Tenant.States.OK)]
    set_rules_serializer_class = serializers.SecurityGroupRuleUpdateSerializer


class IpMappingViewSet(viewsets.ModelViewSet):
    queryset = models.IpMapping.objects.all()
    serializer_class = serializers.IpMappingSerializer
    lookup_field = 'uuid'
    filter_backends = (structure_filters.GenericRoleFilter, DjangoFilterBackend)
    permission_classes = (permissions.IsAuthenticated, permissions.DjangoObjectPermissions)
    filter_class = filters.IpMappingFilter


class FloatingIPViewSet(six.with_metaclass(structure_views.ResourceViewMetaclass,
                                           structure_views.ResourceViewSet)):
    queryset = models.FloatingIP.objects.all()
    serializer_class = serializers.FloatingIPSerializer
    filter_class = filters.FloatingIPFilter
    disabled_actions = ['update', 'partial_update', 'create']
    delete_executor = executors.FloatingIPDeleteExecutor
    pull_executor = executors.FloatingIPPullExecutor

    def list(self, request, *args, **kwargs):
        """
        To get a list of all available floating IPs, issue **GET** against */api/floating-ips/*.
        Floating IPs are read only. Each floating IP has fields: 'address', 'status'.

        Status *DOWN* means that floating IP is not linked to a VM, status *ACTIVE* means that it is in use.
        """

        return super(FloatingIPViewSet, self).list(request, *args, **kwargs)


class TenantViewSet(six.with_metaclass(structure_views.ResourceViewMetaclass, structure_views.ResourceViewSet)):
    queryset = models.Tenant.objects.all()
    serializer_class = serializers.TenantSerializer
    filter_class = structure_filters.BaseResourceFilter

    create_executor = executors.TenantCreateExecutor
    update_executor = executors.TenantUpdateExecutor
    delete_executor = executors.TenantDeleteExecutor
    pull_executor = executors.TenantPullExecutor

    @decorators.detail_route(methods=['post'])
    def create_service(self, request, uuid=None):
        """Create non-admin service with credentials from the tenant"""

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        name = serializer.validated_data['name']

        tenant = self.get_object()

        service = tenant.create_service(name)
        structure_executors.ServiceSettingsCreateExecutor.execute(service.settings, async=self.async_executor)

        serializer = serializers.ServiceSerializer(service, context={'request': request})
        return response.Response(serializer.data, status=status.HTTP_201_CREATED)

    create_service_permissions = [structure_permissions.is_owner]
    create_service_validators = [core_validators.StateValidator(models.Tenant.States.OK)]
    create_service_serializer_class = serializers.ServiceNameSerializer

    @decorators.detail_route(methods=['post'])
    def set_quotas(self, request, uuid=None):
        """
        A quota can be set for a particular tenant. Only staff users can do that.
        In order to set quota submit **POST** request to */api/openstack-tenants/<uuid>/set_quotas/*.
        The quota values are propagated to the backend.

        The following quotas are supported. All values are expected to be integers:

        - instances - maximal number of created instances.
        - ram - maximal size of ram for allocation. In MiB_.
        - storage - maximal size of storage for allocation. In MiB_.
        - vcpu - maximal number of virtual cores for allocation.
        - security_group_count - maximal number of created security groups.
        - security_group_rule_count - maximal number of created security groups rules.
        - volumes - maximal number of created volumes.
        - snapshots - maximal number of created snapshots.

        It is possible to update quotas by one or by submitting all the fields in one request.
        NodeConductor will attempt to update the provided quotas. Please note, that if provided quotas are
        conflicting with the backend (e.g. requested number of instances is below of the already existing ones),
        some quotas might not be applied.

        .. _MiB: http://en.wikipedia.org/wiki/Mebibyte
        .. _settings: http://nodeconductor.readthedocs.org/en/stable/guide/intro.html#id1

        Example of a valid request (token is user specific):

        .. code-block:: http

            POST /api/openstack-tenants/c84d653b9ec92c6cbac41c706593e66f567a7fa4/set_quotas/ HTTP/1.1
            Content-Type: application/json
            Accept: application/json
            Host: example.com

            {
                "instances": 30,
                "ram": 100000,
                "storage": 1000000,
                "vcpu": 30,
                "security_group_count": 100,
                "security_group_rule_count": 100,
                "volumes": 10,
                "snapshots": 20
            }

        Response code of a successful request is **202 ACCEPTED**.
        In case tenant is in a non-stable status, the response would be **409 CONFLICT**.
        In this case REST client is advised to repeat the request after some time.
        On successful completion the task will synchronize quotas with the backend.
        """
        tenant = self.get_object()

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        quotas = dict(serializer.validated_data)
        for quota_name, limit in quotas.items():
            tenant.set_quota_limit(quota_name, limit)
        executors.TenantPushQuotasExecutor.execute(tenant, quotas=quotas)

        return response.Response(
            {'detail': 'Quota update has been scheduled'}, status=status.HTTP_202_ACCEPTED)

    set_quotas_permissions = [structure_permissions.is_staff]
    set_quotas_validators = [core_validators.StateValidator(models.Tenant.States.OK)]
    set_quotas_serializer_class = serializers.TenantQuotaSerializer

    @decorators.detail_route(methods=['post'])
    def create_network(self, request, uuid=None):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        network = serializer.save()

        executors.NetworkCreateExecutor().execute(network)
        return response.Response(serializer.data, status=status.HTTP_201_CREATED)

    create_network_validators = [core_validators.StateValidator(models.Tenant.States.OK)]
    create_network_serializer_class = serializers.NetworkSerializer

    def external_network_is_defined(tenant):
        if not tenant.external_network_id:
            raise core_exceptions.IncorrectStateException(
                'Cannot create floating IP if tenant external network is not defined.')

    @decorators.detail_route(methods=['post'])
    def create_floating_ip(self, request, uuid=None):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        floating_ip = serializer.save()

        executors.FloatingIPCreateExecutor.execute(floating_ip)
        return response.Response(serializer.data, status=status.HTTP_201_CREATED)

    create_floating_ip_validators = [core_validators.StateValidator(models.Tenant.States.OK),
                                     external_network_is_defined]
    create_floating_ip_serializer_class = serializers.FloatingIPSerializer

    @decorators.detail_route(methods=['post'])
    def pull_floating_ips(self, request, uuid=None):
        tenant = self.get_object()

        executors.TenantPullFloatingIPsExecutor.execute(tenant)
        return response.Response(status=status.HTTP_202_ACCEPTED)

    pull_floating_ips_validators = [core_validators.StateValidator(models.Tenant.States.OK)]
    pull_floating_ips_serializer_class = rf_serializers.Serializer

    @decorators.detail_route(methods=['post'])
    def create_security_group(self, request, uuid=None):
        """
        Example of a request:

        .. code-block:: http

            {
                "name": "Security group name",
                "description": "description",
                "rules": [
                    {
                        "protocol": "tcp",
                        "from_port": 1,
                        "to_port": 10,
                        "cidr": "10.1.1.0/24"
                    },
                    {
                        "protocol": "udp",
                        "from_port": 10,
                        "to_port": 8000,
                        "cidr": "10.1.1.0/24"
                    }
                ]
            }
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        security_group = serializer.save()

        executors.SecurityGroupCreateExecutor().execute(security_group)
        return response.Response(serializer.data, status=status.HTTP_201_CREATED)

    create_security_group_validators = [core_validators.StateValidator(models.Tenant.States.OK)]
    create_security_group_serializer_class = serializers.SecurityGroupSerializer

    @decorators.detail_route(methods=['post'])
    def pull_security_groups(self, request, uuid=None):
        executors.TenantPullSecurityGroupsExecutor.execute(self.get_object())
        return response.Response(
            {'status': 'Security groups pull has been scheduled.'}, status=status.HTTP_202_ACCEPTED)

    pull_security_groups_validators = [core_validators.StateValidator(models.Tenant.States.OK)]

    @decorators.detail_route(methods=['post'])
    def change_password(self, request, uuid=None):
        serializer = self.get_serializer(instance=self.get_object(), data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        executors.TenantChangeUserPasswordExecutor.execute(self.get_object())
        return response.Response({'status': 'Password update has been scheduled.'}, status=status.HTTP_202_ACCEPTED)

    change_password_serializer_class = serializers.TenantChangePasswordSerializer
    change_password_validators = [core_validators.StateValidator(models.Tenant.States.OK)]

    def pull_quotas(self, request, uuid=None):
        executors.TenantPullQuotasExecutor.execute(self.get_object())
        return response.Response({'status': 'Quotas pull has been scheduled.'}, status=status.HTTP_202_ACCEPTED)

    pull_quotas_validators = [core_validators.StateValidator(models.Tenant.States.OK)]


class NetworkViewSet(six.with_metaclass(structure_views.ResourceViewMetaclass, structure_views.ResourceViewSet)):
    queryset = models.Network.objects.all()
    serializer_class = serializers.NetworkSerializer
    filter_class = filters.NetworkFilter

    disabled_actions = ['create']
    update_executor = executors.NetworkUpdateExecutor
    delete_executor = executors.NetworkDeleteExecutor
    pull_executor = executors.NetworkPullExecutor

    @decorators.detail_route(methods=['post'])
    def create_subnet(self, request, uuid=None):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        subnet = serializer.save()

        executors.SubNetCreateExecutor.execute(subnet)
        return response.Response(serializer.data, status=status.HTTP_201_CREATED)

    create_subnet_validators = [core_validators.StateValidator(models.Network.States.OK)]
    create_subnet_serializer_class = serializers.SubNetSerializer


class SubNetViewSet(six.with_metaclass(structure_views.ResourceViewMetaclass, structure_views.ResourceViewSet)):
    queryset = models.SubNet.objects.all()
    serializer_class = serializers.SubNetSerializer
    filter_class = filters.SubNetFilter

    disabled_actions = ['create']
    update_executor = executors.SubNetUpdateExecutor
    delete_executor = executors.SubNetDeleteExecutor
    pull_executor = executors.SubNetPullExecutor
