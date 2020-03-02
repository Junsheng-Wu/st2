# Licensed to the StackStorm, Inc ('StackStorm') under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import httplib
import json

import mock
import six
from oslo_config import cfg

from st2common.transport.publishers import PoolPublisher
from st2common.rbac.types import PermissionType
from st2common.rbac.types import ResourceType
from st2common.persistence.auth import User
from st2common.persistence.rbac import Role
from st2common.persistence.rbac import UserRoleAssignment
from st2common.persistence.rbac import PermissionGrant
from st2common.models.db.auth import UserDB
from st2common.models.db.rbac import RoleDB
from st2common.models.db.rbac import UserRoleAssignmentDB
from st2common.models.db.rbac import PermissionGrantDB
from st2tests.fixturesloader import FixturesLoader
from tests.base import APIControllerWithRBACTestCase

http_client = six.moves.http_client

__all__ = [
    'RuleControllerRBACTestCase'
]

FIXTURES_PACK = 'generic'
TEST_FIXTURES = {
    'runners': ['testrunner1.yaml'],
    'actions': ['action1.yaml', 'local.yaml'],
    'triggers': ['trigger1.yaml'],
    'triggertypes': ['triggertype1.yaml']
}


class RuleControllerRBACTestCase(APIControllerWithRBACTestCase):
    fixtures_loader = FixturesLoader()

    def setUp(self):
        super(RuleControllerRBACTestCase, self).setUp()
        self.fixtures_loader.save_fixtures_to_db(fixtures_pack=FIXTURES_PACK,
                                                 fixtures_dict=TEST_FIXTURES)

        file_name = 'rule_with_webhook_trigger.yaml'
        RuleControllerRBACTestCase.RULE_1 = self.fixtures_loader.load_fixtures(
            fixtures_pack=FIXTURES_PACK,
            fixtures_dict={'rules': [file_name]})['rules'][file_name]

        file_name = 'rule_example_pack.yaml'
        RuleControllerRBACTestCase.RULE_2 = self.fixtures_loader.load_fixtures(
            fixtures_pack=FIXTURES_PACK,
            fixtures_dict={'rules': [file_name]})['rules'][file_name]

        file_name = 'rule_action_doesnt_exist.yaml'
        RuleControllerRBACTestCase.RULE_3 = self.fixtures_loader.load_fixtures(
            fixtures_pack=FIXTURES_PACK,
            fixtures_dict={'rules': [file_name]})['rules'][file_name]

        # Insert mock users, roles and assignments

        # Users
        user_1_db = UserDB(name='rule_create')
        user_1_db = User.add_or_update(user_1_db)
        self.users['rule_create'] = user_1_db

        user_2_db = UserDB(name='rule_create_webhook_create')
        user_2_db = User.add_or_update(user_2_db)
        self.users['rule_create_webhook_create'] = user_2_db

        user_3_db = UserDB(name='rule_create_webhook_create_core_local_execute')
        user_3_db = User.add_or_update(user_3_db)
        self.users['rule_create_webhook_create_core_local_execute'] = user_3_db

        user_4_db = UserDB(name='rule_create_1')
        user_4_db = User.add_or_update(user_4_db)
        self.users['rule_create_1'] = user_4_db

        # Roles
        # rule_create grant on parent pack
        grant_db = PermissionGrantDB(resource_uid='pack:examples',
                                     resource_type=ResourceType.PACK,
                                     permission_types=[PermissionType.RULE_CREATE])
        grant_db = PermissionGrant.add_or_update(grant_db)
        permission_grants = [str(grant_db.id)]
        role_1_db = RoleDB(name='rule_create', permission_grants=permission_grants)
        role_1_db = Role.add_or_update(role_1_db)
        self.roles['rule_create'] = role_1_db

        # rule_create grant on parent pack, webhook_create on webhook "sample"
        grant_1_db = PermissionGrantDB(resource_uid='pack:examples',
                                     resource_type=ResourceType.PACK,
                                     permission_types=[PermissionType.RULE_CREATE])
        grant_1_db = PermissionGrant.add_or_update(grant_1_db)
        grant_2_db = PermissionGrantDB(resource_uid='webhook:sample',
                                     resource_type=ResourceType.WEBHOOK,
                                     permission_types=[PermissionType.WEBHOOK_CREATE])
        grant_2_db = PermissionGrant.add_or_update(grant_2_db)
        permission_grants = [str(grant_1_db.id), str(grant_2_db.id)]
        role_2_db = RoleDB(name='rule_create_webhook_create', permission_grants=permission_grants)
        role_2_db = Role.add_or_update(role_2_db)
        self.roles['rule_create_webhook_create'] = role_2_db

        # rule_create grant on parent pack, webhook_create on webhook "sample", action_execute on
        # core.local
        grant_1_db = PermissionGrantDB(resource_uid='pack:examples',
                                     resource_type=ResourceType.PACK,
                                     permission_types=[PermissionType.RULE_CREATE])
        grant_1_db = PermissionGrant.add_or_update(grant_1_db)
        grant_2_db = PermissionGrantDB(resource_uid='webhook:sample',
                                     resource_type=ResourceType.WEBHOOK,
                                     permission_types=[PermissionType.WEBHOOK_CREATE])
        grant_2_db = PermissionGrant.add_or_update(grant_2_db)
        grant_3_db = PermissionGrantDB(resource_uid='action:core:local',
                                     resource_type=ResourceType.ACTION,
                                     permission_types=[PermissionType.ACTION_EXECUTE])
        grant_3_db = PermissionGrant.add_or_update(grant_3_db)
        permission_grants = [str(grant_1_db.id), str(grant_2_db.id), str(grant_3_db.id)]

        role_3_db = RoleDB(name='rule_create_webhook_create_core_local_execute',
                           permission_grants=permission_grants)
        role_3_db = Role.add_or_update(role_3_db)
        self.roles['rule_create_webhook_create_core_local_execute'] = role_3_db

        # rule_create grant on parent pack, webhook_create on webhook "sample", action_execute on
        # examples and wolfpack
        grant_1_db = PermissionGrantDB(resource_uid='pack:examples',
                                     resource_type=ResourceType.PACK,
                                     permission_types=[PermissionType.RULE_CREATE])
        grant_1_db = PermissionGrant.add_or_update(grant_1_db)
        grant_2_db = PermissionGrantDB(resource_uid='webhook:sample',
                                     resource_type=ResourceType.WEBHOOK,
                                     permission_types=[PermissionType.WEBHOOK_CREATE])
        grant_2_db = PermissionGrant.add_or_update(grant_2_db)
        grant_3_db = PermissionGrantDB(resource_uid='pack:wolfpack',
                                     resource_type=ResourceType.PACK,
                                     permission_types=[PermissionType.ACTION_ALL])
        grant_3_db = PermissionGrant.add_or_update(grant_3_db)
        grant_4_db = PermissionGrantDB(resource_uid=None,
                                       resource_type=ResourceType.RULE,
                                       permission_types=[PermissionType.RULE_LIST])
        grant_4_db = PermissionGrant.add_or_update(grant_4_db)
        grant_5_db = PermissionGrantDB(resource_uid='pack:examples',
                                     resource_type=ResourceType.PACK,
                                     permission_types=[PermissionType.ACTION_ALL])
        grant_5_db = PermissionGrant.add_or_update(grant_5_db)
        permission_grants = [str(grant_1_db.id), str(grant_2_db.id), str(grant_3_db.id),
                             str(grant_4_db.id), str(grant_5_db.id)]

        role_4_db = RoleDB(name='rule_create_webhook_create_action_execute',
                           permission_grants=permission_grants)
        role_4_db = Role.add_or_update(role_4_db)
        self.roles['rule_create_webhook_create_action_execute'] = role_4_db

        # Role assignments
        user_db = self.users['rule_create']
        role_assignment_db = UserRoleAssignmentDB(
            user=user_db.name,
            role=self.roles['rule_create'].name,
            source='assignments/%s.yaml' % user_db.name)
        UserRoleAssignment.add_or_update(role_assignment_db)

        user_db = self.users['rule_create_webhook_create']
        role_assignment_db = UserRoleAssignmentDB(
            user=user_db.name,
            role=self.roles['rule_create_webhook_create'].name,
            source='assignments/%s.yaml' % user_db.name)
        UserRoleAssignment.add_or_update(role_assignment_db)

        user_db = self.users['rule_create_webhook_create_core_local_execute']
        role_assignment_db = UserRoleAssignmentDB(
            user=user_db.name,
            role=self.roles['rule_create_webhook_create_core_local_execute'].name,
            source='assignments/%s.yaml' % user_db.name)
        UserRoleAssignment.add_or_update(role_assignment_db)

        user_db = self.users['rule_create_1']
        role_assignment_db = UserRoleAssignmentDB(
            user=user_db.name,
            role=self.roles['rule_create_webhook_create_action_execute'].name,
            source='assignments/%s.yaml' % user_db.name)
        UserRoleAssignment.add_or_update(role_assignment_db)

    def test_post_webhook_trigger_no_trigger_and_action_permission(self):
        # Test a scenario when user selects a webhook trigger, but only has "rule_create"
        # permission
        user_db = self.users['rule_create']
        self.use_user(user_db)

        resp = self.__do_post(RuleControllerRBACTestCase.RULE_1)
        expected_msg = ('User "rule_create" doesn\'t have required permission (webhook_create) '
                        'to use trigger core.st2.webhook')
        self.assertEqual(resp.status_code, httplib.FORBIDDEN)
        self.assertEqual(resp.json['faultstring'], expected_msg)

    def test_post_user_has_no_permission_on_action_which_doesnt_exist_in_db(self):
        # User has rule_create, but no action_execute on the action which doesn't exist in the db
        user_db = self.users['rule_create_webhook_create']
        self.use_user(user_db)

        resp = self.__do_post(RuleControllerRBACTestCase.RULE_3)
        expected_msg = ('User "rule_create_webhook_create" doesn\'t have required (action_execute)'
                        ' permission to use action wolfpack.action-doesnt-exist-woo')
        self.assertEqual(resp.status_code, httplib.FORBIDDEN)
        self.assertEqual(resp.json['faultstring'], expected_msg)

    def test_post_no_webhook_trigger(self):
        # Test a scenario when user with only "rule_create" permission selects a non-webhook
        # trigger for which we don't perform any permission checking right now
        user_db = self.users['rule_create']
        self.use_user(user_db)

        resp = self.__do_post(RuleControllerRBACTestCase.RULE_2)
        expected_msg = ('User "rule_create" doesn\'t have required (action_execute) permission '
                        'to use action wolfpack.action-1')
        self.assertEqual(resp.status_code, httplib.FORBIDDEN)
        self.assertEqual(resp.json['faultstring'], expected_msg)

    def test_post_webhook_trigger_webhook_create_permission_no_action_permission(self):
        # Test a scenario where user with "rule_create" and "webhook_create" selects a webhook
        # trigger and core.local action
        user_db = self.users['rule_create_webhook_create']
        self.use_user(user_db)

        resp = self.__do_post(RuleControllerRBACTestCase.RULE_1)
        expected_msg = ('User "rule_create_webhook_create" doesn\'t have required '
                        '(action_execute) permission to use action core.local')
        self.assertEqual(resp.status_code, httplib.FORBIDDEN)
        self.assertEqual(resp.json['faultstring'], expected_msg)

    def test_post_action_webhook_trigger_webhook_create_and_action_execute_permission(self):
        # Test a scenario where user selects a webhook trigger and has all the required permissions
        user_db = self.users['rule_create_webhook_create_core_local_execute']
        self.use_user(user_db)

        resp = self.__do_post(RuleControllerRBACTestCase.RULE_1)
        self.assertEqual(resp.status_code, httplib.CREATED)

    def test_get_all_limit_minus_one(self):
        user_db = self.users['observer']
        self.use_user(user_db)

        resp = self.app.get('/v1/rules?limit=-1', expect_errors=True)
        self.assertEqual(resp.status_code, httplib.FORBIDDEN)

        user_db = self.users['admin']
        self.use_user(user_db)

        resp = self.app.get('/v1/rules?limit=-1')
        self.assertEqual(resp.status_code, httplib.OK)

    def test_get_respective_created_rules(self):
        cfg.CONF.set_override(name='permission_isolation', override=True,
                              group='rbac')

        user_db = self.users['admin']
        self.use_user(user_db)
        resp = self.__do_post(RuleControllerRBACTestCase.RULE_1)
        self.assertEqual(resp.status_code, http_client.CREATED)
        resp1 = self.app.get('/v1/rules')

        user_db = self.users['rule_create_1']
        self.use_user(user_db)
        resp = self.__do_post(RuleControllerRBACTestCase.RULE_2)
        self.assertEqual(resp.status_code, http_client.CREATED)
        resp = self.__do_post(RuleControllerRBACTestCase.RULE_3)
        self.assertEqual(resp.status_code, http_client.CREATED)
        resp2 = self.app.get('/v1/rules')

        self.assertEqual(len(json.loads(resp1.body)), 1)
        self.assertEqual(len(json.loads(resp2.body)), 2)

    @mock.patch.object(PoolPublisher, 'publish', mock.MagicMock())
    def __do_post(self, rule):
        return self.app.post_json('/v1/rules', rule, expect_errors=True)
