import mock
from rest_framework import status, test

from . import factories, fixtures


class BaseSubNetTest(test.APITransactionTestCase):

    def setUp(self):
        self.fixture = fixtures.OpenStackFixture()


class SubNetCreateActionTest(BaseSubNetTest):

    def setUp(self):
        super(SubNetCreateActionTest, self).setUp()
        self.client.force_authenticate(user=self.fixture.user)

    def test_subnet_create_action_is_not_allowed(self):
        url = factories.SubNetFactory.get_list_url()
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


@mock.patch('nodeconductor_openstack.openstack.executors.SubNetDeleteExecutor.execute')
class SubNetDeleteActionTest(BaseSubNetTest):

    def setUp(self):
        super(SubNetDeleteActionTest, self).setUp()
        self.client.force_authenticate(user=self.fixture.admin)
        self.url = factories.SubNetFactory.get_url(self.fixture.subnet)

    def test_subnet_delete_action_triggers_create_executor(self, executor_action_mock):
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        executor_action_mock.assert_called_once()

    def test_subnet_delete_action_decreases_set_quota_limit(self, executor_action_mock):
        self.fixture.subnet.increase_backend_quotas_usage()
        self.assertEqual(self.fixture.subnet.network.tenant.quotas.get(name='subnet_count').usage, 1)

        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(self.fixture.tenant.quotas.get(name='subnet_count').usage, 0)
        executor_action_mock.assert_called_once()


class SubNetUpdateActionTest(BaseSubNetTest):

    def setUp(self):
        super(SubNetUpdateActionTest, self).setUp()
        self.client.force_authenticate(user=self.fixture.admin)
        self.url = factories.SubNetFactory.get_url(self.fixture.subnet)
        self.request_data = {
            'name': 'test_name'
        }

    @mock.patch('nodeconductor_openstack.openstack.executors.SubNetUpdateExecutor.execute')
    def test_subnet_update_action_triggers_update_executor(self, executor_action_mock):
        response = self.client.put(self.url, self.request_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        executor_action_mock.assert_called_once()
