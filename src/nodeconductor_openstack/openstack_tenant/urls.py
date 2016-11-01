from . import views


def register_in(router):
    router.register(r'openstacktenant', views.OpenStackServiceViewSet, base_name='openstacktenant')
    router.register(r'openstacktenant-service-project-link', views.OpenStackServiceProjectLinkViewSet,
                    base_name='openstacktenant-spl')
    router.register(r'openstacktenant-images', views.ImageViewSet, base_name='openstacktenant-image')
    router.register(r'openstacktenant-flavors', views.FlavorViewSet, base_name='openstacktenant-flavor')
    router.register(r'openstacktenant-floating-ips', views.FloatingIPViewSet, base_name='openstacktenant-fip')
    router.register(r'openstacktenant-security-groups', views.SecurityGroupViewSet, base_name='openstacktenant-sgp')
    router.register(r'openstacktenant-volumes', views.VolumeViewSet, base_name='openstacktenant-volume')
    router.register(r'openstacktenant-snapshots', views.SnapshotViewSet, base_name='openstacktenant-snapshot')