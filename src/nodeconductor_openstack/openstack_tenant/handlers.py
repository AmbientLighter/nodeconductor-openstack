from __future__ import unicode_literals

from django.core import exceptions as django_exceptions

from nodeconductor.core.models import StateMixin
from nodeconductor.structure import models as structure_models

from ..openstack import models as openstack_models
from . import log, models


def _log_scheduled_action(resource, action, action_details):
    class_name = resource.__class__.__name__.lower()
    message = _get_action_message(action, action_details)
    log.event_logger.openstack_resource_action.info(
        'Operation "%s" has been scheduled for %s "%s"' % (message, class_name, resource.name),
        event_type=_get_action_event_type(action, 'scheduled'),
        event_context={'resource': resource, 'action_details': action_details},
    )


def _log_succeeded_action(resource, action, action_details):
    class_name = resource.__class__.__name__.lower()
    message = _get_action_message(action, action_details)
    log.event_logger.openstack_resource_action.info(
        'Successfully executed "%s" operation for %s "%s"' % (message, class_name, resource.name),
        event_type=_get_action_event_type(action, 'succeeded'),
        event_context={'resource': resource, 'action_details': action_details},
    )


def _log_failed_action(resource, action, action_details):
    class_name = resource.__class__.__name__.lower()
    message = _get_action_message(action, action_details)
    log.event_logger.openstack_resource_action.warning(
        'Failed to execute "%s" operation for %s "%s"' % (message, class_name, resource.name),
        event_type=_get_action_event_type(action, 'failed'),
        event_context={'resource': resource, 'action_details': action_details},
    )


def _get_action_message(action, action_details):
    return action_details.pop('message', action)


def _get_action_event_type(action, event_state):
    return 'resource_%s_%s' % (action.replace(' ', '_').lower(), event_state)


def log_action(sender, instance, created=False, **kwargs):
    """ Log any resource action.

        Example of logged volume extend action:
        {
            'event_type': 'volume_extend_succeeded',
            'message': 'Successfully executed "Extend volume from 1024 MB to 2048 MB" operation for volume "pavel-test"',
            'action_details': {'old_size': 1024, 'new_size': 2048}
        }
    """
    resource = instance
    if created or not resource.tracker.has_changed('action'):
        return
    if resource.state == StateMixin.States.UPDATE_SCHEDULED:
        _log_scheduled_action(resource, resource.action, resource.action_details)
    if resource.state == StateMixin.States.OK:
        _log_succeeded_action(
            resource, resource.tracker.previous('action'), resource.tracker.previous('action_details'))
    elif resource.state == StateMixin.States.ERRED:
        _log_failed_action(
            resource, resource.tracker.previous('action'), resource.tracker.previous('action_details'))


def log_snapshot_schedule_creation(sender, instance, created=False, **kwargs):
    if not created:
        return

    snapshot_schedule = instance
    log.event_logger.openstack_snapshot_schedule.info(
        'Snapshot schedule "%s" has been created' % snapshot_schedule.name,
        event_type='resource_snapshot_schedule_created',
        event_context={'resource': snapshot_schedule.source_volume, 'snapshot_schedule': snapshot_schedule},
    )


def log_snapshot_schedule_action(sender, instance, created=False, **kwargs):
    snapshot_schedule = instance
    if created or not snapshot_schedule.tracker.has_changed('is_active'):
        return

    context = {'resource': snapshot_schedule.source_volume, 'snapshot_schedule': snapshot_schedule}
    if snapshot_schedule.is_active:
        log.event_logger.openstack_snapshot_schedule.info(
            'Snapshot schedule "%s" has been activated' % snapshot_schedule.name,
            event_type='resource_snapshot_schedule_activated',
            event_context=context,
        )
    else:
        if snapshot_schedule.error_message:
            message = 'Snapshot schedule "%s" has been deactivated because of error' % snapshot_schedule.name
        else:
            message = 'Snapshot schedule "%s" has been deactivated' % snapshot_schedule.name
        log.event_logger.openstack_snapshot_schedule.info(
            message,
            event_type='resource_snapshot_schedule_deactivated',
            event_context=context,
        )


def log_snapshot_schedule_deletion(sender, instance, **kwargs):
    snapshot_schedule = instance
    log.event_logger.openstack_snapshot_schedule.info(
        'Snapshot schedule "%s" has been deleted' % snapshot_schedule.name,
        event_type='resource_snapshot_schedule_deleted',
        event_context={'resource': snapshot_schedule.source_volume, 'snapshot_schedule': snapshot_schedule},
    )


def log_backup_schedule_creation(sender, instance, created=False, **kwargs):
    if not created:
        return

    backup_schedule = instance
    log.event_logger.openstack_backup_schedule.info(
        'Backup schedule "%s" has been created' % backup_schedule.name,
        event_type='resource_backup_schedule_created',
        event_context={'resource': backup_schedule.instance, 'backup_schedule': backup_schedule},
    )


def log_backup_schedule_action(sender, instance, created=False, **kwargs):
    backup_schedule = instance
    if created or not backup_schedule.tracker.has_changed('is_active'):
        return

    context = {'resource': backup_schedule.instance, 'backup_schedule': backup_schedule}
    if backup_schedule.is_active:
        log.event_logger.openstack_backup_schedule.info(
            'Backup schedule "%s" has been activated' % backup_schedule.name,
            event_type='resource_backup_schedule_activated',
            event_context=context,
        )
    else:
        if backup_schedule.error_message:
            message = 'Backup schedule "%s" has been deactivated because of error' % backup_schedule.name
        else:
            message = 'Backup schedule "%s" has been deactivated' % backup_schedule.name
        log.event_logger.openstack_backup_schedule.info(
            message,
            event_type='resource_backup_schedule_deactivated',
            event_context=context,
        )


def log_backup_schedule_deletion(sender, instance, **kwargs):
    backup_schedule = instance
    log.event_logger.openstack_backup_schedule.info(
        'Backup schedule "%s" has been deleted' % backup_schedule.name,
        event_type='resource_backup_schedule_deleted',
        event_context={'resource': backup_schedule.instance, 'backup_schedule': backup_schedule},
    )


def update_service_settings_password(sender, instance, created=False, **kwargs):
    """
    Updates service settings password on tenant user_password change.
    It is possible to change a user password in tenant,
    as service settings copies tenant user password on creation it has to be update on change.
    """
    if created:
        return

    tenant = instance
    if tenant.tracker.has_changed('user_password'):
        service_settings = structure_models.ServiceSettings.objects.filter(scope=tenant).first()
        if service_settings:
            service_settings.password = tenant.user_password
            service_settings.save()


class BaseSynchronizationHandler(object):
    """
    This class provides signal handlers for synchronization of OpenStack properties
    when parent OpenStack resource are created, updated or deleted.
    Security groups, floating IPs, networks and subnets are implemented as
    resources in openstack application. However they are implemented as service properties
    in the openstack_tenant application.
    """
    property_model = None
    resource_model = None
    fields = []

    def get_tenant(self, resource):
        return resource.tenant

    def get_service_settings(self, resource):
        try:
            return structure_models.ServiceSettings.objects.get(scope=self.get_tenant(resource))
        except (django_exceptions.ObjectDoesNotExist, django_exceptions.MultipleObjectsReturned):
            return

    def get_service_property(self, resource, settings):
        try:
            return self.property_model.objects.get(settings=settings, backend_id=resource.backend_id)
        except (django_exceptions.ObjectDoesNotExist, django_exceptions.MultipleObjectsReturned):
            return

    def map_resource_to_dict(self, resource):
        return {field: getattr(resource, field) for field in self.fields}

    def create_service_property(self, resource, settings):
        params = self.map_resource_to_dict(resource)
        return self.property_model.objects.create(
            settings=settings,
            backend_id=resource.backend_id,
            name=resource.name,
            **params
        )

    def update_service_property(self, resource, settings):
        service_property = self.get_service_property(resource, settings)
        if not service_property:
            return
        params = self.map_resource_to_dict(resource)
        for key, value in params.items():
            setattr(service_property, key, value)
        service_property.name = resource.name
        service_property.save()
        return service_property

    def create_handler(self, sender, instance, name, source, target, **kwargs):
        """
        Creates service property on resource transition from 'CREATING' state to 'OK'.
        """
        if source == StateMixin.States.CREATING and target == StateMixin.States.OK:
            settings = self.get_service_settings(instance)
            if settings:
                self.create_service_property(instance, settings)

    def update_handler(self, sender, instance, name, source, target, **kwargs):
        """
        Updates service property on resource transition from 'UPDATING' state to 'OK'.
        """
        if source == StateMixin.States.UPDATING and target == StateMixin.States.OK:
            settings = self.get_service_settings(instance)
            if settings:
                self.update_service_property(instance, settings)

    def delete_handler(self, sender, instance, **kwargs):
        """
        Deletes service property on resource deletion
        """
        settings = self.get_service_settings(instance)
        if not settings:
            return
        service_property = self.get_service_property(instance, settings)
        if not service_property:
            return
        service_property.delete()


class FloatingIPHandler(BaseSynchronizationHandler):
    property_model = models.FloatingIP
    resource_model = openstack_models.FloatingIP
    fields = ('address', 'backend_network_id', 'runtime_state')


class SecurityGroupHandler(BaseSynchronizationHandler):
    property_model = models.SecurityGroup
    resource_model = openstack_models.SecurityGroup
    fields = ('description',)

    def map_rules(self, security_group, openstack_security_group):
        return [models.SecurityGroupRule(
            protocol=rule.protocol,
            from_port=rule.from_port,
            to_port=rule.to_port,
            cidr=rule.cidr,
            backend_id=rule.backend_id,
            security_group=security_group,
        ) for rule in openstack_security_group.rules.iterator()]

    def create_service_property(self, resource, settings):
        service_property = super(SecurityGroupHandler, self).create_service_property(resource, settings)
        if resource.rules.count() > 0:
            group_rules = self.map_rules(service_property, resource)
            service_property.rules.bulk_create(group_rules)
        return service_property

    def update_service_property(self, resource, settings):
        service_property = super(SecurityGroupHandler, self).update_service_property(resource, settings)
        service_property.rules.all().delete()
        group_rules = self.map_rules(service_property, resource)
        service_property.rules.bulk_create(group_rules)
        return service_property


class NetworkHandler(BaseSynchronizationHandler):
    property_model = models.Network
    resource_model = openstack_models.Network
    fields = ('is_external', 'segmentation_id', 'type')


class SubNetHandler(BaseSynchronizationHandler):
    property_model = models.SubNet
    resource_model = openstack_models.SubNet
    fields = ('allocation_pools', 'cidr', 'dns_nameservers', 'enable_dhcp', 'ip_version')

    def get_tenant(self, resource):
        return resource.network.tenant

    def map_resource_to_dict(self, resource):
        params = super(SubNetHandler, self).map_resource_to_dict(resource)
        params['network'] = models.Network.objects.get(backend_id=resource.network.backend_id)
        return params


resource_handlers = (
    FloatingIPHandler(),
    SecurityGroupHandler(),
    NetworkHandler(),
    SubNetHandler(),
)
