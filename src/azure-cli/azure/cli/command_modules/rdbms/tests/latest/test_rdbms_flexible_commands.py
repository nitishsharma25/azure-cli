# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------
import os
import time
import pytest
import uuid

from datetime import datetime
from time import sleep
from dateutil import parser
from dateutil.tz import tzutc
from azure.cli.testsdk.scenario_tests import AllowLargeResponse
from azure.cli.testsdk.base import execute
from azure.cli.testsdk.scenario_tests.const import ENV_LIVE_TEST
from azure.cli.testsdk import (
    JMESPathCheck,
    JMESPathCheckExists,
    JMESPathCheckNotExists,
    NoneCheck,
    ResourceGroupPreparer,
    KeyVaultPreparer,
    ScenarioTest,
    StringContainCheck,
    live_only)
from azure.cli.testsdk.preparers import (
    AbstractPreparer,
    SingleValueReplacer)
from azure.core.exceptions import HttpResponseError
from ..._client_factory import cf_mysql_flexible_private_dns_zone_suffix_operations, cf_postgres_flexible_private_dns_zone_suffix_operations
from ...flexible_server_virtual_network import prepare_private_network, prepare_private_dns_zone, DEFAULT_VNET_ADDRESS_PREFIX, DEFAULT_SUBNET_ADDRESS_PREFIX
from ...flexible_server_custom_postgres import DbContext as PostgresDbContext
from ...flexible_server_custom_mysql import DbContext as MysqlDbContext
from ...flexible_server_custom_mysql import _determine_iops
from ..._flexible_server_util import get_mysql_list_skus_info
from ..._util import retryable_method
from .conftest import mysql_location, mysql_paired_location, mysql_general_purpose_sku, mysql_memory_optimized_sku
# Constants
SERVER_NAME_PREFIX = 'azuredbclitest-'
SERVER_NAME_MAX_LENGTH = 20


class ServerPreparer(AbstractPreparer, SingleValueReplacer):

    def __init__(self, engine_type, location, engine_parameter_name='database_engine',
                 name_prefix=SERVER_NAME_PREFIX, parameter_name='server',
                 resource_group_parameter_name='resource_group'):
        super(ServerPreparer, self).__init__(name_prefix, SERVER_NAME_MAX_LENGTH)
        from azure.cli.core.mock import DummyCli
        self.cli_ctx = DummyCli()
        self.engine_type = engine_type
        self.engine_parameter_name = engine_parameter_name
        self.location = location
        self.parameter_name = parameter_name
        self.resource_group_parameter_name = resource_group_parameter_name

    def create_resource(self, name, **kwargs):
        group = self._get_resource_group(**kwargs)
        template = 'az {} flexible-server create -l {} -g {} -n {} --public-access none'
        execute(self.cli_ctx, template.format(self.engine_type,
                                              self.location,
                                              group, name))
        return {self.parameter_name: name,
                self.engine_parameter_name: self.engine_type}

    def remove_resource(self, name, **kwargs):
        group = self._get_resource_group(**kwargs)
        execute(self.cli_ctx, 'az {} flexible-server delete -g {} -n {} --yes'.format(self.engine_type, group, name))

    def _get_resource_group(self, **kwargs):
        return kwargs.get(self.resource_group_parameter_name)


class FlexibleServerMgmtScenarioTest(ScenarioTest):

    postgres_location = 'eastus'

    @pytest.mark.mysql_regression
    @AllowLargeResponse()
    @ResourceGroupPreparer(location=mysql_location)
    def test_mysql_flexible_server_iops_mgmt(self, resource_group):
        self._test_flexible_server_iops_mgmt('mysql', resource_group)

    @pytest.mark.mysql_regression
    @AllowLargeResponse()
    @ResourceGroupPreparer(location=mysql_location)
    def test_mysql_flexible_server_paid_iops_mgmt(self, resource_group):
        self._test_flexible_server_paid_iops_mgmt('mysql', resource_group)

    @AllowLargeResponse()
    @ResourceGroupPreparer(location=postgres_location)
    def test_postgres_flexible_server_mgmt(self, resource_group):
        self._test_flexible_server_mgmt('postgres', resource_group)

    @pytest.mark.mysql_regression
    @AllowLargeResponse()
    @ResourceGroupPreparer(location=mysql_location)
    def test_mysql_flexible_server_mgmt(self, resource_group):
        self._test_flexible_server_mgmt('mysql', resource_group)

    @pytest.mark.mysql_regression
    @AllowLargeResponse()
    @ResourceGroupPreparer(location=mysql_location)
    def test_mysql_flexible_server_import_create(self, resource_group):
        self._test_mysql_flexible_server_import_create('mysql', resource_group)

    # To run this test live, make sure that your role excludes the permission 'Microsoft.DBforMySQL/locations/checkNameAvailability/action'
    @pytest.mark.mysql_regression
    @ResourceGroupPreparer(location=mysql_location)
    def test_mysql_flexible_server_check_name_availability_fallback_mgmt(self, resource_group):
        self._test_flexible_server_check_name_availability_fallback_mgmt('mysql', resource_group)

    @AllowLargeResponse()
    @ResourceGroupPreparer(location=postgres_location)
    def test_postgres_flexible_server_restore_mgmt(self, resource_group):
        self._test_flexible_server_restore_mgmt('postgres', resource_group)

    @pytest.mark.mysql_regression
    @AllowLargeResponse()
    @ResourceGroupPreparer(location=mysql_location)
    def test_mysql_flexible_server_restore_mgmt(self, resource_group):
        self._test_flexible_server_restore_mgmt('mysql', resource_group)

    @AllowLargeResponse()
    @ResourceGroupPreparer(location=postgres_location)
    def test_postgres_flexible_server_georestore_mgmt(self, resource_group):
        self._test_flexible_server_georestore_mgmt('postgres', resource_group)

    @pytest.mark.mysql_regression
    @AllowLargeResponse()
    @ResourceGroupPreparer(location=mysql_location)
    def test_mysql_flexible_server_georestore_mgmt(self, resource_group):
        self._test_flexible_server_georestore_mgmt('mysql', resource_group)

    @pytest.mark.mysql_regression
    @AllowLargeResponse()
    @ResourceGroupPreparer(location=mysql_location)
    def test_mysql_flexible_server_georestore_update_mgmt(self, resource_group):
        self._test_flexible_server_georestore_update_mgmt('mysql', resource_group)

    @pytest.mark.mysql_regression
    @AllowLargeResponse()
    @ResourceGroupPreparer(location=mysql_location)
    def test_mysql_flexible_server_gtid_reset(self, resource_group):
        self._test_flexible_server_gtid_reset('mysql', resource_group)

    @pytest.mark.mysql_regression
    @AllowLargeResponse()
    @ResourceGroupPreparer(location=mysql_location)
    @KeyVaultPreparer(name_prefix='rdbmsvault', parameter_name='vault_name', location=mysql_paired_location, additional_params='--enable-purge-protection true --retention-days 90')
    @KeyVaultPreparer(name_prefix='rdbmsvault', parameter_name='backup_vault_name', location=mysql_location, additional_params='--enable-purge-protection true --retention-days 90')
    def test_mysql_flexible_server_byok_mgmt(self, resource_group, vault_name, backup_vault_name):
        self._test_flexible_server_byok_mgmt('mysql', resource_group, vault_name, backup_vault_name)

    @AllowLargeResponse()
    @ResourceGroupPreparer(location=postgres_location)
    @KeyVaultPreparer(name_prefix='rdbmsvault', parameter_name='vault_name', location=postgres_location, additional_params='--enable-purge-protection true --retention-days 90')
    def test_postgres_flexible_server_byok_mgmt(self, resource_group, vault_name):
        self._test_flexible_server_byok_mgmt('postgres', resource_group, vault_name)

    def _test_flexible_server_mgmt(self, database_engine, resource_group):

        if self.cli_ctx.local_context.is_on:
            self.cmd('config param-persist off')

        if database_engine == 'postgres':
            version = '12'
            storage_size = 128
            location = self.postgres_location
            sku_name = 'Standard_D2s_v3'
            memory_optimized_sku = 'Standard_E2ds_v4'
        elif database_engine == 'mysql':
            storage_size = 32
            version = '5.7'
            location = mysql_location
            sku_name = mysql_general_purpose_sku
            memory_optimized_sku = mysql_memory_optimized_sku
        tier = 'GeneralPurpose'
        backup_retention = 7
        database_name = 'testdb'
        server_name = self.create_random_name(SERVER_NAME_PREFIX, SERVER_NAME_MAX_LENGTH)
        ha_value = 'ZoneRedundant'

        self.cmd('{} flexible-server create -g {} -n {} --backup-retention {} --sku-name {} --tier {} \
                  --storage-size {} -u {} --version {} --tags keys=3 --database-name {} --high-availability {} \
                  --public-access None'.format(database_engine, resource_group, server_name, backup_retention,
                                               sku_name, tier, storage_size, 'dbadmin', version, database_name, ha_value))

        basic_info = self.cmd('{} flexible-server show -g {} -n {}'.format(database_engine, resource_group, server_name)).get_output_in_json()
        self.assertEqual(basic_info['name'], server_name)
        self.assertEqual(str(basic_info['location']).replace(' ', '').lower(), location)
        self.assertEqual(basic_info['resourceGroup'], resource_group)
        self.assertEqual(basic_info['sku']['name'], sku_name)
        self.assertEqual(basic_info['sku']['tier'], tier)
        self.assertEqual(basic_info['version'], version)
        self.assertEqual(basic_info['storage']['storageSizeGb'], storage_size)
        self.assertEqual(basic_info['backup']['backupRetentionDays'], backup_retention)

        self.cmd('{} flexible-server db show -g {} -s {} -d {}'
                    .format(database_engine, resource_group, server_name, database_name), checks=[JMESPathCheck('name', database_name)])

        self.cmd('{} flexible-server update -g {} -n {} -p randompw321##@!'
                 .format(database_engine, resource_group, server_name))

        self.cmd('{} flexible-server update -g {} -n {} --storage-size 256'
                 .format(database_engine, resource_group, server_name),
                 checks=[JMESPathCheck('storage.storageSizeGb', 256 )])

        self.cmd('{} flexible-server update -g {} -n {} --backup-retention {}'
                 .format(database_engine, resource_group, server_name, backup_retention + 10),
                 checks=[JMESPathCheck('backup.backupRetentionDays', backup_retention + 10)])

        tier = 'MemoryOptimized'
        sku_name = memory_optimized_sku
        self.cmd('{} flexible-server update -g {} -n {} --tier {} --sku-name {}'
                 .format(database_engine, resource_group, server_name, tier, sku_name),
                 checks=[JMESPathCheck('sku.tier', tier),
                         JMESPathCheck('sku.name', sku_name)])

        self.cmd('{} flexible-server update -g {} -n {} --tags keys=3'
                 .format(database_engine, resource_group, server_name),
                 checks=[JMESPathCheck('tags.keys', '3')])

        self.cmd('{} flexible-server restart -g {} -n {}'
                 .format(database_engine, resource_group, server_name), checks=NoneCheck())

        self.cmd('{} flexible-server stop -g {} -n {}'
                 .format(database_engine, resource_group, server_name), checks=NoneCheck())

        self.cmd('{} flexible-server start -g {} -n {}'
                 .format(database_engine, resource_group, server_name), checks=NoneCheck())

        self.cmd('{} flexible-server list -g {}'.format(database_engine, resource_group),
                 checks=[JMESPathCheck('type(@)', 'array')])

        restore_server_name = 'restore-' + server_name
        self.cmd('{} flexible-server restore -g {} --name {} --source-server {}'
                 .format(database_engine, resource_group, restore_server_name, server_name),
                 checks=[JMESPathCheck('name', restore_server_name)])

        connection_string = self.cmd('{} flexible-server show-connection-string -s {}'
                                     .format(database_engine, server_name)).get_output_in_json()

        self.assertIn('jdbc', connection_string['connectionStrings'])
        self.assertIn('node.js', connection_string['connectionStrings'])
        self.assertIn('php', connection_string['connectionStrings'])
        self.assertIn('python', connection_string['connectionStrings'])
        self.assertIn('ado.net', connection_string['connectionStrings'])

        self.cmd('{} flexible-server list-skus -l {}'.format(database_engine, location),
                 checks=[JMESPathCheck('type(@)', 'array')])

        self.cmd('{} flexible-server delete -g {} -n {} --yes'.format(database_engine, resource_group, server_name), checks=NoneCheck())

        self.cmd('{} flexible-server delete -g {} -n {} --yes'.format(database_engine, resource_group, restore_server_name), checks=NoneCheck())
    
    # @pytest.mark.custom_mark
    def _test_mysql_flexible_server_import_create(self, database_engine, resource_group):
        storage_size = 32
        version = '5.7'
        location = 'eastus'
        sku_name = 'Standard_B1ms'
        tier = 'Burstable'
        resource_group = 'nitishsharma-group'
        server_name = self.create_random_name(SERVER_NAME_PREFIX, SERVER_NAME_MAX_LENGTH)
        data_source_type = 'mysql_single'
        data_source = 'nitish-single-ss'
        mode = 'offline'

        self.cmd('{} flexible-server import create -g {} -n {} --sku-name {} --tier {} \
                  --storage-size {} -u {} --version {} --tags keys=3 \
                  --public-access None --location {} --data-source-type {} --data-source {} --mode {}'.format(database_engine,
                                                                                                              resource_group, server_name, sku_name, tier, storage_size,
                                                                                                              'dbadmin', version, location, data_source_type, data_source, mode))

        basic_info = self.cmd('{} flexible-server show -g {} -n {}'.format(database_engine, resource_group, server_name)).get_output_in_json()
        self.assertEqual(basic_info['name'], server_name)
        self.assertEqual(str(basic_info['location']).replace(' ', '').lower(), location)
        self.assertEqual(basic_info['resourceGroup'], resource_group)
        self.assertEqual(basic_info['sku']['name'], sku_name)
        self.assertEqual(basic_info['sku']['tier'], tier)
        self.assertEqual(basic_info['version'], version)
        self.assertEqual(basic_info['storage']['storageSizeGb'], storage_size)

        self.cmd('{} flexible-server delete -g {} -n {} --yes'.format(database_engine, resource_group, server_name), checks=NoneCheck())
        

    def _test_flexible_server_check_name_availability_fallback_mgmt(self, database_engine, resource_group):
        server_name = self.create_random_name(SERVER_NAME_PREFIX, SERVER_NAME_MAX_LENGTH)

        self.cmd('{} flexible-server create -g {} -n {} --public-access None --tier GeneralPurpose --sku-name {}'
                 .format(database_engine, resource_group, server_name, mysql_general_purpose_sku))
        
        self.cmd('{} flexible-server delete -g {} -n {} --yes'.format(database_engine, resource_group, server_name))
    
    def _test_flexible_server_iops_mgmt(self, database_engine, resource_group):

        if self.cli_ctx.local_context.is_on:
            self.cmd('config param-persist off')

        location = mysql_location
        list_skus_info = get_mysql_list_skus_info(self, location)
        iops_info = list_skus_info['iops_info']

        # flexible-server create with user input
        server_name = self.create_random_name(SERVER_NAME_PREFIX, SERVER_NAME_MAX_LENGTH)
        server_name_2 = self.create_random_name(SERVER_NAME_PREFIX + '2', SERVER_NAME_MAX_LENGTH)
        server_name_3 = self.create_random_name(SERVER_NAME_PREFIX + '3', SERVER_NAME_MAX_LENGTH)

        # IOPS passed is within limit of max allowed by SKU but smaller than storage*3
        self.cmd('{} flexible-server create --public-access none -g {} -n {} -l {} --iops 50 --storage-size 200 --tier Burstable --sku-name Standard_B1s'
                 .format(database_engine, resource_group, server_name, location))

        result = self.cmd('{} flexible-server show -g {} -n {}'.format(database_engine, resource_group, server_name),
                          checks=[JMESPathCheck('storage.iops', 400)]).get_output_in_json()

        # SKU upgraded and IOPS value set smaller than free iops, max iops for the sku

        iops = 400
        iops_result = _determine_iops(storage_gb=result["storage"]["storageSizeGb"],
                                      iops_info=iops_info,
                                      iops_input=iops,
                                      tier="Burstable",
                                      sku_name="Standard_B1ms")
        self.assertEqual(iops_result, 640)

        # SKU downgraded and IOPS not specified
        iops = result["storage"]["iops"]
        iops_result = _determine_iops(storage_gb=result["storage"]["storageSizeGb"],
                                      iops_info=iops_info,
                                      iops_input=iops,
                                      tier="Burstable",
                                      sku_name="Standard_B1s")
        self.assertEqual(iops_result, 400)

        # IOPS passed is within limit of max allowed by SKU but smaller than default
        self.cmd('{} flexible-server create --public-access none -g {} -n {} -l {} --iops 50 --storage-size 30 --tier Burstable --sku-name Standard_B1s'
                 .format(database_engine, resource_group, server_name_2, location))

        result = self.cmd('{} flexible-server show -g {} -n {}'.format(database_engine, resource_group, server_name_2),
                          checks=[JMESPathCheck('storage.iops', 390)]).get_output_in_json()

        iops = 700
        iops_result = _determine_iops(storage_gb=result["storage"]["storageSizeGb"],
                                      iops_info=iops_info,
                                      iops_input=iops,
                                      tier="Burstable",
                                      sku_name="Standard_B1ms")
        self.assertEqual(iops_result, 640)

        # IOPS passed is within limit of max allowed by SKU and bigger than default
        self.cmd('{} flexible-server create --public-access none -g {} -n {} -l {} --iops 50 --storage-size 40 --tier Burstable --sku-name Standard_B1s'
                 .format(database_engine, resource_group, server_name_3, location))

        self.cmd('{} flexible-server show -g {} -n {}'.format(database_engine, resource_group, server_name_3),
                 checks=[JMESPathCheck('storage.iops', 400)])

        iops = 500
        iops_result = _determine_iops(storage_gb=300,
                                      iops_info=iops_info,
                                      iops_input=iops,
                                      tier="Burstable",
                                      sku_name="Standard_B1ms")
        self.assertEqual(iops_result, 640)

    def _test_flexible_server_paid_iops_mgmt(self, database_engine, resource_group):
        
        location = mysql_location
        server_name = self.create_random_name(SERVER_NAME_PREFIX, SERVER_NAME_MAX_LENGTH)
        server_name_2 = self.create_random_name(SERVER_NAME_PREFIX + '2', SERVER_NAME_MAX_LENGTH)

        self.cmd('{} flexible-server create --public-access none -g {} -n {} -l {} --iops 50 --storage-size 64 --sku-name {} --tier GeneralPurpose'
                 .format(database_engine, resource_group, server_name, location, mysql_general_purpose_sku))
        
        self.cmd('{} flexible-server show -g {} -n {}'.format(database_engine, resource_group, server_name),
                          checks=[JMESPathCheck('storage.autoIoScaling', 'Disabled')]).get_output_in_json()

        self.cmd('{} flexible-server update -g {} -n {} --auto-scale-iops Enabled'
                 .format(database_engine, resource_group, server_name))
        
        self.cmd('{} flexible-server show -g {} -n {}'.format(database_engine, resource_group, server_name),
                          checks=[JMESPathCheck('storage.autoIoScaling', 'Enabled')]).get_output_in_json()
        
        self.cmd('{} flexible-server update -g {} -n {} --auto-scale-iops Disabled'
                 .format(database_engine, resource_group, server_name))
        
        self.cmd('{} flexible-server show -g {} -n {}'.format(database_engine, resource_group, server_name),
                          checks=[JMESPathCheck('storage.autoIoScaling', 'Disabled')]).get_output_in_json()

        self.cmd('{} flexible-server create --public-access none -g {} -n {} -l {} --auto-scale-iops Enabled --storage-size 64 --sku-name {} --tier GeneralPurpose'
                 .format(database_engine, resource_group, server_name_2, location, mysql_general_purpose_sku))

        self.cmd('{} flexible-server show -g {} -n {}'.format(database_engine, resource_group, server_name_2),
                          checks=[JMESPathCheck('storage.autoIoScaling', 'Enabled')]).get_output_in_json()

    def _test_flexible_server_restore_mgmt(self, database_engine, resource_group):

        private_dns_param = 'privateDnsZoneResourceId' if database_engine == 'mysql' else 'privateDnsZoneArmResourceId'
        if database_engine == 'postgres':
            location = self.postgres_location
        elif database_engine == 'mysql':
            location = mysql_location

        source_server = self.create_random_name(SERVER_NAME_PREFIX, SERVER_NAME_MAX_LENGTH)
        target_server_default = self.create_random_name(SERVER_NAME_PREFIX, SERVER_NAME_MAX_LENGTH)
        target_server_diff_vnet = self.create_random_name(SERVER_NAME_PREFIX, SERVER_NAME_MAX_LENGTH)
        target_server_diff_vnet_2 = self.create_random_name(SERVER_NAME_PREFIX, SERVER_NAME_MAX_LENGTH)
        target_server_public_access = self.create_random_name(SERVER_NAME_PREFIX, SERVER_NAME_MAX_LENGTH)
        target_server_config = self.create_random_name(SERVER_NAME_PREFIX, SERVER_NAME_MAX_LENGTH)

        source_vnet = self.create_random_name('VNET', SERVER_NAME_MAX_LENGTH)
        source_subnet = self.create_random_name('SUBNET', SERVER_NAME_MAX_LENGTH)
        new_vnet = self.create_random_name('VNET', SERVER_NAME_MAX_LENGTH)
        new_subnet = self.create_random_name('SUBNET', SERVER_NAME_MAX_LENGTH)
        new_vnet_2 = self.create_random_name('VNET', SERVER_NAME_MAX_LENGTH)
        new_subnet_2 = self.create_random_name('SUBNET', SERVER_NAME_MAX_LENGTH)

        self.cmd('{} flexible-server create -g {} -n {} --vnet {} --subnet {} -l {} --yes'.format(
                 database_engine, resource_group, source_server, source_vnet, source_subnet, location))
        result = self.cmd('{} flexible-server show -g {} -n {}'.format(database_engine, resource_group, source_server)).get_output_in_json()

        # Wait until snapshot is created
        current_time = datetime.utcnow().replace(tzinfo=tzutc()).isoformat()
        earliest_restore_time = result['backup']['earliestRestoreDate']
        seconds_to_wait = (parser.isoparse(earliest_restore_time) - parser.isoparse(current_time)).total_seconds()
        os.environ.get(ENV_LIVE_TEST, False) and sleep(max(0, seconds_to_wait) + 180)

        # default vnet resources
        restore_result = self.cmd('{} flexible-server restore -g {} --name {} --source-server {} '
                                  .format(database_engine, resource_group, target_server_default, source_server)).get_output_in_json()

        self.assertEqual(restore_result['network']['delegatedSubnetResourceId'],
                         '/subscriptions/{}/resourceGroups/{}/providers/Microsoft.Network/virtualNetworks/{}/subnets/{}'.format(
                             self.get_subscription_id(), resource_group, source_vnet, source_subnet))
        self.assertEqual(restore_result['network'][private_dns_param],
                         '/subscriptions/{}/resourceGroups/{}/providers/Microsoft.Network/privateDnsZones/{}'.format(
                             self.get_subscription_id(), resource_group, '{}.private.{}.database.azure.com'.format(source_server, database_engine)))

        # MYSQL only - vnet to public access
        if database_engine == 'mysql':
            restore_result = self.cmd('{} flexible-server restore -g {} --name {} --source-server {} --public-access Enabled'
                                  .format(database_engine, resource_group, target_server_public_access, source_server)).get_output_in_json()

            #self.assertEqual(restore_result['network']['publicNetworkAccess'], 'Enabled')

        # to different vnet and private dns zone
        self.cmd('network vnet create -g {} -l {} -n {} --address-prefixes 172.1.0.0/16'.format(
                 resource_group, location, new_vnet))

        subnet = self.cmd('network vnet subnet create -g {} -n {} --vnet-name {} --address-prefixes 172.1.0.0/24'.format(
                          resource_group, new_subnet, new_vnet)).get_output_in_json()

        private_dns_zone = '{}.private.{}.database.azure.com'.format(target_server_diff_vnet, database_engine)
        self.cmd('network private-dns zone create -g {} --name {}'.format(resource_group, private_dns_zone))

        restore_result = self.cmd('{} flexible-server restore -g {} -n {} --source-server {} --subnet {} --private-dns-zone {}'.format(
                                  database_engine, resource_group, target_server_diff_vnet, source_server, subnet["id"], private_dns_zone)).get_output_in_json()

        self.assertEqual(restore_result['network']['delegatedSubnetResourceId'],
                         '/subscriptions/{}/resourceGroups/{}/providers/Microsoft.Network/virtualNetworks/{}/subnets/{}'.format(
                             self.get_subscription_id(), resource_group, new_vnet, new_subnet))

        self.assertEqual(restore_result['network'][private_dns_param],
                         '/subscriptions/{}/resourceGroups/{}/providers/Microsoft.Network/privateDnsZones/{}'.format(
                             self.get_subscription_id(), resource_group, private_dns_zone))

        # public access to vnet
        if database_engine == 'mysql':
            self.cmd('network vnet create -g {} -l {} -n {} --address-prefixes 172.1.0.0/16'.format(
            resource_group, location, new_vnet_2))

            subnet = self.cmd('network vnet subnet create -g {} -n {} --vnet-name {} --address-prefixes 172.1.0.0/24'.format(
                            resource_group, new_subnet_2, new_vnet_2)).get_output_in_json()

            private_dns_zone = '{}.private.{}.database.azure.com'.format(target_server_diff_vnet_2, database_engine)
            self.cmd('network private-dns zone create -g {} --name {}'.format(resource_group, private_dns_zone))

            restore_result = self.cmd('{} flexible-server restore -g {} -n {} --source-server {} --subnet {} --private-dns-zone {}'.format(
                                    database_engine, resource_group, target_server_diff_vnet_2, target_server_public_access, subnet["id"], private_dns_zone)).get_output_in_json()

            self.assertEqual(restore_result['network']['delegatedSubnetResourceId'],
                            '/subscriptions/{}/resourceGroups/{}/providers/Microsoft.Network/virtualNetworks/{}/subnets/{}'.format(
                                self.get_subscription_id(), resource_group, new_vnet_2, new_subnet_2))

            self.assertEqual(restore_result['network'][private_dns_param],
                            '/subscriptions/{}/resourceGroups/{}/providers/Microsoft.Network/privateDnsZones/{}'.format(
                                self.get_subscription_id(), resource_group, private_dns_zone))
            
        # take params tier, storage-size, sku-name, storage-auto-grow, backup-retention and geo-redundant-backup
        if database_engine == 'mysql':
            restore_result = self.cmd('{} flexible-server restore -g {} -n {} --source-server {} --storage-size 64 --tier GeneralPurpose --storage-auto-grow Enabled --sku-name {} --backup-retention 9  --geo-redundant-backup Enabled'.format(
                                    database_engine, resource_group, target_server_config, source_server, mysql_general_purpose_sku)).get_output_in_json()
            
            self.assertEqual(restore_result['backup']['backupRetentionDays'], 9)
            self.assertEqual(restore_result['backup']['geoRedundantBackup'], "Enabled")
            self.assertEqual(restore_result['sku']['name'], mysql_general_purpose_sku)
            self.assertEqual(restore_result['sku']['tier'], "GeneralPurpose")
            self.assertEqual(restore_result['storage']['storageSizeGb'], 64)
            self.assertEqual(restore_result['storage']['autoGrow'], "Enabled")

        self.cmd('{} flexible-server delete -g {} -n {} --yes'.format(
                 database_engine, resource_group, source_server), checks=NoneCheck())

        self.cmd('{} flexible-server delete -g {} -n {} --yes'.format(
                 database_engine, resource_group, target_server_default), checks=NoneCheck())

        self.cmd('{} flexible-server delete -g {} -n {} --yes'.format(
                 database_engine, resource_group, target_server_diff_vnet), checks=NoneCheck())

        self.cmd('{} flexible-server delete -g {} -n {} --yes'.format(
                 database_engine, resource_group, target_server_diff_vnet_2), checks=NoneCheck())

        self.cmd('{} flexible-server delete -g {} -n {} --yes'.format(
                 database_engine, resource_group, target_server_public_access), checks=NoneCheck())
        
        self.cmd('{} flexible-server delete -g {} -n {} --yes'.format(
                 database_engine, resource_group, target_server_config), checks=NoneCheck())

    def _test_flexible_server_georestore_mgmt(self, database_engine, resource_group):

        private_dns_param = 'privateDnsZoneResourceId' if database_engine == 'mysql' else 'privateDnsZoneArmResourceId'
        if database_engine == 'postgres':
            location = self.postgres_location
            target_location = 'westus'
        elif database_engine == 'mysql':
            location = mysql_location
            target_location = mysql_paired_location

        source_server = self.create_random_name(SERVER_NAME_PREFIX, SERVER_NAME_MAX_LENGTH)
        source_server_2 = self.create_random_name(SERVER_NAME_PREFIX, SERVER_NAME_MAX_LENGTH)
        target_server_default = self.create_random_name(SERVER_NAME_PREFIX, SERVER_NAME_MAX_LENGTH)
        target_server_diff_vnet = self.create_random_name(SERVER_NAME_PREFIX, SERVER_NAME_MAX_LENGTH)
        target_server_diff_vnet_2 = self.create_random_name(SERVER_NAME_PREFIX, SERVER_NAME_MAX_LENGTH)
        target_server_public_access = self.create_random_name(SERVER_NAME_PREFIX, SERVER_NAME_MAX_LENGTH)
        target_server_public_access_2 = self.create_random_name(SERVER_NAME_PREFIX, SERVER_NAME_MAX_LENGTH)
        target_server_config = self.create_random_name(SERVER_NAME_PREFIX, SERVER_NAME_MAX_LENGTH)

        source_vnet = self.create_random_name('VNET', SERVER_NAME_MAX_LENGTH)
        source_subnet = self.create_random_name('SUBNET', SERVER_NAME_MAX_LENGTH)
        new_vnet = self.create_random_name('VNET', SERVER_NAME_MAX_LENGTH)
        new_subnet = self.create_random_name('SUBNET', SERVER_NAME_MAX_LENGTH)
        new_vnet_2 = self.create_random_name('VNET', SERVER_NAME_MAX_LENGTH)
        new_subnet_2 = self.create_random_name('SUBNET', SERVER_NAME_MAX_LENGTH)

        self.cmd('{} flexible-server create -g {} -n {} --vnet {} --subnet {} -l {} --geo-redundant-backup Enabled --yes'.format(
                 database_engine, resource_group, source_server, source_vnet, source_subnet, location))
        result = self.cmd('{} flexible-server show -g {} -n {}'.format(database_engine, resource_group, source_server)).get_output_in_json()
        self.assertEqual(result['backup']['geoRedundantBackup'], 'Enabled')

        self.cmd('{} flexible-server create -g {} -n {} --public-access None -l {} --geo-redundant-backup Enabled'.format(
                 database_engine, resource_group, source_server_2, location))
        result = self.cmd('{} flexible-server show -g {} -n {}'.format(database_engine, resource_group, source_server_2)).get_output_in_json()
        self.assertEqual(result['backup']['geoRedundantBackup'], 'Enabled')
        self.assertEqual(result['network']['publicNetworkAccess'], 'Enabled')

        # 1. vnet -> vnet without network parameters fail
        self.cmd('{} flexible-server geo-restore -g {} -l {} --name {} --source-server {} '
                 .format(database_engine, resource_group, target_location, target_server_default, source_server), expect_failure=True)

        # 2. vnet to public access
        if database_engine == 'mysql':
            restore_result = self.cmd('{} flexible-server geo-restore -g {} -l {} --name {} --source-server {} --public-access enabled'
                                  .format(database_engine, resource_group, target_location, target_server_public_access, source_server)).get_output_in_json()

            #self.assertEqual(restore_result['network']['publicNetworkAccess'], 'Enabled')
            self.assertEqual(str(restore_result['location']).replace(' ', '').lower(), target_location)

        # 3. vnet to different vnet
        self.cmd('network vnet create -g {} -l {} -n {} --address-prefixes 172.1.0.0/16'.format(
                 resource_group, target_location, new_vnet))

        subnet = self.cmd('network vnet subnet create -g {} -n {} --vnet-name {} --address-prefixes 172.1.0.0/24'.format(
                          resource_group, new_subnet, new_vnet)).get_output_in_json()

        restore_result = retryable_method(retries=10, interval_sec=360 if os.environ.get(ENV_LIVE_TEST, False) else 0, exception_type=HttpResponseError,
                                          condition=lambda ex: 'GeoBackupsNotAvailable' in ex.message)(self.cmd)(
                                              '{} flexible-server geo-restore -g {} -l {} -n {} --source-server {} --subnet {} --yes'.format(
                                              database_engine, resource_group, target_location, target_server_diff_vnet, source_server, subnet["id"])
                                          ).get_output_in_json()

        self.assertEqual(restore_result['network']['delegatedSubnetResourceId'],
                         '/subscriptions/{}/resourceGroups/{}/providers/Microsoft.Network/virtualNetworks/{}/subnets/{}'.format(
                             self.get_subscription_id(), resource_group, new_vnet, new_subnet))

        self.assertEqual(restore_result['network'][private_dns_param],  # private dns zone needs to be created
                         '/subscriptions/{}/resourceGroups/{}/providers/Microsoft.Network/privateDnsZones/{}'.format(
                             self.get_subscription_id(), resource_group, '{}.private.{}.database.azure.com'.format(target_server_diff_vnet, database_engine)))

        # 4. public access to vnet
        if database_engine == 'mysql':
            self.cmd('network vnet create -g {} -l {} -n {} --address-prefixes 172.1.0.0/16'.format(
            resource_group, target_location, new_vnet_2))

            subnet = self.cmd('network vnet subnet create -g {} -n {} --vnet-name {} --address-prefixes 172.1.0.0/24'.format(
                            resource_group, new_subnet_2, new_vnet_2)).get_output_in_json()

            private_dns_zone = '{}.private.{}.database.azure.com'.format(target_server_diff_vnet_2, database_engine)
            self.cmd('network private-dns zone create -g {} --name {}'.format(resource_group, private_dns_zone))

            restore_result = self.cmd('{} flexible-server geo-restore -g {} -l {} -n {} --source-server {} --subnet {} --private-dns-zone {} --public-access disabled --yes'.format(
                                    database_engine, resource_group, target_location, target_server_diff_vnet_2, source_server_2, subnet["id"], private_dns_zone)).get_output_in_json()

            self.assertEqual(restore_result['network']['delegatedSubnetResourceId'],
                            '/subscriptions/{}/resourceGroups/{}/providers/Microsoft.Network/virtualNetworks/{}/subnets/{}'.format(
                                self.get_subscription_id(), resource_group, new_vnet_2, new_subnet_2))

            self.assertEqual(restore_result['network'][private_dns_param],
                            '/subscriptions/{}/resourceGroups/{}/providers/Microsoft.Network/privateDnsZones/{}'.format(
                                self.get_subscription_id(), resource_group, private_dns_zone))

        # 5. public to public
        restore_result = retryable_method(retries=10, interval_sec=360 if os.environ.get(ENV_LIVE_TEST, False) else 0, exception_type=HttpResponseError,
                                          condition=lambda ex: 'GeoBackupsNotAvailable' in ex.message)(self.cmd)(
                                              '{} flexible-server geo-restore -g {} -l {} --name {} --source-server {}'.format(
                                              database_engine, resource_group, target_location, target_server_public_access_2, source_server_2)
                                         ).get_output_in_json()

        #self.assertEqual(restore_result['network']['publicNetworkAccess'], 'Enabled')
        self.assertEqual(str(restore_result['location']).replace(' ', '').lower(), target_location)

        # 6. take params tier, storage-size, sku-name, storage-auto-grow, backup-retention and geo-redundant-backup
        if database_engine == 'mysql':
            restore_result = self.cmd('{} flexible-server geo-restore -g {} -l {} -n {} --source-server {} --public-access enabled --storage-size 64 --tier GeneralPurpose --storage-auto-grow Enabled --sku-name {} --backup-retention 9  --geo-redundant-backup Enabled'.format(
                                    database_engine, resource_group, target_location, target_server_config, source_server, mysql_general_purpose_sku)).get_output_in_json()
            
            self.assertEqual(restore_result['backup']['backupRetentionDays'], 9)
            self.assertEqual(restore_result['backup']['geoRedundantBackup'], "Enabled")
            self.assertEqual(restore_result['sku']['name'], mysql_general_purpose_sku)
            self.assertEqual(restore_result['sku']['tier'], "GeneralPurpose")
            self.assertEqual(restore_result['storage']['storageSizeGb'], 64)
            self.assertEqual(restore_result['storage']['autoGrow'], "Enabled")

        # Delete servers
        self.cmd('{} flexible-server delete -g {} -n {} --yes'.format(
                 database_engine, resource_group, source_server), checks=NoneCheck())

        self.cmd('{} flexible-server delete -g {} -n {} --yes'.format(
                 database_engine, resource_group, target_server_diff_vnet), checks=NoneCheck())

        self.cmd('{} flexible-server delete -g {} -n {} --yes'.format(
                 database_engine, resource_group, target_server_diff_vnet_2), checks=NoneCheck())

        self.cmd('{} flexible-server delete -g {} -n {} --yes'.format(
                 database_engine, resource_group, target_server_public_access), checks=NoneCheck())

        self.cmd('{} flexible-server delete -g {} -n {} --yes'.format(
                 database_engine, resource_group, target_server_config), checks=NoneCheck())

    def _test_flexible_server_georestore_update_mgmt(self, database_engine, resource_group):
        if database_engine == 'postgres':
            location = self.postgres_location
        elif database_engine == 'mysql':
            location = mysql_location
            target_location = mysql_paired_location

        source_server = self.create_random_name(SERVER_NAME_PREFIX, SERVER_NAME_MAX_LENGTH)
        target_server = self.create_random_name(SERVER_NAME_PREFIX, SERVER_NAME_MAX_LENGTH)

        self.cmd('{} flexible-server create -g {} -n {} -l {} --public-access none --tier {} --sku-name {}'
                 .format(database_engine, resource_group, source_server, location, 'GeneralPurpose', mysql_general_purpose_sku))

        self.cmd('{} flexible-server show -g {} -n {}'
                 .format(database_engine, resource_group, source_server),
                 checks=[JMESPathCheck('backup.geoRedundantBackup', 'Disabled')])

        result = self.cmd('{} flexible-server update -g {} -n {} --geo-redundant-backup Enabled'
                          .format(database_engine, resource_group, source_server),
                          checks=[JMESPathCheck('backup.geoRedundantBackup', 'Enabled')]).get_output_in_json()

        current_time = datetime.utcnow().replace(tzinfo=tzutc()).isoformat()
        earliest_restore_time = result['backup']['earliestRestoreDate']
        seconds_to_wait = (parser.isoparse(earliest_restore_time) - parser.isoparse(current_time)).total_seconds()
        os.environ.get(ENV_LIVE_TEST, False) and sleep(max(0, seconds_to_wait) + 180)

        self.cmd('{} flexible-server geo-restore -g {} -l {} -n {} --source-server {}'
                 .format(database_engine, resource_group, target_location, target_server, source_server),
                 checks=[JMESPathCheck('backup.geoRedundantBackup', 'Enabled')])

        self.cmd('{} flexible-server update -g {} -n {} --geo-redundant-backup Disabled'
                 .format(database_engine, resource_group, source_server),
                 checks=[JMESPathCheck('backup.geoRedundantBackup', 'Disabled')])

        self.cmd('{} flexible-server delete -g {} -n {} --yes'.format(database_engine, resource_group, source_server))
        self.cmd('{} flexible-server delete -g {} -n {} --yes'.format(database_engine, resource_group, target_server))

    def _test_flexible_server_byok_mgmt(self, database_engine, resource_group, vault_name, backup_vault_name=None):
        key_name = self.create_random_name('rdbmskey', 32)
        identity_name = self.create_random_name('identity', 32)
        backup_key_name = self.create_random_name('rdbmskey', 32)
        backup_identity_name = self.create_random_name('identity', 32)
        server_name = self.create_random_name(SERVER_NAME_PREFIX, SERVER_NAME_MAX_LENGTH)
        replica_1_name = self.create_random_name(SERVER_NAME_PREFIX, SERVER_NAME_MAX_LENGTH)
        replica_2_name = self.create_random_name(SERVER_NAME_PREFIX, SERVER_NAME_MAX_LENGTH)
        backup_name = self.create_random_name(SERVER_NAME_PREFIX, SERVER_NAME_MAX_LENGTH)
        key_2_name = self.create_random_name('rdbmskey', 32)
        identity_2_name = self.create_random_name('identity', 32)
        server_2_name = self.create_random_name(SERVER_NAME_PREFIX, SERVER_NAME_MAX_LENGTH)
        tier = 'GeneralPurpose'
        if database_engine == 'mysql':
            sku_name = mysql_general_purpose_sku
            location = mysql_paired_location
            backup_location = mysql_location
            replication_role = 'Replica'
        elif database_engine == 'postgres':
            sku_name = 'Standard_D2s_v3'
            location = self.postgres_location
            backup_location = 'westus'
            replication_role = 'AsyncReplica'

        key = self.cmd('keyvault key create --name {} -p software --vault-name {}'
                       .format(key_name, vault_name)).get_output_in_json()

        identity = self.cmd('identity create -g {} --name {} --location {}'.format(resource_group, identity_name, location)).get_output_in_json()

        self.cmd('keyvault set-policy -g {} -n {} --object-id {} --key-permissions wrapKey unwrapKey get list'
                 .format(resource_group, vault_name, identity['principalId']))

        if database_engine == 'mysql':
            backup_key = self.cmd('keyvault key create --name {} -p software --vault-name {}'
                                  .format(backup_key_name, backup_vault_name)).get_output_in_json()

            backup_identity = self.cmd('identity create -g {} --name {} --location {}'.format(resource_group, backup_identity_name, backup_location)).get_output_in_json()

            self.cmd('keyvault set-policy -g {} -n {} --object-id {} --key-permissions wrapKey unwrapKey get list'
                     .format(resource_group, backup_vault_name, backup_identity['principalId']))
        elif database_engine == 'postgres':
            key_2 = self.cmd('keyvault key create --name {} -p software --vault-name {}'
                             .format(key_2_name, vault_name)).get_output_in_json()

            identity_2 = self.cmd('identity create -g {} --name {} --location {}'.format(resource_group, identity_2_name, location)).get_output_in_json()

            self.cmd('keyvault set-policy -g {} -n {} --object-id {} --key-permissions wrapKey unwrapKey get list'
                     .format(resource_group, vault_name, identity_2['principalId']))

        def invalid_input_tests():
            # key or identity only
            self.cmd('{} flexible-server create -g {} -n {} --public-access none --tier {} --sku-name {} --key {}'.format(
                database_engine,
                resource_group,
                server_name,
                tier,
                sku_name,
                key['key']['kid']
            ), expect_failure=True)

            self.cmd('{} flexible-server create -g {} -n {} --public-access none --tier {} --sku-name {} --identity {}'.format(
                database_engine,
                resource_group,
                server_name,
                tier,
                sku_name,
                identity['id'],
            ), expect_failure=True)

            if database_engine == 'mysql':
                # backup key or backup identity only
                self.cmd('{} flexible-server create -g {} -n {} --public-access none --tier {} --sku-name {} --key {} --identity {} --backup-key {} --geo-redundant-backup Enabled'.format(
                    database_engine,
                    resource_group,
                    server_name,
                    tier,
                    sku_name,
                    key['key']['kid'],
                    identity['id'],
                    backup_key['key']['kid']
                ), expect_failure=True)

                self.cmd('{} flexible-server create -g {} -n {} --public-access none --tier {} --sku-name {} --key {} --identity {} --backup-identity {} --geo-redundant-backup Enabled'.format(
                    database_engine,
                    resource_group,
                    server_name,
                    tier,
                    sku_name,
                    key['key']['kid'],
                    identity['id'],
                    backup_identity['id'],
                ), expect_failure=True)

                # backup key without principal key
                self.cmd('{} flexible-server create -g {} -n {} --public-access none --tier {} --sku-name {} --backup-key {} --backup-identity {}'.format(
                    database_engine,
                    resource_group,
                    server_name,
                    tier,
                    sku_name,
                    backup_key['key']['kid'],
                    backup_identity['id']
                ), expect_failure=True)

                # geo-redundant server without backup-key
                self.cmd('{} flexible-server create -g {} -n {} --public-access none --tier {} --sku-name {} --key {} --identity {} --geo-redundant-backup Enabled'.format(
                    database_engine,
                    resource_group,
                    server_name,
                    tier,
                    sku_name,
                    key['key']['kid'],
                    identity['id'],
                ), expect_failure=True)
            elif database_engine == 'postgres':
                # geo-redundant server with data encryption is not supported
                self.cmd('{} flexible-server create -g {} -n {} --public-access none --tier {} --sku-name {} --key {} --identity {} --geo-redundant-backup Enabled'.format(
                    database_engine,
                    resource_group,
                    server_name,
                    tier,
                    sku_name,
                    key['key']['kid'],
                    identity['id'],
                ), expect_failure=True)

        def main_tests(geo_redundant_backup):
            geo_redundant_backup_enabled = 'Enabled' if geo_redundant_backup else 'Disabled'
            backup_key_id_flags = '--backup-key {} --backup-identity {}'.format(backup_key['key']['kid'], backup_identity['id']) if geo_redundant_backup else ''
            restore_type = 'geo-restore --location {}'.format(backup_location) if geo_redundant_backup else 'restore'

            # create primary flexible server with data encryption
            self.cmd('{} flexible-server create -g {} -n {} --public-access none --tier {} --sku-name {} --key {} --identity {} {} --location {} --geo-redundant-backup {}'.format(
                        database_engine,
                        resource_group,
                        server_name,
                        tier,
                        sku_name,
                        key['key']['kid'],
                        identity['id'],
                        backup_key_id_flags,
                        location,
                        geo_redundant_backup_enabled
                    ))

            # should fail because we can't remove identity used for data encryption
            self.cmd('{} flexible-server identity remove -g {} -s {} -n {} --yes'
                     .format(database_engine, resource_group, server_name, identity['id']),
                     expect_failure=True)

            if database_engine == 'mysql' and geo_redundant_backup:
                self.cmd('{} flexible-server identity remove -g {} -s {} -n {} --yes'
                         .format(database_engine, resource_group, server_name, backup_identity['id']),
                         expect_failure=True)

            main_checks = [
                JMESPathCheckExists('identity.userAssignedIdentities."{}"'.format(identity['id'])),
                JMESPathCheck('dataEncryption.primaryKeyUri', key['key']['kid']),
                JMESPathCheck('dataEncryption.primaryUserAssignedIdentityId', identity['id'])
            ]

            if geo_redundant_backup:
                main_checks += [
                    JMESPathCheckExists('identity.userAssignedIdentities."{}"'.format(backup_identity['id'])),
                    JMESPathCheck('dataEncryption.geoBackupKeyUri', backup_key['key']['kid']),
                    JMESPathCheck('dataEncryption.geoBackupUserAssignedIdentityId', backup_identity['id'])
                ]

            result = self.cmd('{} flexible-server show -g {} -n {}'.format(database_engine, resource_group, server_name),
                    checks=main_checks).get_output_in_json()

            if database_engine == 'mysql':
                # should fail because disable-data-encryption and key for data encryption are provided at the same time
                self.cmd('{} flexible-server update -g {} -n {} --key {} --identity {} --disable-data-encryption'.format(
                    database_engine,
                    resource_group,
                    server_name,
                    key['key']['kid'],
                    identity['id']
                ), expect_failure=True)

                # disable data encryption in primary server
                self.cmd('{} flexible-server update -g {} -n {} --disable-data-encryption'.format(database_engine, resource_group, server_name),
                        checks=[JMESPathCheck('dataEncryption', None)])

                # create replica 1, it shouldn't have data encryption
                self.cmd('{} flexible-server replica create -g {} --replica-name {} --source-server {}'.format(
                            database_engine,
                            resource_group,
                            replica_1_name,
                            server_name
                ), checks=[
                    JMESPathCheckExists('identity.userAssignedIdentities."{}"'.format(identity['id'])),
                    JMESPathCheck('dataEncryption', None),
                    JMESPathCheck('replicationRole', replication_role)
                ] + ([JMESPathCheckExists('identity.userAssignedIdentities."{}"'.format(backup_identity['id']))] if geo_redundant_backup else []))

                # enable data encryption again in primary server
                self.cmd('{} flexible-server update -g {} -n {} --key {} --identity {} {}'.format(
                            database_engine,
                            resource_group,
                            server_name,
                            key['key']['kid'],
                            identity['id'],
                            backup_key_id_flags
                ), checks=main_checks)

                # replica 1 now should have data encryption as well
                self.cmd('{} flexible-server show -g {} -n {}'.format(database_engine, resource_group, replica_1_name),
                            checks=main_checks)

                # create replica 2
                self.cmd('{} flexible-server replica create -g {} --replica-name {} --source-server {}'.format(
                            database_engine,
                            resource_group,
                            replica_2_name,
                            server_name
                ), checks=main_checks + [JMESPathCheck('replicationRole', replication_role)])

                # should fail because modifying data encryption on replica server is not allowed
                self.cmd('{} flexible-server update -g {} -n {} --disable-data-encryption'
                        .format(database_engine, resource_group, replica_2_name),
                    expect_failure=True)
            elif database_engine == 'postgres':
                # create replica 1 with data encryption
                self.cmd('{} flexible-server replica create -g {} --replica-name {} --source-server {} --key {} --identity {}'.format(
                            database_engine,
                            resource_group,
                            replica_1_name,
                            server_name,
                            key['key']['kid'],
                            identity['id']
                ), checks=main_checks + [JMESPathCheck('replicationRole', replication_role)])

                # update different key and identity in primary server
                self.cmd('{} flexible-server update -g {} -n {} --key {} --identity {}'.format(
                            database_engine,
                            resource_group,
                            server_name,
                            key_2['key']['kid'],
                            identity_2['id']
                ), checks=[
                    JMESPathCheckExists('identity.userAssignedIdentities."{}"'.format(identity_2['id'])),
                    JMESPathCheck('dataEncryption.primaryKeyUri', key_2['key']['kid']),
                    JMESPathCheck('dataEncryption.primaryUserAssignedIdentityId', identity_2['id'])
                ])

                # try to update key and identity in a server without data encryption
                self.cmd('{} flexible-server create -g {} -n {} --public-access none --tier {} --sku-name {} --location {}'.format(
                        database_engine,
                        resource_group,
                        server_2_name,
                        tier,
                        sku_name,
                        location
                    ))
                
                self.cmd('{} flexible-server update -g {} -n {} --key {} --identity {}'
                        .format(database_engine,
                        resource_group,
                        server_2_name,
                        key['key']['kid'],
                        identity['id']),
                    expect_failure=True)

                self.cmd('{} flexible-server delete -g {} -n {} --yes'.format(database_engine, resource_group, server_2_name))

            # restore backup
            current_time = datetime.utcnow().replace(tzinfo=tzutc()).isoformat()
            earliest_restore_time = result['backup']['earliestRestoreDate']
            seconds_to_wait = (parser.isoparse(earliest_restore_time) - parser.isoparse(current_time)).total_seconds()
            sleep(max(0, seconds_to_wait))

            restore_result = self.cmd('{} flexible-server {} -g {} --name {} --source-server {} {}'.format(
                     database_engine,
                     restore_type,
                     resource_group,
                     backup_name,
                     server_name,
                     F"--key {key['key']['kid']} --identity {identity['id']}" if database_engine == 'postgres' else ''
            ), checks=main_checks).get_output_in_json()

            if geo_redundant_backup:
                self.assertEqual(str(restore_result['location']).replace(' ', '').lower(), backup_location)

            if database_engine == 'mysql':
                # disable data encryption in primary server
                self.cmd('{} flexible-server update -g {} -n {} --disable-data-encryption'.format(database_engine, resource_group, server_name),
                        checks=[JMESPathCheck('dataEncryption', None)])

                # none of the replica servers should have data encryption now
                self.cmd('{} flexible-server show -g {} -n {}'.format(database_engine, resource_group, replica_1_name),
                    checks=[JMESPathCheck('dataEncryption', None)])

                self.cmd('{} flexible-server show -g {} -n {}'.format(database_engine, resource_group, replica_2_name),
                    checks=[JMESPathCheck('dataEncryption', None)])

            # delete all servers
            self.cmd('{} flexible-server delete -g {} -n {} --yes'.format(database_engine, resource_group, replica_1_name))
            self.cmd('{} flexible-server delete -g {} -n {} --yes'.format(database_engine, resource_group, replica_2_name))
            self.cmd('{} flexible-server delete -g {} -n {} --yes'.format(database_engine, resource_group, backup_name))
            self.cmd('{} flexible-server delete -g {} -n {} --yes'.format(database_engine, resource_group, server_name))

        invalid_input_tests()
        if database_engine == 'mysql' and backup_location != 'eastus2euap':
            main_tests(True)
        main_tests(False)

    def _test_flexible_server_gtid_reset(self, database_engine, resource_group):
        if database_engine == 'postgres':
            location = self.postgres_location
        elif database_engine == 'mysql':
            location = mysql_location

        source_server = self.create_random_name(SERVER_NAME_PREFIX, SERVER_NAME_MAX_LENGTH)

        self.cmd('{} flexible-server create -g {} -n {} -l {} --public-access none --tier {} --sku-name {}'
                 .format(database_engine, resource_group, source_server, location, 'GeneralPurpose', mysql_general_purpose_sku))
        
        self.cmd('{} flexible-server show -g {} -n {}'
                 .format(database_engine, resource_group, source_server),
                 checks=[JMESPathCheck('backup.geoRedundantBackup', 'Disabled')])
        
        # update server paramters to enable gtid
        source = 'user-override'
        parameter_name = 'enforce_gtid_consistency'
        self.cmd('{} flexible-server parameter set --name {} -v {} --source {} -s {} -g {}'
                 .format(database_engine, parameter_name, 'ON', source, source_server, resource_group),
                 checks=[JMESPathCheck('value', 'ON'), JMESPathCheck('source', source), JMESPathCheck('name', parameter_name)])

        parameter_name = 'gtid_mode'
        self.cmd('{} flexible-server parameter set --name {} -v {} --source {} -s {} -g {}'
                 .format(database_engine, parameter_name, 'OFF_PERMISSIVE', source, source_server, resource_group),
                 checks=[JMESPathCheck('value', 'OFF_PERMISSIVE'), JMESPathCheck('source', source), JMESPathCheck('name', parameter_name)])
        
        self.cmd('{} flexible-server parameter set --name {} -v {} --source {} -s {} -g {}'
                 .format(database_engine, parameter_name, 'ON_PERMISSIVE', source, source_server, resource_group),
                 checks=[JMESPathCheck('value', 'ON_PERMISSIVE'), JMESPathCheck('source', source), JMESPathCheck('name', parameter_name)])
        
        self.cmd('{} flexible-server parameter set --name {} -v {} --source {} -s {} -g {}'
                 .format(database_engine, parameter_name, 'ON', source, source_server, resource_group),
                 checks=[JMESPathCheck('value', 'ON'), JMESPathCheck('source', source), JMESPathCheck('name', parameter_name)])

        # set gtid string to source server
        self.cmd('{} flexible-server gtid reset --resource-group {} --server-name {} --gtid-set {} --yes'
                 .format(database_engine, resource_group, source_server, str(uuid.uuid4()).upper() + ":1"), expect_failure=False)

        # udpate server geo-redundant-backup to enable
        self.cmd('{} flexible-server update -g {} -n {} --geo-redundant-backup Enabled'
                 .format(database_engine, resource_group, source_server),
                 checks=[JMESPathCheck('backup.geoRedundantBackup', 'Enabled')])
        
        self.cmd('{} flexible-server gtid reset --resource-group {} --server-name {} --gtid-set {} --yes'
                 .format(database_engine, resource_group, source_server, str(uuid.uuid4()).upper() + ":1"), expect_failure=True)
        
        self.cmd('{} flexible-server delete -g {} -n {} --yes'.format(database_engine, resource_group, source_server))


class FlexibleServerProxyResourceMgmtScenarioTest(ScenarioTest):

    postgres_location = 'eastus'

    @AllowLargeResponse()
    @ResourceGroupPreparer(location=postgres_location)
    @ServerPreparer(engine_type='postgres', location=postgres_location)
    def test_postgres_flexible_server_proxy_resource(self, resource_group, server):
        self._test_firewall_rule_mgmt('postgres', resource_group, server)
        self._test_parameter_mgmt('postgres', resource_group, server)
        self._test_database_mgmt('postgres', resource_group, server)

    @pytest.mark.mysql_regression
    @AllowLargeResponse()
    @ResourceGroupPreparer(location=mysql_location)
    @ServerPreparer(engine_type='mysql', location=mysql_location)
    def test_mysql_flexible_server_proxy_resource(self, resource_group, server):
        self._test_firewall_rule_mgmt('mysql', resource_group, server)
        self._test_parameter_mgmt('mysql', resource_group, server)
        self._test_database_mgmt('mysql', resource_group, server)
        self._test_log_file_mgmt('mysql', resource_group, server)

    def _test_firewall_rule_mgmt(self, database_engine, resource_group, server):

        firewall_rule_name = 'firewall_test_rule'
        start_ip_address = '10.10.10.10'
        end_ip_address = '12.12.12.12'
        firewall_rule_checks = [JMESPathCheck('name', firewall_rule_name),
                                JMESPathCheck('endIpAddress', end_ip_address),
                                JMESPathCheck('startIpAddress', start_ip_address)]

        self.cmd('{} flexible-server firewall-rule create -g {} --name {} --rule-name {} '
                 '--start-ip-address {} --end-ip-address {} '
                 .format(database_engine, resource_group, server, firewall_rule_name, start_ip_address, end_ip_address),
                 checks=firewall_rule_checks)

        self.cmd('{} flexible-server firewall-rule show -g {} --name {} --rule-name {} '
                 .format(database_engine, resource_group, server, firewall_rule_name),
                 checks=firewall_rule_checks)

        new_start_ip_address = '9.9.9.9'
        self.cmd('{} flexible-server firewall-rule update -g {} --name {} --rule-name {} --start-ip-address {}'
                 .format(database_engine, resource_group, server, firewall_rule_name, new_start_ip_address),
                 checks=[JMESPathCheck('startIpAddress', new_start_ip_address)])

        new_end_ip_address = '13.13.13.13'
        self.cmd('{} flexible-server firewall-rule update -g {} --name {} --rule-name {} --end-ip-address {}'
                 .format(database_engine, resource_group, server, firewall_rule_name, new_end_ip_address))

        new_firewall_rule_name = 'firewall_test_rule2'
        firewall_rule_checks = [JMESPathCheck('name', new_firewall_rule_name),
                                JMESPathCheck('endIpAddress', end_ip_address),
                                JMESPathCheck('startIpAddress', start_ip_address)]
        self.cmd('{} flexible-server firewall-rule create -g {} -n {} --rule-name {} '
                 '--start-ip-address {} --end-ip-address {} '
                 .format(database_engine, resource_group, server, new_firewall_rule_name, start_ip_address, end_ip_address),
                 checks=firewall_rule_checks)

        self.cmd('{} flexible-server firewall-rule list -g {} -n {}'
                 .format(database_engine, resource_group, server), checks=[JMESPathCheck('length(@)', 2)])

        self.cmd('{} flexible-server firewall-rule delete --rule-name {} -g {} --name {} --yes'
                 .format(database_engine, firewall_rule_name, resource_group, server), checks=NoneCheck())

        self.cmd('{} flexible-server firewall-rule list -g {} --name {}'
                 .format(database_engine, resource_group, server), checks=[JMESPathCheck('length(@)', 1)])

        self.cmd('{} flexible-server firewall-rule delete -g {} -n {} --rule-name {} --yes'
                 .format(database_engine, resource_group, server, new_firewall_rule_name))

        self.cmd('{} flexible-server firewall-rule list -g {} -n {}'
                 .format(database_engine, resource_group, server), checks=NoneCheck())

    def _test_parameter_mgmt(self, database_engine, resource_group, server):

        self.cmd('{} flexible-server parameter list -g {} -s {}'.format(database_engine, resource_group, server), checks=[JMESPathCheck('type(@)', 'array')])

        if database_engine == 'mysql':
            parameter_name = 'wait_timeout'
            default_value = '28800'
            value = '30000'
        elif database_engine == 'postgres':
            parameter_name = 'lock_timeout'
            default_value = '0'
            value = '2000'

        source = 'system-default'
        self.cmd('{} flexible-server parameter show --name {} -g {} -s {}'.format(database_engine, parameter_name, resource_group, server),
                 checks=[JMESPathCheck('defaultValue', default_value),
                         JMESPathCheck('source', source)])

        source = 'user-override'
        self.cmd('{} flexible-server parameter set --name {} -v {} --source {} -s {} -g {}'.format(database_engine, parameter_name, value, source, server, resource_group),
                 checks=[JMESPathCheck('value', value),
                         JMESPathCheck('source', source)])

    def _test_database_mgmt(self, database_engine, resource_group, server):

        database_name = self.create_random_name('database', 20)

        self.cmd('{} flexible-server db create -g {} -s {} -d {}'.format(database_engine, resource_group, server, database_name),
                 checks=[JMESPathCheck('name', database_name)])

        self.cmd('{} flexible-server db show -g {} -s {} -d {}'.format(database_engine, resource_group, server, database_name),
                 checks=[
                     JMESPathCheck('name', database_name),
                     JMESPathCheck('resourceGroup', resource_group)])

        self.cmd('{} flexible-server db list -g {} -s {} '.format(database_engine, resource_group, server),
                 checks=[JMESPathCheck('type(@)', 'array')])

        self.cmd('{} flexible-server db delete -g {} -s {} -d {} --yes'.format(database_engine, resource_group, server, database_name),
                 checks=NoneCheck())

    def _test_log_file_mgmt(self, database_engine, resource_group, server):
        if database_engine == 'mysql':
            # enable logs to be written to a file
            self.cmd('{} flexible-server parameter set -g {} -s {} -n log_output --value FILE'
                     .format(database_engine, resource_group, server))

            # enable slow query log
            config_name = 'slow_query_log'
            new_value = 'ON'

            self.cmd('{} flexible-server parameter set -g {} -s {} -n {} --value {}'
                     .format(database_engine, resource_group, server, config_name, new_value),
                     checks=[
                         JMESPathCheck('name', config_name),
                         JMESPathCheck('value', new_value)])

            # retrieve logs filenames
            result = self.cmd('{} flexible-server server-logs list -g {} -s {} --file-last-written 43800'
                              .format(database_engine, resource_group, server),
                              checks=[
                                  JMESPathCheck('length(@)', 1),
                                  JMESPathCheck('type(@)', 'array')]).get_output_in_json()

            name = result[0]['name']
            self.assertIsNotNone(name)

            # download log
            if name:
                self.cmd('{} flexible-server server-logs download -g {} -s {} -n {}'
                         .format(database_engine, resource_group, server, name))
                
                # assert that log file was downloaded successfully and delete it
                self.assertTrue(os.path.isfile(name))
                os.remove(name)


class FlexibleServerValidatorScenarioTest(ScenarioTest):

    postgres_location = 'eastus'

    @AllowLargeResponse()
    @ResourceGroupPreparer(location=postgres_location)
    def test_postgres_flexible_server_mgmt_create_validator(self, resource_group):
        self._test_mgmt_create_validator('postgres', resource_group)

    @pytest.mark.mysql_regression
    @AllowLargeResponse()
    @ResourceGroupPreparer(location=mysql_location)
    def test_mysql_flexible_server_mgmt_create_validator(self, resource_group):
        self._test_mgmt_create_validator('mysql', resource_group)

    @AllowLargeResponse()
    @ResourceGroupPreparer(location=postgres_location)
    def test_postgres_flexible_server_mgmt_update_validator(self, resource_group):
        self._test_mgmt_update_validator('postgres', resource_group)

    @pytest.mark.mysql_regression
    @AllowLargeResponse()
    @ResourceGroupPreparer(location=mysql_location)
    def test_mysql_flexible_server_mgmt_update_validator(self, resource_group):
        self._test_mgmt_update_validator('mysql', resource_group)

    def _test_mgmt_create_validator(self, database_engine, resource_group):

        RANDOM_VARIABLE_MAX_LENGTH = 30
        if database_engine == 'postgres':
            location = self.postgres_location
        elif database_engine == 'mysql':
            location = mysql_location
        server_name = self.create_random_name(SERVER_NAME_PREFIX, SERVER_NAME_MAX_LENGTH)
        invalid_version = self.create_random_name('version', RANDOM_VARIABLE_MAX_LENGTH)
        invalid_sku_name = self.create_random_name('sku_name', RANDOM_VARIABLE_MAX_LENGTH)
        invalid_tier = self.create_random_name('tier', RANDOM_VARIABLE_MAX_LENGTH)
        valid_tier = 'GeneralPurpose'
        invalid_backup_retention = 40
        ha_value = 'ZoneRedundant'

        # Create
        if database_engine == 'postgres':
            self.cmd('{} flexible-server create -g {} -n Wrongserver.Name -l {}'.format(
                    database_engine, resource_group, location),
                    expect_failure=True)

        self.cmd('{} flexible-server create -g {} -n {} -l {} --tier {}'.format(
                 database_engine, resource_group, server_name, location, invalid_tier),
                 expect_failure=True)

        self.cmd('{} flexible-server create -g {} -n {} -l {} --version {}'.format(
                 database_engine, resource_group, server_name, location, invalid_version),
                 expect_failure=True)

        self.cmd('{} flexible-server create -g {} -n {} -l {} --tier {} --sku-name {}'.format(
                 database_engine, resource_group, server_name, location, valid_tier, invalid_sku_name),
                 expect_failure=True)

        self.cmd('{} flexible-server create -g {} -n {} -l {} --backup-retention {}'.format(
                 database_engine, resource_group, server_name, location, invalid_backup_retention),
                 expect_failure=True)

        self.cmd('{} flexible-server create -g {} -n {} -l centraluseuap --high-availability {} '.format(
                 database_engine, resource_group, server_name, ha_value),
                 expect_failure=True)

        # high availability validator
        self.cmd('{} flexible-server create -g {} -n {} -l {} --tier Burstable --sku-name Standard_B1ms --high-availability {}'.format(
                 database_engine, resource_group, server_name, location, ha_value),
                 expect_failure=True)

        self.cmd('{} flexible-server create -g {} -n {} -l centraluseuap --tier GeneralPurpose --sku-name Standard_D2s_v3 --high-availability {}'.format(
                 database_engine, resource_group, server_name, ha_value), # single availability zone location
                 expect_failure=True)

        self.cmd('{} flexible-server create -g {} -n {} -l {} --tier GeneralPurpose --sku-name Standard_D2s_v3 --high-availability {} --zone 1 --standby-zone 1'.format(
                 database_engine, resource_group, server_name, location, ha_value), # single availability zone location
                 expect_failure=True)

        if database_engine == 'mysql':
            self.cmd('{} flexible-server create -g {} -n {} -l {} --tier GeneralPurpose --sku-name Standard_D2s_v3 --high-availability {} --storage-auto-grow Disabled'.format(
                    database_engine, resource_group, server_name, location, ha_value), # auto grow must be enabled for high availability server
                    expect_failure=True)

        # Network
        self.cmd('{} flexible-server create -g {} -n {} -l {} --vnet testvnet --subnet testsubnet --public-access All'.format(
                 database_engine, resource_group, server_name, location),
                 expect_failure=True)

        self.cmd('{} flexible-server create -g {} -n {} -l {} --subnet testsubnet'.format(
                 database_engine, resource_group, server_name, location),
                 expect_failure=True)

        self.cmd('{} flexible-server create -g {} -n {} -l {} --public-access 12.0.0.0-10.0.0.0.0'.format(
                 database_engine, resource_group, server_name, location),
                 expect_failure=True)

        if database_engine == 'postgres':
            invalid_storage_size = 60
        elif database_engine == 'mysql':
            invalid_storage_size = 10
        self.cmd('{} flexible-server create -g {} -l {} --storage-size {} --public-access none'.format(
                 database_engine, resource_group, location, invalid_storage_size),
                 expect_failure=True)

    def _test_mgmt_update_validator(self, database_engine, resource_group):
        RANDOM_VARIABLE_MAX_LENGTH = 30
        server_name = self.create_random_name(SERVER_NAME_PREFIX, SERVER_NAME_MAX_LENGTH)
        invalid_version = self.create_random_name('version', RANDOM_VARIABLE_MAX_LENGTH)
        invalid_sku_name = self.create_random_name('sku_name', RANDOM_VARIABLE_MAX_LENGTH)
        invalid_tier = self.create_random_name('tier', RANDOM_VARIABLE_MAX_LENGTH)
        valid_tier = 'GeneralPurpose'
        invalid_backup_retention = 40
        if database_engine == 'postgres':
            version = 12
            storage_size = 128
            location = self.postgres_location
        elif database_engine == 'mysql':
            version = 5.7
            storage_size = 32
            location = mysql_location
        tier = 'Burstable'
        sku_name = 'Standard_B1ms'
        backup_retention = 10

        list_checks = [JMESPathCheck('name', server_name),
                       JMESPathCheck('resourceGroup', resource_group),
                       JMESPathCheck('sku.name', sku_name),
                       JMESPathCheck('sku.tier', tier),
                       JMESPathCheck('version', version),
                       JMESPathCheck('storage.storageSizeGb', storage_size),
                       JMESPathCheck('backup.backupRetentionDays', backup_retention)]

        self.cmd('{} flexible-server create -g {} -n {} -l {} --tier {} --version {} --sku-name {} --storage-size {} --backup-retention {} --public-access none'
                 .format(database_engine, resource_group, server_name, location, tier, version, sku_name, storage_size, backup_retention))
        self.cmd('{} flexible-server show -g {} -n {}'.format(database_engine, resource_group, server_name), checks=list_checks)

        invalid_tier = 'GeneralPurpose'
        self.cmd('{} flexible-server update -g {} -n {} --tier {}'.format(
                 database_engine, resource_group, server_name, invalid_tier), # can't update to this tier because of the instance's sku name
                 expect_failure=True)

        self.cmd('{} flexible-server update -g {} -n {} --tier {} --sku-name {}'.format(
                 database_engine, resource_group, server_name, valid_tier, invalid_sku_name),
                 expect_failure=True)

        if database_engine == 'postgres':
            invalid_storage_size = 64
        else:
            invalid_storage_size = 30
        self.cmd('{} flexible-server update -g {} -n {} --storage-size {}'.format(
                 database_engine, resource_group, server_name, invalid_storage_size), #cannot update to smaller size
                 expect_failure=True)

        self.cmd('{} flexible-server update -g {} -n {} --backup-retention {}'.format(
                 database_engine, resource_group, server_name, invalid_backup_retention),
                 expect_failure=True)

        ha_value = 'ZoneRedundant'
        self.cmd('{} flexible-server update -g {} -n {} --high-availability {}'.format(
                 database_engine, resource_group, server_name, ha_value),
                 expect_failure=True)

        self.cmd('{} flexible-server delete -g {} -n {} --yes'.format(
                 database_engine, resource_group, server_name), checks=NoneCheck())


class FlexibleServerReplicationMgmtScenarioTest(ScenarioTest):  # pylint: disable=too-few-public-methods

    postgres_location = 'eastus'

    @AllowLargeResponse()
    @ResourceGroupPreparer(location=postgres_location)
    def test_postgres_flexible_server_replica_mgmt(self, resource_group):
        self._test_flexible_server_replica_mgmt('postgres', resource_group, True)
        self._test_flexible_server_replica_mgmt('postgres', resource_group, False)

    @pytest.mark.mysql_regression
    @AllowLargeResponse()
    @ResourceGroupPreparer(location=mysql_location)
    def test_mysql_flexible_server_replica_mgmt(self, resource_group):
        self._test_flexible_server_replica_mgmt('mysql', resource_group, False)

    @pytest.mark.mysql_regression
    @AllowLargeResponse()
    @ResourceGroupPreparer()
    def test_mysql_flexible_server_cross_region_replica_mgmt(self, resource_group):
        self._test_flexible_server_cross_region_replica_mgmt('mysql', resource_group)
    
    def _test_flexible_server_cross_region_replica_mgmt(self, database_engine, resource_group):
        # create a server
        master_location = mysql_paired_location
        replica_location = mysql_location
        primary_role = 'None'
        replica_role = 'Replica'
        private_dns_param = 'privateDnsZoneResourceId' if database_engine == 'mysql' else 'privateDnsZoneArmResourceId'

        master_server = self.create_random_name(SERVER_NAME_PREFIX, 32)
        replicas = [self.create_random_name(F'azuredbclirep{i+1}', SERVER_NAME_MAX_LENGTH) for i in range(2)]
        self.cmd('{} flexible-server create -g {} --name {} -l {} --storage-size {} --tier GeneralPurpose --sku-name {} --public-access none'
                 .format(database_engine, resource_group, master_server, master_location, 32, mysql_general_purpose_sku))
        result = self.cmd('{} flexible-server show -g {} --name {} '
                          .format(database_engine, resource_group, master_server),
                          checks=[JMESPathCheck('replicationRole', primary_role)]).get_output_in_json()

        # test replica create for public access
        replica_result = self.cmd('{} flexible-server replica create -g {} --replica-name {} --source-server {} --location {}'
                 .format(database_engine, resource_group, replicas[0], result['id'], replica_location),
                 checks=[
                     JMESPathCheck('name', replicas[0]),
                     JMESPathCheck('resourceGroup', resource_group),
                     JMESPathCheck('sku.tier', result['sku']['tier']),
                     JMESPathCheck('sku.name', result['sku']['name']),
                     JMESPathCheck('replicationRole', replica_role),
                     JMESPathCheck('sourceServerResourceId', result['id']),
                     JMESPathCheck('replicaCapacity', '0')]).get_output_in_json()
                     #JMESPathCheck('network.publicNetworkAccess', 'Enabled')]).get_output_in_json()
        self.assertEqual(str(replica_result['location']).replace(' ', '').lower(), replica_location)

        # test replica create for private access
        replica_vnet = self.create_random_name('VNET', SERVER_NAME_MAX_LENGTH)
        replica_subnet = self.create_random_name('SUBNET', SERVER_NAME_MAX_LENGTH)
        private_dns_zone = '{}.private.{}.database.azure.com'.format(replicas[1], database_engine)

        self.cmd('network vnet create -g {} -l {} -n {} --address-prefixes 172.1.0.0/16'
                 .format(resource_group, replica_location, replica_vnet))
        subnet = self.cmd('network vnet subnet create -g {} -n {} --vnet-name {} --address-prefixes 172.1.0.0/24'
                          .format(resource_group, replica_subnet, replica_vnet)).get_output_in_json()
        self.cmd('network private-dns zone create -g {} --name {}'.format(resource_group, private_dns_zone))

        replica_result = self.cmd('{} flexible-server replica create -g {} --replica-name {} --source-server {} --location {} --subnet {} --private-dns-zone {}'
                 .format(database_engine, resource_group, replicas[1], result['id'], replica_location, subnet["id"], private_dns_zone),
                 checks=[
                     JMESPathCheck('name', replicas[1]),
                     JMESPathCheck('resourceGroup', resource_group),
                     JMESPathCheck('sku.tier', result['sku']['tier']),
                     JMESPathCheck('sku.name', result['sku']['name']),
                     JMESPathCheck('replicationRole', replica_role),
                     JMESPathCheck('sourceServerResourceId', result['id']),
                     JMESPathCheck('replicaCapacity', '0'),
                     #JMESPathCheck('network.publicNetworkAccess', 'Disabled'),
                     JMESPathCheck('network.delegatedSubnetResourceId', '/subscriptions/{}/resourceGroups/{}/providers/Microsoft.Network/virtualNetworks/{}/subnets/{}'
                                   .format(self.get_subscription_id(), resource_group, replica_vnet, replica_subnet)),
                     JMESPathCheck('network.{}'.format(private_dns_param), '/subscriptions/{}/resourceGroups/{}/providers/Microsoft.Network/privateDnsZones/{}'
                                   .format(self.get_subscription_id(), resource_group, private_dns_zone))]).get_output_in_json()
        self.assertEqual(str(replica_result['location']).replace(' ', '').lower(), replica_location)

        # test replica list
        self.cmd('{} flexible-server replica list -g {} --name {}'
                 .format(database_engine, resource_group, master_server),
                 checks=[JMESPathCheck('length(@)', 2)])

        # clean up servers
        self.cmd('{} flexible-server delete -g {} --name {} --yes'
                 .format(database_engine, resource_group, replicas[0]), checks=NoneCheck())
        self.cmd('{} flexible-server delete -g {} --name {} --yes'
                 .format(database_engine, resource_group, replicas[1]), checks=NoneCheck())
        self.cmd('{} flexible-server delete -g {} --name {} --yes'
                    .format(database_engine, resource_group, master_server), checks=NoneCheck())


    def _test_flexible_server_replica_mgmt(self, database_engine, resource_group, vnet_enabled):
        if database_engine == 'postgres':
            location = self.postgres_location
            primary_role = 'Primary'
            replica_role = 'AsyncReplica'
            public_access_arg = ''
            public_access_check = []
        else:
            location = mysql_location
            primary_role = 'None'
            replica_role = 'Replica'
            public_access_arg = '--public-access Disabled'
            public_access_check = [JMESPathCheck('network.publicNetworkAccess', 'Disabled')]

        master_server = self.create_random_name(SERVER_NAME_PREFIX, 32)
        replicas = [self.create_random_name(F'azuredbclirep{i+1}', SERVER_NAME_MAX_LENGTH) for i in range(2)]

        if vnet_enabled:
            master_vnet = self.create_random_name('VNET', SERVER_NAME_MAX_LENGTH)
            master_subnet = self.create_random_name('SUBNET', SERVER_NAME_MAX_LENGTH)
            master_vnet_args = F'--vnet {master_vnet} --subnet {master_subnet} --address-prefixes 10.0.0.0/16 --subnet-prefixes 10.0.0.0/24'
            master_vnet_check = [JMESPathCheck('network.delegatedSubnetResourceId', F'/subscriptions/{self.get_subscription_id()}/resourceGroups/{resource_group}/providers/Microsoft.Network/virtualNetworks/{master_vnet}/subnets/{master_subnet}')]
            replica_subnet = [self.create_random_name(F'SUBNET{i+1}', SERVER_NAME_MAX_LENGTH) for i in range(2)]
            replica_vnet_args = [F'--vnet {master_vnet} --subnet {replica_subnet[i]} --address-prefixes 10.0.0.0/16 --subnet-prefixes 10.0.{i+1}.0/24 --yes' for i in range(2)]
            replica_vnet_check = [[JMESPathCheck('network.delegatedSubnetResourceId', F'/subscriptions/{self.get_subscription_id()}/resourceGroups/{resource_group}/providers/Microsoft.Network/virtualNetworks/{master_vnet}/subnets/{replica_subnet[i]}')] for i in range(2)]
        else:
            master_vnet_args = '--public-access none'
            master_vnet_check = []
            replica_vnet_args = [''] * 2
            replica_vnet_check = [[]] * 2

        # create a server
        self.cmd('{} flexible-server create -g {} --name {} -l {} --storage-size {} {} --tier GeneralPurpose --sku-name {} --yes'
                 .format(database_engine, resource_group, master_server, location, 256, master_vnet_args, mysql_general_purpose_sku))
        result = self.cmd('{} flexible-server show -g {} --name {} '
                          .format(database_engine, resource_group, master_server),
                          checks=[JMESPathCheck('replicationRole', primary_role)] + master_vnet_check).get_output_in_json()
        
        # test replica create
        self.cmd('{} flexible-server replica create -g {} --replica-name {} --source-server {} --zone 2 {} {}'
                 .format(database_engine, resource_group, replicas[0], result['id'], replica_vnet_args[0], public_access_arg),
                 checks=[
                     JMESPathCheck('name', replicas[0]),
                     JMESPathCheck('availabilityZone', 2),
                     JMESPathCheck('resourceGroup', resource_group),
                     JMESPathCheck('sku.tier', result['sku']['tier']),
                     JMESPathCheck('sku.name', result['sku']['name']),
                     JMESPathCheck('replicationRole', replica_role),
                     JMESPathCheck('sourceServerResourceId', result['id']),
                     JMESPathCheck('replicaCapacity', '0')] + replica_vnet_check[0] + public_access_check)

        # test replica list
        self.cmd('{} flexible-server replica list -g {} --name {}'
                 .format(database_engine, resource_group, master_server),
                 checks=[JMESPathCheck('length(@)', 1)])

        if database_engine == 'mysql':
            # autogrow disable fail for replica server
            self.cmd('{} flexible-server update -g {} -n {} --storage-auto-grow Disabled'.format(
                    database_engine, resource_group, master_server),
                    expect_failure=True)

        # test replica stop
        self.cmd('{} flexible-server replica stop-replication -g {} --name {} --yes'
                 .format(database_engine, resource_group, replicas[0]),
                 checks=[
                     JMESPathCheck('name', replicas[0]),
                     JMESPathCheck('resourceGroup', resource_group),
                     JMESPathCheck('replicationRole', primary_role),
                     JMESPathCheck('sourceServerResourceId', 'None'),
                     JMESPathCheck('replicaCapacity', result['replicaCapacity'])])

        # test show server with replication info, master becomes normal server
        self.cmd('{} flexible-server show -g {} --name {}'
                 .format(database_engine, resource_group, master_server),
                 checks=[
                     JMESPathCheck('replicationRole', primary_role),
                     JMESPathCheck('sourceServerResourceId', 'None'),
                     JMESPathCheck('replicaCapacity', result['replicaCapacity'])])

        # test delete master server
        self.cmd('{} flexible-server replica create -g {} --replica-name {} --source-server {} {}'
                .format(database_engine, resource_group, replicas[1], result['id'], replica_vnet_args[1]),
                checks=[
                    JMESPathCheck('name', replicas[1]),
                    JMESPathCheck('resourceGroup', resource_group),
                    JMESPathCheck('sku.name', result['sku']['name']),
                    JMESPathCheck('replicationRole', replica_role),
                    JMESPathCheck('sourceServerResourceId', result['id']),
                    JMESPathCheck('replicaCapacity', '0')] + replica_vnet_check[1])

        if database_engine == 'mysql':
            self.cmd('{} flexible-server delete -g {} --name {} --yes'
                    .format(database_engine, resource_group, master_server), checks=NoneCheck())

            self.cmd('{} flexible-server wait -g {} --name {} --custom "{}"'
                    .format(database_engine, resource_group, replicas[1], F"replicationRole=='{primary_role}'"))

            # test show server with replication info, replica was auto stopped after master server deleted
            self.cmd('{} flexible-server show -g {} --name {}'
                    .format(database_engine, resource_group, replicas[1]),
                    checks=[
                        JMESPathCheck('replicationRole', primary_role),
                        JMESPathCheck('sourceServerResourceId', 'None'),
                        JMESPathCheck('replicaCapacity', result['replicaCapacity'])])
        else:
            # in postgres we can't delete master server if it has replicas
            self.cmd('{} flexible-server delete -g {} --name {} --yes'
                     .format(database_engine, resource_group, master_server),
                     expect_failure=True)

            # delete replica server first
            self.cmd('{} flexible-server delete -g {} --name {} --yes'
                     .format(database_engine, resource_group, replicas[1]))

            # now we can delete master server
            self.cmd('{} flexible-server delete -g {} --name {} --yes'
                     .format(database_engine, resource_group, master_server))

        # clean up servers
        self.cmd('{} flexible-server delete -g {} --name {} --yes'
                 .format(database_engine, resource_group, replicas[0]), checks=NoneCheck())
        self.cmd('{} flexible-server delete -g {} --name {} --yes'
                 .format(database_engine, resource_group, replicas[1]), checks=NoneCheck())


class FlexibleServerVnetMgmtScenarioTest(ScenarioTest):

    postgres_location = 'eastus'

    @AllowLargeResponse()
    @ResourceGroupPreparer(location=postgres_location)
    def test_postgres_flexible_server_vnet_mgmt_supplied_subnetid(self, resource_group):
        # Provision a server with supplied Subnet ID that exists, where the subnet is not delegated
        self._test_flexible_server_vnet_mgmt_existing_supplied_subnetid('postgres', resource_group)

    @pytest.mark.mysql_regression
    @AllowLargeResponse()
    @ResourceGroupPreparer(location=mysql_location)
    def test_mysql_flexible_server_vnet_mgmt_supplied_subnetid(self, resource_group):
        # Provision a server with supplied Subnet ID that exists, where the subnet is not delegated
        self._test_flexible_server_vnet_mgmt_existing_supplied_subnetid('mysql', resource_group)

    @AllowLargeResponse()
    @ResourceGroupPreparer(location=postgres_location)
    def test_postgres_flexible_server_vnet_mgmt_supplied_vname_and_subnetname(self, resource_group):
        self._test_flexible_server_vnet_mgmt_supplied_vname_and_subnetname('postgres', resource_group)

    @pytest.mark.mysql_regression
    @AllowLargeResponse()
    @ResourceGroupPreparer(location=mysql_location)
    def test_mysql_flexible_server_vnet_mgmt_supplied_vname_and_subnetname(self, resource_group):
        self._test_flexible_server_vnet_mgmt_supplied_vname_and_subnetname('mysql', resource_group)

    @AllowLargeResponse()
    @ResourceGroupPreparer(location=postgres_location, parameter_name='resource_group_1')
    @ResourceGroupPreparer(location=postgres_location, parameter_name='resource_group_2')
    def test_postgres_flexible_server_vnet_mgmt_supplied_subnet_id_in_different_rg(self, resource_group_1, resource_group_2):
        self._test_flexible_server_vnet_mgmt_supplied_subnet_id_in_different_rg('postgres', resource_group_1, resource_group_2)

    @pytest.mark.mysql_regression
    @AllowLargeResponse()
    @ResourceGroupPreparer(location=mysql_location, parameter_name='resource_group_1')
    @ResourceGroupPreparer(location=mysql_location, parameter_name='resource_group_2')
    def test_mysql_flexible_server_vnet_mgmt_supplied_subnet_id_in_different_rg(self, resource_group_1, resource_group_2):
        self._test_flexible_server_vnet_mgmt_supplied_subnet_id_in_different_rg('mysql', resource_group_1, resource_group_2)

    @AllowLargeResponse()
    @ResourceGroupPreparer(location=postgres_location)
    def test_flexible_server_vnet_mgmt_prepare_private_network_vname_and_subnetname(self, resource_group):
        self._test_flexible_server_vnet_mgmt_prepare_private_network_vname_and_subnetname(resource_group)

    @AllowLargeResponse()
    @ResourceGroupPreparer(location=postgres_location)
    def test_flexible_server_vnet_mgmt_prepare_private_network_vnet(self, resource_group):
        self._test_flexible_server_vnet_mgmt_prepare_private_network_vnet(resource_group)

    @AllowLargeResponse()
    @ResourceGroupPreparer(location=postgres_location)
    def test_flexible_server_vnet_mgmt_prepare_private_network_subnet(self, resource_group):
        self._test_flexible_server_vnet_mgmt_prepare_private_network_subnet(resource_group)

    @AllowLargeResponse()
    @ResourceGroupPreparer(location=postgres_location)
    def test_flexible_server_vnet_mgmt_validator(self, resource_group):
        self._test_flexible_server_vnet_mgmt_validator(resource_group)
  
    @pytest.mark.mysql_regression
    @AllowLargeResponse()
    @ResourceGroupPreparer(location=mysql_location)
    def test_mysql_flexible_server_public_access_custom(self, resource_group):
        self._test_mysql_flexible_server_public_access_custom('mysql', resource_group)

    @pytest.mark.mysql_regression
    @AllowLargeResponse()
    @ResourceGroupPreparer(location=mysql_location)
    def test_mysql_flexible_server_public_access_restore(self, resource_group):
        self._test_mysql_flexible_server_public_access_restore('mysql', resource_group)

    @pytest.mark.mysql_regression
    @AllowLargeResponse()
    @ResourceGroupPreparer(location=mysql_location)
    def test_mysql_flexible_server_public_access_georestore(self, resource_group):
        self._test_mysql_flexible_server_public_access_georestore('mysql', resource_group)
    
    def _test_mysql_flexible_server_public_access_georestore(self, database_engine, resource_group):
        location = 'northeurope'
        paired_location = 'westeurope'
        server_name_soure_restore = self.create_random_name(SERVER_NAME_PREFIX, SERVER_NAME_MAX_LENGTH)
        server_name_target_restore = self.create_random_name(SERVER_NAME_PREFIX, SERVER_NAME_MAX_LENGTH)
        api_version = '2022-09-30-preview'

         #Test restore server
        result = self.cmd('{} flexible-server create --geo-redundant-backup Enabled --public-access Enabled -g {} -n {} -l {} --iops 50 --storage-size 100 --sku-name Standard_B1ms --tier Burstable'
                 .format(database_engine, resource_group, server_name_soure_restore, location)).get_output_in_json()
        
        restore_server = self.cmd('resource show --id {} --api-version {}'.format(result['id'], api_version)).get_output_in_json()
        
        print(restore_server)
        current_time = datetime.utcnow().replace(tzinfo=tzutc()).isoformat()
        earliest_restore_time = restore_server['properties']['backup']['earliestRestoreDate']
        seconds_to_wait = (parser.isoparse(earliest_restore_time) - parser.isoparse(current_time)).total_seconds()
        print(current_time)
        print(seconds_to_wait)
        time.sleep(max(0, seconds_to_wait) + 180)

        target_server = self.cmd('{} flexible-server geo-restore -g {} -n {} --source-server {} --public-access Disabled --location {}'
                 .format(database_engine, resource_group, server_name_target_restore, server_name_soure_restore, paired_location)).get_output_in_json()

        self.cmd('resource show --id {} --api-version {}'.format(target_server['id'], api_version),
                          checks=[JMESPathCheck('properties.network.publicNetworkAccess', 'Disabled')])

    def _test_mysql_flexible_server_public_access_restore(self, database_engine, resource_group):
        location = 'northeurope'
        server_name_soure_restore = self.create_random_name(SERVER_NAME_PREFIX, SERVER_NAME_MAX_LENGTH)
        server_name_target_restore = self.create_random_name(SERVER_NAME_PREFIX, SERVER_NAME_MAX_LENGTH)
        api_version = '2022-09-30-preview'

         #Test restore server
        result = self.cmd('{} flexible-server create --public-access Enabled -g {} -n {} -l {} --iops 50 --storage-size 100 --sku-name Standard_B1ms --tier Burstable'
                 .format(database_engine, resource_group, server_name_soure_restore, location)).get_output_in_json()
        
        restore_server = self.cmd('resource show --id {} --api-version {}'.format(result['id'], api_version)).get_output_in_json()
        
        current_time = datetime.utcnow().replace(tzinfo=tzutc()).isoformat()
        earliest_restore_time = restore_server['properties']['backup']['earliestRestoreDate']
        seconds_to_wait = (parser.isoparse(earliest_restore_time) - parser.isoparse(current_time)).total_seconds()
        print(current_time)
        print(seconds_to_wait)
        time.sleep(max(0, seconds_to_wait) + 180)

        target_server = self.cmd('{} flexible-server restore -g {} -n {} --source-server {} --public-access Disabled'
                 .format(database_engine, resource_group, server_name_target_restore, server_name_soure_restore)).get_output_in_json()

        self.cmd('resource show --id {} --api-version {}'.format(target_server['id'], api_version),
                          checks=[JMESPathCheck('properties.network.publicNetworkAccess', 'Disabled')])

    def _test_mysql_flexible_server_public_access_custom(self, database_engine, resource_group):

        location = mysql_paired_location
        server_name = self.create_random_name(SERVER_NAME_PREFIX, SERVER_NAME_MAX_LENGTH)
        server_name_2 = self.create_random_name(SERVER_NAME_PREFIX + '2', SERVER_NAME_MAX_LENGTH)
        api_version = '2022-09-30-preview'

        #Test create server with public access enabled
        result = self.cmd('{} flexible-server create --public-access Enabled -g {} -n {} -l {} --iops 50 --storage-size 100 --sku-name Standard_B1ms --tier Burstable'
                 .format(database_engine, resource_group, server_name, location)).get_output_in_json()

        self.cmd('resource show --id {} --api-version {}'.format(result['id'], api_version),
                          checks=[JMESPathCheck('properties.network.publicNetworkAccess', 'Enabled')])

        #Test create server with public access disabled
        result = self.cmd('{} flexible-server create --public-access Disabled -g {} -n {} -l {} --iops 50 --storage-size 100 --sku-name Standard_B1ms --tier Burstable'
                 .format(database_engine, resource_group, server_name_2, location)).get_output_in_json()

        self.cmd('resource show --id {} --api-version {}'.format(result['id'], api_version),
                          checks=[JMESPathCheck('properties.network.publicNetworkAccess', 'Disabled')])
        
        #Test update server
        self.cmd('{} flexible-server update -g {} -n {} --public-access Enabled'
                 .format(database_engine, resource_group, server_name_2))
        
        # delete server
        self.cmd('{} flexible-server delete -g {} -n {} --yes'.format(database_engine, resource_group, server_name))
        self.cmd('{} flexible-server delete -g {} -n {} --yes'.format(database_engine, resource_group, server_name_2))

    def _test_flexible_server_vnet_mgmt_existing_supplied_subnetid(self, database_engine, resource_group):

        # flexible-server create
        if self.cli_ctx.local_context.is_on:
            self.cmd('config param-persist off')

        if database_engine == 'postgres':
            location = self.postgres_location
            private_dns_zone_key = "privateDnsZoneArmResourceId"
        elif database_engine == 'mysql':
            location = mysql_location
            private_dns_zone_key = "privateDnsZoneResourceId"

        server_name = self.create_random_name(SERVER_NAME_PREFIX, SERVER_NAME_MAX_LENGTH)
        private_dns_zone = "testdnszone0.private.{}.database.azure.com".format(database_engine)

        # Scenario : Provision a server with supplied Subnet ID that exists, where the subnet is not delegated
        vnet_name = 'testvnet'
        subnet_name = 'testsubnet'
        address_prefix = '172.1.0.0/16'
        subnet_prefix = '172.1.0.0/24'
        self.cmd('network vnet create -g {} -l {} -n {} --address-prefixes {} --subnet-name {} --subnet-prefixes {}'.format(
                 resource_group, location, vnet_name, address_prefix, subnet_name, subnet_prefix))
        subnet_id = self.cmd('network vnet subnet show -g {} -n {} --vnet-name {}'.format(resource_group, subnet_name, vnet_name)).get_output_in_json()['id']

        # create server - Delegation should be added.
        self.cmd('{} flexible-server create -g {} -n {} --subnet {} -l {} --private-dns-zone {} --yes'
                 .format(database_engine, resource_group, server_name, subnet_id, location, private_dns_zone))

        # flexible-server show to validate delegation is added to both the created server
        show_result_1 = self.cmd('{} flexible-server show -g {} -n {}'
                                 .format(database_engine, resource_group, server_name)).get_output_in_json()
        self.assertEqual(show_result_1['network']['delegatedSubnetResourceId'], subnet_id)
        if database_engine == 'postgres':
            self.assertEqual(show_result_1['network'][private_dns_zone_key],
                            '/subscriptions/{}/resourceGroups/{}/providers/Microsoft.Network/privateDnsZones/{}'.format(
                                self.get_subscription_id(), resource_group, private_dns_zone))
        # delete server
        self.cmd('{} flexible-server delete -g {} -n {} --yes'.format(database_engine, resource_group, server_name))

        time.sleep(15 * 60)

    def _test_flexible_server_vnet_mgmt_supplied_vname_and_subnetname(self, database_engine, resource_group):

        # flexible-server create
        if self.cli_ctx.local_context.is_on:
            self.cmd('config param-persist off')

        vnet_name = 'clitestvnet3'
        subnet_name = 'clitestsubnet3'
        vnet_name_2 = 'clitestvnet4'
        address_prefix = '13.0.0.0/16'

        if database_engine == 'postgres':
            location = self.postgres_location
            private_dns_zone_key = "privateDnsZoneArmResourceId"
        elif database_engine == 'mysql':
            location = mysql_location
            private_dns_zone_key = "privateDnsZoneResourceId"

        # flexible-servers
        servers = [self.create_random_name(SERVER_NAME_PREFIX, SERVER_NAME_MAX_LENGTH) + database_engine, self.create_random_name(SERVER_NAME_PREFIX, SERVER_NAME_MAX_LENGTH) + database_engine]
        private_dns_zone_1 = "testdnszone3.private.{}.database.azure.com".format(database_engine)
        private_dns_zone_2 = "testdnszone4.private.{}.database.azure.com".format(database_engine)
        # Case 1 : Provision a server with supplied Vname and subnet name that exists.

        # create vnet and subnet. When vnet name is supplied, the subnet created will be given the default name.
        self.cmd('network vnet create -n {} -g {} -l {} --address-prefix {}'
                  .format(vnet_name, resource_group, location, address_prefix))

        # create server - Delegation should be added.
        self.cmd('{} flexible-server create -g {} -n {} --vnet {} -l {} --subnet {} --private-dns-zone {} --yes'
                 .format(database_engine, resource_group, servers[0], vnet_name, location, subnet_name, private_dns_zone_1))

        # Case 2 : Provision a server with a supplied Vname and subnet name that does not exist.
        self.cmd('{} flexible-server create -g {} -n {} -l {} --vnet {} --private-dns-zone {} --yes'
                 .format(database_engine, resource_group, servers[1], location, vnet_name_2, private_dns_zone_2))

        # flexible-server show to validate delegation is added to both the created server
        show_result_1 = self.cmd('{} flexible-server show -g {} -n {}'
                                 .format(database_engine, resource_group, servers[0])).get_output_in_json()

        show_result_2 = self.cmd('{} flexible-server show -g {} -n {}'
                                 .format(database_engine, resource_group, servers[1])).get_output_in_json()

        self.assertEqual(show_result_1['network']['delegatedSubnetResourceId'],
                         '/subscriptions/{}/resourceGroups/{}/providers/Microsoft.Network/virtualNetworks/{}/subnets/{}'.format(
                         self.get_subscription_id(), resource_group, vnet_name, subnet_name))

        self.assertEqual(show_result_2['network']['delegatedSubnetResourceId'],
                         '/subscriptions/{}/resourceGroups/{}/providers/Microsoft.Network/virtualNetworks/{}/subnets/{}'.format(
                         self.get_subscription_id(), resource_group, vnet_name_2, 'Subnet' + servers[1]))

        if database_engine == 'postgres':
            self.assertEqual(show_result_1['network'][private_dns_zone_key],
                            '/subscriptions/{}/resourceGroups/{}/providers/Microsoft.Network/privateDnsZones/{}'.format(
                                self.get_subscription_id(), resource_group, private_dns_zone_1))

            self.assertEqual(show_result_2['network'][private_dns_zone_key],
                            '/subscriptions/{}/resourceGroups/{}/providers/Microsoft.Network/privateDnsZones/{}'.format(
                                self.get_subscription_id(), resource_group, private_dns_zone_2))

        # delete all servers
        self.cmd('{} flexible-server delete -g {} -n {} --yes'.format(database_engine, resource_group, servers[0]),
                 checks=NoneCheck())

        self.cmd('{} flexible-server delete -g {} -n {} --yes'.format(database_engine, resource_group, servers[1]),
                 checks=NoneCheck())

        time.sleep(15 * 60)

    def _test_flexible_server_vnet_mgmt_supplied_subnet_id_in_different_rg(self, database_engine, resource_group_1, resource_group_2):
        # flexible-server create
        if self.cli_ctx.local_context.is_on:
            self.cmd('config param-persist off')

        if database_engine == 'postgres':
            location = self.postgres_location
            private_dns_zone_key = "privateDnsZoneArmResourceId"
        elif database_engine == 'mysql':
            location = mysql_location
            private_dns_zone_key = "privateDnsZoneResourceId"

        vnet_name = 'clitestvnet5'
        subnet_name = 'clitestsubnet5'
        address_prefix = '10.10.0.0/16'
        subnet_prefix = '10.10.0.0/24'

        # flexible-servers
        server_name = self.create_random_name(SERVER_NAME_PREFIX, SERVER_NAME_MAX_LENGTH)
        private_dns_zone = "testdnszone5.private.{}.database.azure.com".format(database_engine)

        # Case 1 : Provision a server with supplied subnetid that exists in a different RG

        # create vnet and subnet.
        vnet_result = self.cmd(
            'network vnet create -n {} -g {} -l {} --address-prefix {} --subnet-name {} --subnet-prefix {}'
            .format(vnet_name, resource_group_1, location, address_prefix, subnet_name,
                    subnet_prefix)).get_output_in_json()

        # create server - Delegation should be added.
        self.cmd('{} flexible-server create -g {} -n {} --subnet {} -l {} --private-dns-zone {} --yes'
                 .format(database_engine, resource_group_2, server_name, vnet_result['newVNet']['subnets'][0]['id'], location, private_dns_zone))

        # flexible-server show to validate delegation is added to both the created server
        show_result_1 = self.cmd('{} flexible-server show -g {} -n {}'
                                 .format(database_engine, resource_group_2, server_name)).get_output_in_json()

        self.assertEqual(show_result_1['network']['delegatedSubnetResourceId'],
                         '/subscriptions/{}/resourceGroups/{}/providers/Microsoft.Network/virtualNetworks/{}/subnets/{}'.format(
                             self.get_subscription_id(), resource_group_1, vnet_name, subnet_name))

        if database_engine == 'postgres':
            self.assertEqual(show_result_1['network'][private_dns_zone_key],
                            '/subscriptions/{}/resourceGroups/{}/providers/Microsoft.Network/privateDnsZones/{}'.format(
                                self.get_subscription_id(), resource_group_1, private_dns_zone))

        # delete all servers
        self.cmd('{} flexible-server delete -g {} -n {} --yes'.format(database_engine, resource_group_2, server_name),
                 checks=NoneCheck())


        # time.sleep(15 * 60)

        # remove delegations from all vnets
        self.cmd('network vnet subnet update -g {} --name {} --vnet-name {} --remove delegations'.format(resource_group_1, subnet_name, vnet_name))
        # remove all vnets
        self.cmd('network vnet delete -g {} -n {}'.format(resource_group_1, vnet_name))

    def _test_flexible_server_vnet_mgmt_prepare_private_network_vname_and_subnetname(self, resource_group):
        server_name = 'vnet-preparer-server'
        delegation_service_name = "Microsoft.DBforPostgreSQL/flexibleServers"
        location = self.postgres_location
        yes = True

        #   Vnet x exist, subnet x exist, address prefixes
        vnet = 'testvnet1'
        subnet = 'testsubnet1'
        vnet_address_pref = '172.1.0.0/16'
        subnet_address_pref = '172.1.0.0/24'
        subnet_id = prepare_private_network(self, resource_group, server_name, vnet, subnet, location, delegation_service_name, vnet_address_pref, subnet_address_pref, yes=yes)
        vnet_id = subnet_id.split('/subnets/')[0]
        self.assertEqual(subnet_id,
                         '/subscriptions/{}/resourceGroups/{}/providers/Microsoft.Network/virtualNetworks/{}/subnets/{}'.format(
                         self.get_subscription_id(), resource_group, vnet, subnet))
        self.cmd('network vnet show --id {}'.format(vnet_id),
                 checks=[StringContainCheck(vnet_address_pref)])
        self.cmd('network vnet subnet show --id {}'.format(subnet_id),
                 checks=[JMESPathCheck('addressPrefix', subnet_address_pref),
                         JMESPathCheck('delegations[0].serviceName', delegation_service_name)])

        #   Vnet exist, subnet x exist, address prefixes
        vnet = 'testvnet1'
        subnet = 'testsubnet2'
        vnet_address_pref = '172.1.0.0/16'
        subnet_address_pref = '172.1.1.0/24'
        subnet_id = prepare_private_network(self, resource_group, server_name, vnet, subnet, location, delegation_service_name, vnet_address_pref, subnet_address_pref, yes=yes)
        vnet_id = subnet_id.split('/subnets/')[0]
        self.assertEqual(subnet_id,
                         '/subscriptions/{}/resourceGroups/{}/providers/Microsoft.Network/virtualNetworks/{}/subnets/{}'.format(
                         self.get_subscription_id(), resource_group, vnet, subnet))
        self.cmd('network vnet show --id {}'.format(vnet_id),
                 checks=[StringContainCheck(vnet_address_pref)])
        self.cmd('network vnet subnet show --id {}'.format(subnet_id),
                 checks=[JMESPathCheck('addressPrefix', subnet_address_pref),
                         JMESPathCheck('delegations[0].serviceName', delegation_service_name)])

        # Vnet exist, subnet x exist, x address prefixes
        vnet = 'testvnet1'
        subnet = 'testsubnet3'
        subnet_id = prepare_private_network(self, resource_group, server_name, vnet, subnet, location, delegation_service_name, None, None, yes=yes)
        vnet_id = subnet_id.split('/subnets/')[0]
        self.assertEqual(subnet_id,
                         '/subscriptions/{}/resourceGroups/{}/providers/Microsoft.Network/virtualNetworks/{}/subnets/{}'.format(
                         self.get_subscription_id(), resource_group, vnet, subnet))
        self.cmd('network vnet show --id {}'.format(vnet_id),
                 checks=[StringContainCheck(DEFAULT_VNET_ADDRESS_PREFIX)])
        self.cmd('network vnet subnet show --id {}'.format(subnet_id),
                 checks=[JMESPathCheck('addressPrefix', DEFAULT_SUBNET_ADDRESS_PREFIX),
                         JMESPathCheck('delegations[0].serviceName', delegation_service_name)])

        # Vnet exist, subnet exist, x address prefixes
        vnet = 'testvnet1'
        subnet = 'testsubnet1'
        vnet_address_pref = '172.1.0.0/16'
        subnet_address_pref = '172.1.0.0/24'
        subnet_id = prepare_private_network(self, resource_group, server_name, vnet, subnet, location, delegation_service_name, None, None, yes=yes)
        vnet_id = subnet_id.split('/subnets/')[0]
        self.assertEqual(subnet_id,
                         '/subscriptions/{}/resourceGroups/{}/providers/Microsoft.Network/virtualNetworks/{}/subnets/{}'.format(
                         self.get_subscription_id(), resource_group, vnet, subnet))
        self.cmd('network vnet show --id {}'.format(vnet_id),
                 checks=[StringContainCheck(vnet_address_pref)])
        self.cmd('network vnet subnet show --id {}'.format(subnet_id),
                 checks=[JMESPathCheck('addressPrefix', subnet_address_pref),
                         JMESPathCheck('delegations[0].serviceName', delegation_service_name)])

        # Vnet exist, subnet exist, address prefixes
        vnet = 'testvnet1'
        subnet = 'testsubnet1'
        vnet_address_pref = '173.1.0.0/16'
        subnet_address_pref = '173.2.0.0/24'
        subnet_id = prepare_private_network(self, resource_group, server_name, vnet, subnet, location, delegation_service_name, None, None, yes=yes)
        self.cmd('network vnet show --id {}'.format(vnet_id),
                 checks=[StringContainCheck('172.1.0.0/16')])
        self.cmd('network vnet subnet show --id {}'.format(subnet_id),
                 checks=[JMESPathCheck('addressPrefix', '172.1.0.0/24'),
                         JMESPathCheck('delegations[0].serviceName', delegation_service_name)])

    def _test_flexible_server_vnet_mgmt_prepare_private_network_vnet(self, resource_group):
        server_name = 'vnet-preparer-server'
        resource_group_2 = self.create_random_name('clitest.rg', 20)
        delegation_service_name = "Microsoft.DBforPostgreSQL/flexibleServers"
        location = self.postgres_location
        yes = True

        # Vnet x exist -> subnet generate with default prefix
        vnet = 'testvnet1'
        subnet_id = prepare_private_network(self, resource_group, server_name, vnet, None, location, delegation_service_name, None, None, yes=yes)
        vnet_id = subnet_id.split('/subnets/')[0]
        self.assertEqual(subnet_id,
                         '/subscriptions/{}/resourceGroups/{}/providers/Microsoft.Network/virtualNetworks/{}/subnets/{}'.format(
                         self.get_subscription_id(), resource_group, vnet, 'Subnet' + server_name))
        self.cmd('network vnet show --id {}'.format(vnet_id),
                 checks=[StringContainCheck(DEFAULT_VNET_ADDRESS_PREFIX)])
        self.cmd('network vnet subnet show --id {}'.format(subnet_id),
                 checks=[JMESPathCheck('addressPrefix', DEFAULT_SUBNET_ADDRESS_PREFIX),
                         JMESPathCheck('delegations[0].serviceName', delegation_service_name)])

        # Vnet x exist (id, diff rg)
        vnet = '/subscriptions/{}/resourceGroups/{}/providers/Microsoft.Network/virtualNetworks/{}'.format(self.get_subscription_id(), resource_group_2, 'testvnet2')
        subnet_id = prepare_private_network(self, resource_group, server_name, vnet, None, location, delegation_service_name, None, None, yes=yes)
        vnet_id = subnet_id.split('/subnets/')[0]
        self.assertEqual(subnet_id,
                         '/subscriptions/{}/resourceGroups/{}/providers/Microsoft.Network/virtualNetworks/{}/subnets/{}'.format(
                         self.get_subscription_id(), resource_group_2, 'testvnet2', 'Subnet' + server_name))
        self.cmd('network vnet show --id {}'.format(vnet_id),
                 checks=[StringContainCheck(DEFAULT_VNET_ADDRESS_PREFIX)])
        self.cmd('network vnet subnet show --id {}'.format(subnet_id),
                 checks=[JMESPathCheck('addressPrefix', DEFAULT_SUBNET_ADDRESS_PREFIX),
                         JMESPathCheck('delegations[0].serviceName', delegation_service_name)])

	    # Vnet exist (name), vnet prefix, subnet prefix
        vnet = 'testvnet3'
        vnet_address_pref = '172.0.0.0/16'
        self.cmd('network vnet create -n {} -g {} -l {} --address-prefix {}'
                  .format(vnet, resource_group, location, vnet_address_pref))
        subnet_address_pref = '172.0.10.0/24'
        subnet_id = prepare_private_network(self, resource_group, server_name, vnet, None, location, delegation_service_name, vnet_address_pref, subnet_address_pref, yes=yes)
        vnet_id = subnet_id.split('/subnets/')[0]
        self.assertEqual(subnet_id,
                         '/subscriptions/{}/resourceGroups/{}/providers/Microsoft.Network/virtualNetworks/{}/subnets/{}'.format(
                         self.get_subscription_id(), resource_group, vnet, 'Subnet' + server_name))
        self.cmd('network vnet show --id {}'.format(vnet_id),
                 checks=[StringContainCheck(vnet_address_pref)])
        self.cmd('network vnet subnet show --id {}'.format(subnet_id),
                 checks=[JMESPathCheck('addressPrefix', subnet_address_pref),
                         JMESPathCheck('delegations[0].serviceName', delegation_service_name)])

	    # Vnet exist (id, diff rg), vnet prefix, subnet prefix
        vnet = '/subscriptions/{}/resourceGroups/{}/providers/Microsoft.Network/virtualNetworks/{}'.format(self.get_subscription_id(), resource_group_2, 'testvnet4')
        vnet_address_pref = '173.1.0.0/16'
        self.cmd('network vnet create -n {} -g {} -l {} --address-prefix {}'
                  .format('testvnet4', resource_group_2, location, vnet_address_pref))
        subnet_address_pref = '173.1.1.0/24'
        subnet_id = prepare_private_network(self, resource_group, server_name, vnet, None, location, delegation_service_name, vnet_address_pref, subnet_address_pref, yes=yes)
        vnet_id = subnet_id.split('/subnets/')[0]
        self.assertEqual(subnet_id,
                         '/subscriptions/{}/resourceGroups/{}/providers/Microsoft.Network/virtualNetworks/{}/subnets/{}'.format(
                         self.get_subscription_id(), resource_group_2, 'testvnet4', 'Subnet' + server_name))
        self.cmd('network vnet show --id {}'.format(vnet_id),
                 checks=[StringContainCheck(vnet_address_pref)])
        self.cmd('network vnet subnet show --id {}'.format(subnet_id),
                 checks=[JMESPathCheck('addressPrefix', subnet_address_pref),
                         JMESPathCheck('delegations[0].serviceName', delegation_service_name)])

    def _test_flexible_server_vnet_mgmt_prepare_private_network_subnet(self, resource_group):
        server_name = 'vnet-preparer-server'
        delegation_service_name = "Microsoft.DBforPostgreSQL/flexibleServers"
        location = self.postgres_location
        yes = True

        #   subnet x exist
        subnet = '/subscriptions/{}/resourceGroups/{}/providers/Microsoft.Network/virtualNetworks/{}/subnets/{}'.format(
                 self.get_subscription_id(), resource_group, 'testvnet', 'testsubnet')
        vnet_address_pref = '172.1.0.0/16'
        subnet_address_pref = '172.1.0.0/24'
        subnet_id = prepare_private_network(self, resource_group, server_name, None, subnet, location, delegation_service_name, vnet_address_pref, subnet_address_pref, yes=yes)
        vnet_id = subnet_id.split('/subnets/')[0]
        self.assertEqual(subnet_id,
                         '/subscriptions/{}/resourceGroups/{}/providers/Microsoft.Network/virtualNetworks/{}/subnets/{}'.format(
                         self.get_subscription_id(), resource_group, 'testvnet', 'testsubnet'))
        self.cmd('network vnet show --id {}'.format(vnet_id),
                 checks=[StringContainCheck(vnet_address_pref)])
        self.cmd('network vnet subnet show --id {}'.format(subnet_id),
                 checks=[JMESPathCheck('addressPrefix', subnet_address_pref),
                         JMESPathCheck('delegations[0].serviceName', delegation_service_name)])

        # subnet exist
        subnet_address_pref = '172.1.1.0/24'
        self.cmd('network vnet subnet create -g {} -n {} --address-prefixes {} --vnet-name {}'.format(
                  resource_group, 'testsubnet2', subnet_address_pref, 'testvnet'))
        subnet = '/subscriptions/{}/resourceGroups/{}/providers/Microsoft.Network/virtualNetworks/{}/subnets/{}'.format(
                 self.get_subscription_id(), resource_group, 'testvnet', 'testsubnet2')

        subnet_id = prepare_private_network(self, resource_group, server_name, None, subnet, location, delegation_service_name, vnet_address_pref, subnet_address_pref, yes=yes)
        vnet_id = subnet_id.split('/subnets/')[0]
        self.assertEqual(subnet_id,
                         '/subscriptions/{}/resourceGroups/{}/providers/Microsoft.Network/virtualNetworks/{}/subnets/{}'.format(
                         self.get_subscription_id(), resource_group, 'testvnet', 'testsubnet2'))
        self.cmd('network vnet show --id {}'.format(vnet_id),
                 checks=[StringContainCheck(vnet_address_pref)])
        self.cmd('network vnet subnet show --id {}'.format(subnet_id),
                 checks=[JMESPathCheck('addressPrefix', subnet_address_pref),
                         JMESPathCheck('delegations[0].serviceName', delegation_service_name)])

    def _test_flexible_server_vnet_mgmt_validator(self, resource_group):
        # location validator
        vnet_name = 'testvnet'
        subnet_name = 'testsubnet'
        vnet_prefix = '172.1.0.0/16'
        subnet_prefix = '172.1.0.0/24'
        location = self.postgres_location
        self.cmd('network vnet create -g {} -l {} -n {} --address-prefixes {}'.format(
                 resource_group, location, vnet_name, vnet_prefix))

        self.cmd('postgres flexible-server create -g {} -l {} --vnet {} --yes'.format(
                 resource_group, 'westus', vnet_name), # location of vnet and server are different
                 expect_failure=True)

        # delegated to different service
        subnet = self.cmd('network vnet subnet create -g {} -n {} --vnet-name {} --address-prefixes {} --delegations {}'.format(
                          resource_group, subnet_name, vnet_name, subnet_prefix, "Microsoft.DBforMySQL/flexibleServers")).get_output_in_json()

        self.cmd('postgres flexible-server create -g {} -l {} --subnet {} --yes'.format(
                 resource_group, 'eastus', subnet["id"]), # Delegated to different service
                 expect_failure=True)

    def get_models(self, *attr_args, **kwargs):
        from azure.cli.core.profiles import get_sdk
        self.module_kwargs = kwargs
        resource_type = kwargs.get('resource_type', self._get_resource_type())
        operation_group = kwargs.get('operation_group', self.module_kwargs.get('operation_group', None))
        return get_sdk(self.cli_ctx, resource_type, *attr_args, mod='models', operation_group=operation_group)

    def _get_resource_type(self):
        resource_type = self.module_kwargs.get('resource_type', None)
        if not resource_type:
            command_type = self.module_kwargs.get('command_type', None)
            resource_type = command_type.settings.get('resource_type', None) if command_type else None
        return resource_type


class FlexibleServerPrivateDnsZoneScenarioTest(ScenarioTest):
    postgres_location = 'eastus'

    @AllowLargeResponse()
    @ResourceGroupPreparer(location=postgres_location, parameter_name='server_resource_group')
    @ResourceGroupPreparer(location=postgres_location, parameter_name='vnet_resource_group')
    def test_postgres_flexible_server_existing_private_dns_zone(self, server_resource_group, vnet_resource_group):
        self._test_flexible_server_existing_private_dns_zone('postgres', server_resource_group, vnet_resource_group)

    @pytest.mark.mysql_regression
    @AllowLargeResponse()
    @ResourceGroupPreparer(location=mysql_location, parameter_name='server_resource_group')
    @ResourceGroupPreparer(location=mysql_location, parameter_name='vnet_resource_group')
    def test_mysql_flexible_server_existing_private_dns_zone(self, server_resource_group, vnet_resource_group):
        self._test_flexible_server_existing_private_dns_zone('mysql', server_resource_group, vnet_resource_group)

    @AllowLargeResponse()
    @ResourceGroupPreparer(location=postgres_location, parameter_name='server_resource_group')
    @ResourceGroupPreparer(location=postgres_location, parameter_name='vnet_resource_group')
    @ResourceGroupPreparer(location=postgres_location, parameter_name='dns_resource_group')
    def test_postgres_flexible_server_new_private_dns_zone(self, server_resource_group, vnet_resource_group, dns_resource_group):
        self._test_flexible_server_new_private_dns_zone('postgres', server_resource_group, vnet_resource_group, dns_resource_group)

    @pytest.mark.mysql_regression
    @AllowLargeResponse()
    @ResourceGroupPreparer(location=mysql_location, parameter_name='server_resource_group')
    @ResourceGroupPreparer(location=mysql_location, parameter_name='vnet_resource_group')
    @ResourceGroupPreparer(location=mysql_location, parameter_name='dns_resource_group')
    def test_mysql_flexible_server_new_private_dns_zone(self, server_resource_group, vnet_resource_group, dns_resource_group):
        self._test_flexible_server_new_private_dns_zone('mysql', server_resource_group, vnet_resource_group, dns_resource_group)

    def _test_flexible_server_existing_private_dns_zone(self, database_engine, server_resource_group, vnet_resource_group):
        server_names = [self.create_random_name(SERVER_NAME_PREFIX, SERVER_NAME_MAX_LENGTH),
                        self.create_random_name(SERVER_NAME_PREFIX, SERVER_NAME_MAX_LENGTH)]
        if database_engine == 'postgres':
            location = self.postgres_location
            delegation_service_name = "Microsoft.DBforPostgreSQL/flexibleServers"
            private_dns_zone_key = "privateDnsZoneArmResourceId"
        else:
            location = mysql_location
            delegation_service_name = "Microsoft.DBforMySQL/flexibleServers"
            private_dns_zone_key = "privateDnsZoneResourceId"


        server_group_vnet_name = 'servergrouptestvnet'
        server_group_subnet_name = 'servergrouptestsubnet'
        vnet_group_vnet_name = 'vnetgrouptestvnet'
        vnet_group_subnet_name = 'vnetgrouptestsubnet'
        vnet_prefix = '172.1.0.0/16'
        subnet_prefix = '172.1.0.0/24'
        self.cmd('network vnet create -g {} -l {} -n {} --address-prefixes {} --subnet-name {} --subnet-prefixes {}'.format(
                 server_resource_group, location, server_group_vnet_name, vnet_prefix, server_group_subnet_name, subnet_prefix))
        server_group_vnet = self.cmd('network vnet show -g {} -n {}'.format(
                                     server_resource_group, server_group_vnet_name)).get_output_in_json()
        server_group_subnet = self.cmd('network vnet subnet show -g {} -n {} --vnet-name {}'.format(
                                       server_resource_group, server_group_subnet_name, server_group_vnet_name)).get_output_in_json()
        self.cmd('network vnet create -g {} -l {} -n {} --address-prefixes {} --subnet-name {} --subnet-prefixes {}'.format(
                 vnet_resource_group, location, vnet_group_vnet_name, vnet_prefix, vnet_group_subnet_name, subnet_prefix))
        vnet_group_vnet = self.cmd('network vnet show -g {} -n {}'.format(
                                   vnet_resource_group, vnet_group_vnet_name)).get_output_in_json()
        vnet_group_subnet = self.cmd('network vnet subnet show -g {} -n {} --vnet-name {}'.format(
                                       vnet_resource_group, vnet_group_subnet_name, vnet_group_vnet_name)).get_output_in_json()

        # FQDN validator
        self.cmd('{} flexible-server create -g {} -n {} -l {} --private-dns-zone {} --vnet {} --subnet {} --yes'.format(
                 database_engine, server_resource_group, server_names[0], location, server_names[0] + '.' + database_engine + '.database.azure.com', server_group_vnet_name, server_group_subnet_name),
                 expect_failure=True)

        # validate wrong suffix
        dns_zone_incorrect_suffix = 'clitestincorrectsuffix.database.{}.azure.com'.format(database_engine)
        self.cmd('{} flexible-server create -g {} -n {} -l {} --private-dns-zone {} --subnet {} --yes'.format(
            database_engine, server_resource_group, server_names[0], location, dns_zone_incorrect_suffix, server_group_subnet["id"]),
            expect_failure=True)

        # existing private dns zone in server group, no link
        unlinked_dns_zone = 'clitestunlinked.{}.database.azure.com'.format(database_engine)
        self.cmd('network private-dns zone create -g {} --name {}'.format(
                 server_resource_group, unlinked_dns_zone))

        self.cmd('{} flexible-server create -g {} -n {} -l {} --private-dns-zone {} --subnet {} --yes'.format(
            database_engine, server_resource_group, server_names[0], location, unlinked_dns_zone, server_group_subnet["id"]))
        result = self.cmd('{} flexible-server show -g {} -n {}'.format(database_engine, server_resource_group, server_names[0])).get_output_in_json()

        self.assertEqual(result["network"]["delegatedSubnetResourceId"],
                         '/subscriptions/{}/resourceGroups/{}/providers/Microsoft.Network/virtualNetworks/{}/subnets/{}'.format(
                         self.get_subscription_id(), server_resource_group, server_group_vnet_name, server_group_subnet_name))
        if database_engine == 'postgres':
            self.assertEqual(result["network"][private_dns_zone_key],
                            '/subscriptions/{}/resourceGroups/{}/providers/Microsoft.Network/privateDnsZones/{}'.format(
                            self.get_subscription_id(), server_resource_group, unlinked_dns_zone))
        self.cmd('network vnet show --id {}'.format(server_group_vnet['id']),
                 checks=[StringContainCheck(vnet_prefix)])
        self.cmd('network vnet subnet show --id {}'.format(server_group_subnet['id']),
                 checks=[JMESPathCheck('addressPrefix', subnet_prefix),
                         JMESPathCheck('delegations[0].serviceName', delegation_service_name)])

        # exisitng private dns zone in vnet group
        vnet_group_dns_zone = 'clitestvnetgroup.{}.database.azure.com'.format(database_engine)
        self.cmd('network private-dns zone create -g {} --name {}'.format(
                 vnet_resource_group, vnet_group_dns_zone))
        self.cmd('network private-dns link vnet create -g {} -n MyLinkName -z {} -v {} -e False'.format(
                 vnet_resource_group, vnet_group_dns_zone, vnet_group_vnet['id']
        ))
        self.cmd('{} flexible-server create -g {} -n {} -l {} --private-dns-zone {} --subnet {} --yes'.format(
                 database_engine, server_resource_group, server_names[1], location, vnet_group_dns_zone, vnet_group_subnet["id"]))
        result = self.cmd('{} flexible-server show -g {} -n {}'.format(database_engine, server_resource_group, server_names[1])).get_output_in_json()

        self.assertEqual(result["network"]["delegatedSubnetResourceId"],
                         '/subscriptions/{}/resourceGroups/{}/providers/Microsoft.Network/virtualNetworks/{}/subnets/{}'.format(
                         self.get_subscription_id(), vnet_resource_group, vnet_group_vnet_name, vnet_group_subnet_name))
        if database_engine == 'postgres':
            self.assertEqual(result["network"][private_dns_zone_key],
                            '/subscriptions/{}/resourceGroups/{}/providers/Microsoft.Network/privateDnsZones/{}'.format(
                            self.get_subscription_id(), vnet_resource_group, vnet_group_dns_zone))
        self.cmd('network vnet show --id {}'.format(vnet_group_vnet['id']),
                 checks=[StringContainCheck(vnet_prefix)])
        self.cmd('network vnet subnet show --id {}'.format(vnet_group_subnet['id']),
                 checks=[JMESPathCheck('addressPrefix', subnet_prefix),
                         JMESPathCheck('delegations[0].serviceName', delegation_service_name)])

        # delete all servers
        self.cmd('{} flexible-server delete -g {} -n {} --yes'.format(database_engine, server_resource_group, server_names[0]),
                 checks=NoneCheck())

        self.cmd('{} flexible-server delete -g {} -n {} --yes'.format(database_engine, server_resource_group, server_names[1]),
                 checks=NoneCheck())

        time.sleep(15 * 60)

    def _test_flexible_server_new_private_dns_zone(self, database_engine, server_resource_group, vnet_resource_group, dns_resource_group):
        server_names = ['clitest-private-dns-zone-test-3', 'clitest-private-dns-zone-test-4',
                        self.create_random_name(SERVER_NAME_PREFIX, SERVER_NAME_MAX_LENGTH),
                        self.create_random_name(SERVER_NAME_PREFIX, SERVER_NAME_MAX_LENGTH),
                        self.create_random_name(SERVER_NAME_PREFIX, SERVER_NAME_MAX_LENGTH)]
        private_dns_zone_names = ["clitestdnszone1.private.{}.database.azure.com".format(database_engine),
                                  "clitestdnszone2.private.{}.database.azure.com".format(database_engine),
                                  "clitestdnszone3.private.{}.database.azure.com".format(database_engine)]
        if database_engine == 'postgres':
            location = self.postgres_location
            delegation_service_name = "Microsoft.DBforPostgreSQL/flexibleServers"
            private_dns_zone_key = "privateDnsZoneArmResourceId"
            db_context = PostgresDbContext(cmd=self,
                                           cf_private_dns_zone_suffix=cf_postgres_flexible_private_dns_zone_suffix_operations,
                                           command_group='postgres')
        else:
            location = mysql_location
            delegation_service_name = "Microsoft.DBforMySQL/flexibleServers"
            db_context = MysqlDbContext(cmd=self,
                                        cf_private_dns_zone_suffix=cf_mysql_flexible_private_dns_zone_suffix_operations,
                                        command_group='mysql')
            private_dns_zone_key = "privateDnsZoneResourceId"

        server_group_vnet_name = 'servergrouptestvnet'
        server_group_subnet_name = 'servergrouptestsubnet'
        vnet_group_vnet_name = 'vnetgrouptestvnet'
        vnet_group_subnet_name = 'vnetgrouptestsubnet'
        vnet_prefix = '172.1.0.0/16'
        subnet_prefix = '172.1.0.0/24'
        self.cmd('network vnet create -g {} -l {} -n {} --address-prefixes {} --subnet-name {} --subnet-prefixes {}'.format(
                 server_resource_group, location, server_group_vnet_name, vnet_prefix, server_group_subnet_name, subnet_prefix))
        server_group_vnet = self.cmd('network vnet show -g {} -n {}'.format(
                                     server_resource_group, server_group_vnet_name)).get_output_in_json()
        server_group_subnet = self.cmd('network vnet subnet show -g {} -n {} --vnet-name {}'.format(
                                       server_resource_group, server_group_subnet_name, server_group_vnet_name)).get_output_in_json()
        self.cmd('network vnet create -g {} -l {} -n {} --address-prefixes {} --subnet-name {} --subnet-prefixes {}'.format(
                 vnet_resource_group, location, vnet_group_vnet_name, vnet_prefix, vnet_group_subnet_name, subnet_prefix))
        vnet_group_vnet = self.cmd('network vnet show -g {} -n {}'.format(
                                   vnet_resource_group, vnet_group_vnet_name)).get_output_in_json()
        vnet_group_subnet = self.cmd('network vnet subnet show -g {} -n {} --vnet-name {}'.format(
                                       vnet_resource_group, vnet_group_subnet_name, vnet_group_vnet_name)).get_output_in_json()
        # no input, vnet in server rg
        dns_zone = prepare_private_dns_zone(db_context, database_engine, server_resource_group, server_names[0], None, server_group_subnet["id"], location, True)
        self.assertEqual(dns_zone,
                         '/subscriptions/{}/resourceGroups/{}/providers/Microsoft.Network/privateDnsZones/{}'.format(
                         self.get_subscription_id(), server_resource_group, server_names[0] + ".private." + database_engine + ".database.azure.com"))

        # no input, vnet in vnet rg
        dns_zone = prepare_private_dns_zone(db_context, database_engine, server_resource_group, server_names[1], None, vnet_group_subnet["id"], location, True)
        self.assertEqual(dns_zone,
                         '/subscriptions/{}/resourceGroups/{}/providers/Microsoft.Network/privateDnsZones/{}'.format(
                         self.get_subscription_id(), vnet_resource_group, server_names[1] + ".private." + database_engine + ".database.azure.com"))

        # new private dns zone, zone name (vnet in smae rg)
        dns_zone = prepare_private_dns_zone(db_context, database_engine, server_resource_group, server_names[2], private_dns_zone_names[0],
                                            server_group_subnet["id"], location, True)
        self.assertEqual(dns_zone,
                         '/subscriptions/{}/resourceGroups/{}/providers/Microsoft.Network/privateDnsZones/{}'.format(
                         self.get_subscription_id(), server_resource_group, private_dns_zone_names[0]))

        # new private dns zone in dns rg, zone id (vnet in diff rg)
        dns_id = '/subscriptions/{}/resourceGroups/{}/providers/Microsoft.Network/privateDnsZones/{}'.format(
                 self.get_subscription_id(), dns_resource_group, private_dns_zone_names[1])
        self.cmd('{} flexible-server create -g {} -n {} -l {} --private-dns-zone {} --subnet {} --yes'.format(
                 database_engine, server_resource_group, server_names[3], location, dns_id, vnet_group_subnet["id"]))
        result = self.cmd('{} flexible-server show -g {} -n {}'.format(database_engine, server_resource_group, server_names[3])).get_output_in_json()
        self.assertEqual(result["network"]["delegatedSubnetResourceId"],
                         '/subscriptions/{}/resourceGroups/{}/providers/Microsoft.Network/virtualNetworks/{}/subnets/{}'.format(
                         self.get_subscription_id(), vnet_resource_group, vnet_group_vnet_name, vnet_group_subnet_name))
        if database_engine == 'postgres':
            self.assertEqual(result["network"][private_dns_zone_key], dns_id)

        # new private dns zone, zone id vnet server same rg, zone diff rg
        dns_id = '/subscriptions/{}/resourceGroups/{}/providers/Microsoft.Network/privateDnsZones/{}'.format(
                 self.get_subscription_id(), dns_resource_group, private_dns_zone_names[2])
        self.cmd('{} flexible-server create -g {} -n {} -l {} --private-dns-zone {} --subnet {} --yes'.format(
                 database_engine, server_resource_group, server_names[4], location, dns_id, server_group_subnet["id"]))
        result = self.cmd('{} flexible-server show -g {} -n {}'.format(database_engine, server_resource_group, server_names[4])).get_output_in_json()
        self.assertEqual(result["network"]["delegatedSubnetResourceId"],
                         '/subscriptions/{}/resourceGroups/{}/providers/Microsoft.Network/virtualNetworks/{}/subnets/{}'.format(
                         self.get_subscription_id(), server_resource_group, server_group_vnet_name, server_group_subnet_name))
        if database_engine == 'postgres':
            self.assertEqual(result["network"][private_dns_zone_key], dns_id)

        self.cmd('{} flexible-server delete -g {} -n {} --yes'.format(database_engine, server_resource_group, server_names[3]),
                 checks=NoneCheck())

        self.cmd('{} flexible-server delete -g {} -n {} --yes'.format(database_engine, server_resource_group, server_names[4]),
                 checks=NoneCheck())

        time.sleep(15 * 60)


class FlexibleServerPublicAccessMgmtScenarioTest(ScenarioTest):
    postgres_location = 'eastus'

    @AllowLargeResponse()
    @ResourceGroupPreparer(location=postgres_location)
    @live_only()
    def test_postgres_flexible_server_public_access_mgmt(self, resource_group):
        self._test_flexible_server_public_access_mgmt('postgres', resource_group)

    @pytest.mark.mysql_regression
    @AllowLargeResponse()
    @ResourceGroupPreparer(location=mysql_location)
    @live_only()
    def test_mysql_flexible_server_public_access_mgmt(self, resource_group):
        self._test_flexible_server_public_access_mgmt('mysql', resource_group)

    def _test_flexible_server_public_access_mgmt(self, database_engine, resource_group):
        # flexible-server create
        if self.cli_ctx.local_context.is_on:
            self.cmd('config param-persist off')

        if database_engine == 'postgres':
            sku_name = 'Standard_D2s_v3'
            location = self.postgres_location
        elif database_engine == 'mysql':
            sku_name = 'Standard_B1ms'
            location = mysql_location

        # flexible-servers
        servers = [self.create_random_name(SERVER_NAME_PREFIX, SERVER_NAME_MAX_LENGTH),
                   self.create_random_name(SERVER_NAME_PREFIX, SERVER_NAME_MAX_LENGTH),
                   self.create_random_name(SERVER_NAME_PREFIX, SERVER_NAME_MAX_LENGTH),
                   self.create_random_name(SERVER_NAME_PREFIX, SERVER_NAME_MAX_LENGTH)]

        # Case 1 : Provision a server with public access all
        result = self.cmd('{} flexible-server create -g {} -n {} --public-access {} -l {}'
                          .format(database_engine, resource_group, servers[0], 'all', location)).get_output_in_json()

        self.cmd('{} flexible-server firewall-rule show -g {} -n {} -r {}'
                 .format(database_engine, resource_group, servers[0], result["firewallName"]),
                 checks=[JMESPathCheck('startIpAddress', '0.0.0.0'),
                         JMESPathCheck('endIpAddress', '255.255.255.255')])

        # Case 2 : Provision a server with public access allowing all azure services
        result = self.cmd('{} flexible-server create -g {} -n {} --public-access {} -l {}'
                          .format(database_engine, resource_group, servers[1], '0.0.0.0', location)).get_output_in_json()

        self.cmd('{} flexible-server firewall-rule show -g {} -n {} -r {}'
                 .format(database_engine, resource_group, servers[1], result["firewallName"]),
                 checks=[JMESPathCheck('startIpAddress', '0.0.0.0'),
                         JMESPathCheck('endIpAddress', '0.0.0.0')])

        # Case 3 : Provision a server with public access with rangwe
        result = self.cmd('{} flexible-server create -g {} -n {} --public-access {} -l {}'
                          .format(database_engine, resource_group, servers[2], '10.0.0.0-12.0.0.0', location)).get_output_in_json()

        self.cmd('{} flexible-server firewall-rule show -g {} -n {} -r {}'
                 .format(database_engine, resource_group, servers[2], result["firewallName"]),
                 checks=[JMESPathCheck('startIpAddress', '10.0.0.0'),
                         JMESPathCheck('endIpAddress', '12.0.0.0')])

        # Case 3 : Provision a server with public access with rangwe
        result = self.cmd('{} flexible-server create -g {} -n {} -l {} --yes'
                          .format(database_engine, resource_group, servers[3], location)).get_output_in_json()

        firewall_rule = self.cmd('{} flexible-server firewall-rule show -g {} -n {} -r {}'
                                 .format(database_engine, resource_group, servers[3], result["firewallName"])).get_output_in_json()
        self.assertEqual(firewall_rule['startIpAddress'], firewall_rule['endIpAddress'])

        # delete all servers
        self.cmd('{} flexible-server delete -g {} -n {} --yes'.format(database_engine, resource_group, servers[0]),
                 checks=NoneCheck())

        self.cmd('{} flexible-server delete -g {} -n {} --yes'.format(database_engine, resource_group, servers[1]),
                 checks=NoneCheck())

        self.cmd('{} flexible-server delete -g {} -n {} --yes'.format(database_engine, resource_group, servers[2]),
                 checks=NoneCheck())

        self.cmd('{} flexible-server delete -g {} -n {} --yes'.format(database_engine, resource_group, servers[3]),
                 checks=NoneCheck())


class FlexibleServerUpgradeMgmtScenarioTest(ScenarioTest):
    postgres_location = 'eastus'

    @AllowLargeResponse()
    @ResourceGroupPreparer(location=mysql_location)
    def test_postgres_flexible_server_upgrade_mgmt(self, resource_group):
        self._test_flexible_server_upgrade_mgmt('postgres', resource_group, False)
        self._test_flexible_server_upgrade_mgmt('postgres', resource_group, True)

    @pytest.mark.mysql_regression
    @AllowLargeResponse()
    @ResourceGroupPreparer(location=mysql_location)
    def test_mysql_flexible_server_upgrade_mgmt(self, resource_group):
        self._test_flexible_server_upgrade_mgmt('mysql', resource_group, False)
        self._test_flexible_server_upgrade_mgmt('mysql', resource_group, True)
    
    def _test_flexible_server_upgrade_mgmt(self, database_engine, resource_group, public_access):
        server_name = self.create_random_name(SERVER_NAME_PREFIX, SERVER_NAME_MAX_LENGTH)
        replica_name = self.create_random_name(SERVER_NAME_PREFIX, SERVER_NAME_MAX_LENGTH)

        if database_engine == 'mysql':
            current_version = '5.7'
            new_version = '8'
            location = mysql_location
        else:
            current_version = '11'
            new_version = '14'
            location = self.postgres_location

        create_command = '{} flexible-server create -g {} -n {} --tier GeneralPurpose --sku-name {} --location {} --version {} --yes'.format(
            database_engine, resource_group, server_name, mysql_general_purpose_sku, location, current_version)
        if public_access:
            create_command += ' --public-access none'
        else:
            vnet_name = self.create_random_name('VNET', SERVER_NAME_MAX_LENGTH)
            subnet_name = self.create_random_name('SUBNET', SERVER_NAME_MAX_LENGTH)
            create_command += ' --vnet {} --subnet {}'.format(vnet_name, subnet_name)

        # create primary server
        self.cmd(create_command)

        self.cmd('{} flexible-server show -g {} -n {}'.format(database_engine, resource_group, server_name),
                 checks=[JMESPathCheck('version', current_version)])

        # create replica
        self.cmd('{} flexible-server replica create -g {} --replica-name {} --source-server {}'
                 .format(database_engine, resource_group, replica_name, server_name),
                 checks=[JMESPathCheck('version', current_version)])

        if database_engine == 'mysql':
            # remove sql_mode NO_AUTO_CREATE_USER, which is incompatible with new version 8
            for server in [replica_name, server_name]:
                self.cmd('{} flexible-server parameter set -g {} -s {} -n {} -v {}'
                         .format(database_engine,
                                 resource_group,
                                 server,
                                 'sql_mode',
                                 'ONLY_FULL_GROUP_BY,STRICT_TRANS_TABLES,NO_ZERO_IN_DATE,NO_ZERO_DATE,ERROR_FOR_DIVISION_BY_ZERO'))

            # should fail because we first need to upgrade replica
            self.cmd('{} flexible-server upgrade -g {} -n {} --version {} --yes'.format(database_engine, resource_group, server_name, new_version),
                     expect_failure=True)

            # upgrade replica
            result = self.cmd('{} flexible-server upgrade -g {} -n {} --version {} --yes'.format(database_engine, resource_group, replica_name, new_version)).get_output_in_json()
            self.assertTrue(result['version'].startswith(new_version))
        else:
            # should fail because we can't upgrade replica
            self.cmd('{} flexible-server upgrade -g {} -n {} --version {} --yes'.format(database_engine, resource_group, replica_name, new_version),
                     expect_failure=True)

            # should fail because we can't upgrade primary server with existing replicas
            self.cmd('{} flexible-server upgrade -g {} -n {} --version {} --yes'.format(database_engine, resource_group, server_name, new_version),
                     expect_failure=True)

            # delete replica
            self.cmd('{} flexible-server delete -g {} -n {} --yes'.format(database_engine, resource_group, replica_name))

        # upgrade primary server
        result = self.cmd('{} flexible-server upgrade -g {} -n {} --version {} --yes'.format(database_engine, resource_group, server_name, new_version)).get_output_in_json()
        self.assertTrue(result['version'].startswith(new_version))


class FlexibleServerBackupsMgmtScenarioTest(ScenarioTest):
    postgres_location = 'eastus'

    @AllowLargeResponse()
    @ResourceGroupPreparer(location=postgres_location)
    @ServerPreparer(engine_type='postgres', location=postgres_location)
    def test_postgres_flexible_server_backups_mgmt(self, resource_group, server):
        self._test_backups_mgmt('postgres', resource_group, server)

    @pytest.mark.mysql_regression
    @AllowLargeResponse()
    @ResourceGroupPreparer(location=mysql_location)
    @ServerPreparer(engine_type='mysql', location=mysql_location)
    def test_mysql_flexible_server_backups_mgmt(self, resource_group, server):
        self._test_backups_mgmt('mysql', resource_group, server)

    def _test_backups_mgmt(self, database_engine, resource_group, server):
        if database_engine == 'postgres':
            attempts = 0
            while attempts < 10:
                backups = self.cmd('{} flexible-server backup list -g {} -n {}'
                                .format(database_engine, resource_group, server)).get_output_in_json()
                attempts += 1
                if len(backups) > 0:
                    break
                os.environ.get(ENV_LIVE_TEST, False) and sleep(60)

            self.assertTrue(len(backups) == 1)

            automatic_backup = self.cmd('{} flexible-server backup show -g {} -n {} --backup-name {}'
                                        .format(database_engine, resource_group, server, backups[0]['name'])).get_output_in_json()

            self.assertDictEqual(automatic_backup, backups[0])

        # No need to check the first backup in mysql flexible server because first backup visibility is a probability event. 
        if database_engine == 'mysql':
            backup_name = self.create_random_name('backup', 20)
            self.cmd('{} flexible-server backup create -g {} -n {} --backup-name {}'
                     .format(database_engine, resource_group, server, backup_name))

            backups = self.cmd('{} flexible-server backup list -g {} -n {}'
                               .format(database_engine, resource_group, server)).get_output_in_json()

            backups = sorted(backups, key=lambda x: x['completedTime'], reverse=True)

            customer_backup = self.cmd('{} flexible-server backup show -g {} -n {} --backup-name {}'
                                        .format(database_engine, resource_group, server, backup_name)).get_output_in_json()

            self.assertEqual(backup_name, customer_backup['name'])
            self.assertDictEqual(customer_backup, backups[0])


class FlexibleServerIdentityAADAdminMgmtScenarioTest(ScenarioTest):
    postgres_location = 'eastus'

    @pytest.mark.mysql_regression
    @AllowLargeResponse()
    @ResourceGroupPreparer(location=mysql_location)
    def test_mysql_flexible_server_identity_aad_admin_mgmt(self, resource_group):
        self._test_identity_aad_admin_mgmt('mysql', resource_group, 'enabled')

    @AllowLargeResponse()
    @ResourceGroupPreparer(location=postgres_location)
    def test_postgresql_flexible_server_identity_aad_admin_mgmt(self, resource_group):
        self._test_identity_aad_admin_mgmt('postgres', resource_group, 'enabled')

    def _test_identity_aad_admin_mgmt(self, database_engine, resource_group, password_auth):
        login = 'alanenriqueo@microsoft.com'
        sid = '894ef8da-7971-4f68-972c-f561441eb329'

        if database_engine == 'postgres':
            auth_args = '--password-auth {} --active-directory-auth enabled'.format(password_auth)
            admin_id_arg = '-i {}'.format(sid) if database_engine == 'postgres' else ''
        elif database_engine == 'mysql':
            auth_args = ''
            admin_id_arg = ''

        server = self.create_random_name(SERVER_NAME_PREFIX, SERVER_NAME_MAX_LENGTH)
        replica = [self.create_random_name(SERVER_NAME_PREFIX, SERVER_NAME_MAX_LENGTH) for _ in range(2)]

        # create server
        self.cmd('{} flexible-server create -g {} -n {} --public-access none --tier {} --sku-name {} {}'
                 .format(database_engine, resource_group, server, 'GeneralPurpose', mysql_general_purpose_sku, auth_args))

        # create 3 identities
        identity = []
        identity_id = []
        for i in range(3):
            identity.append(self.create_random_name('identity', 32))
            result = self.cmd('identity create -g {} --name {}'.format(resource_group, identity[i])).get_output_in_json()
            identity_id.append(result['id'])

        # add identity 1 to primary server
        self.cmd('{} flexible-server identity assign -g {} -s {} -n {}'
                 .format(database_engine, resource_group, server, identity_id[0]),
                 checks=[
                     JMESPathCheckExists('userAssignedIdentities."{}"'.format(identity_id[0]))])

        # create replica 1
        self.cmd('{} flexible-server replica create -g {} --replica-name {} --source-server {}'
                 .format(database_engine, resource_group, replica[0], server))

        if database_engine == 'postgres':
            # assign identity 1 to replica 1
            self.cmd('{} flexible-server identity assign -g {} -s {} -n {}'
                     .format(database_engine, resource_group, replica[0], identity_id[0]))

        self.cmd('{} flexible-server identity list -g {} -s {}'
                 .format(database_engine, resource_group, replica[0]),
                 checks=[
                     JMESPathCheckExists('userAssignedIdentities."{}"'.format(identity_id[0]))])

        admins = self.cmd('{} flexible-server ad-admin list -g {} -s {}'
                          .format(database_engine, resource_group, server)).get_output_in_json()
        self.assertEqual(0, len(admins))

        if database_engine == 'mysql':
            # try to add identity 2 to replica 1
            self.cmd('{} flexible-server identity assign -g {} -s {} -n {}'
                     .format(database_engine, resource_group, replica[0], identity_id[1]),
                     expect_failure=True)

            # try to add AAD admin with identity 2 to replica 1
            self.cmd('{} flexible-server ad-admin create -g {} -s {} -u {} -i {} --identity {}'
                     .format(database_engine, resource_group, replica[0], login, sid, identity_id[1]),
                     expect_failure=True)
        elif database_engine == 'postgres':
            # add identity 1 to replica 1
            self.cmd('{} flexible-server identity assign -g {} -s {} -n {}'
                     .format(database_engine, resource_group, replica[0], identity_id[0]),
                     checks=[
                         JMESPathCheckExists('userAssignedIdentities."{}"'.format(identity_id[0]))])

            # add identity 2 to replica 1 and primary server
            for server_name in [replica[0], server]:
                self.cmd('{} flexible-server identity assign -g {} -s {} -n {}'
                         .format(database_engine, resource_group, server_name, identity_id[1]),
                         checks=[
                             JMESPathCheckExists('userAssignedIdentities."{}"'.format(identity_id[1]))])

            # try to add AAD admin to replica 1
            self.cmd('{} flexible-server ad-admin create -g {} -s {} -u {} -i {}'
                     .format(database_engine, resource_group, replica[0], login, sid),
                     expect_failure=True)

        if database_engine == 'mysql':
            # add AAD admin with identity 2 to primary server
            admin_checks = [JMESPathCheck('identityResourceId', identity_id[1]),
                            JMESPathCheck('administratorType', 'ActiveDirectory'),
                            JMESPathCheck('name', 'ActiveDirectory'),
                            JMESPathCheck('login', login),
                            JMESPathCheck('sid', sid)]

            self.cmd('{} flexible-server ad-admin create -g {} -s {} -u {} -i {} --identity {}'
                     .format(database_engine, resource_group, server, login, sid, identity_id[1]))
            
            self.cmd('{} flexible-server ad-admin show -g {} -s {} {}'
                        .format(database_engine, resource_group, server, admin_id_arg),
                        checks=admin_checks)

            self.cmd('{} flexible-server identity list -g {} -s {}'
                    .format(database_engine, resource_group, server),
                    checks=[
                        JMESPathCheckExists('userAssignedIdentities."{}"'.format(identity_id[0])),
                        JMESPathCheckExists('userAssignedIdentities."{}"'.format(identity_id[1]))])
        elif database_engine == 'postgres':
            # add AAD admin to primary server
            admin_checks = [JMESPathCheck('principalType', 'User'),
                            JMESPathCheck('principalName', login),
                            JMESPathCheck('objectId', sid)]

            self.cmd('{} flexible-server ad-admin create -g {} -s {} -u {} -i {}'
                     .format(database_engine, resource_group, server, login, sid))

            for server_name in [server, replica[0]]:
                self.cmd('{} flexible-server ad-admin show -g {} -s {} {}'
                        .format(database_engine, resource_group, server_name, admin_id_arg),
                        checks=admin_checks)

                self.cmd('{} flexible-server identity list -g {} -s {}'
                        .format(database_engine, resource_group, server_name),
                        checks=[
                            JMESPathCheckExists('userAssignedIdentities."{}"'.format(identity_id[0])),
                            JMESPathCheckExists('userAssignedIdentities."{}"'.format(identity_id[1]))])

        # create replica 2
        self.cmd('{} flexible-server replica create -g {} --replica-name {} --source-server {}'
                 .format(database_engine, resource_group, replica[1], server))

        if database_engine == 'postgres':
            # assign identities 1 and 2 to replica 2
            self.cmd('{} flexible-server identity assign -g {} -s {} -n {} {}'
                     .format(database_engine, resource_group, replica[1], identity_id[0], identity_id[1]))

        self.cmd('{} flexible-server identity list -g {} -s {}'
                 .format(database_engine, resource_group, replica[1]),
                 checks=[
                     JMESPathCheckExists('userAssignedIdentities."{}"'.format(identity_id[0])),
                     JMESPathCheckExists('userAssignedIdentities."{}"'.format(identity_id[1]))])

        self.cmd('{} flexible-server ad-admin show -g {} -s {} {}'
                    .format(database_engine, resource_group, replica[1], admin_id_arg),
                    checks=admin_checks)

        if database_engine == 'mysql':
            # verify that aad_auth_only=OFF in primary server and all replicas
            for server_name in [server, replica[0], replica[1]]:
                self.cmd('{} flexible-server parameter show -g {} -s {} -n aad_auth_only'
                         .format(database_engine, resource_group, server_name),
                         checks=[JMESPathCheck('value', 'OFF')])
        elif database_engine == 'postgres':
            # verify that authConfig.activeDirectoryAuth=enabled and authConfig.passwordAuth=disabled in primary server and all replicas
            for server_name in [server, replica[0], replica[1]]:
                list_checks = [JMESPathCheck('authConfig.activeDirectoryAuth', 'enabled', False),
                            JMESPathCheck('authConfig.passwordAuth', password_auth, False)]
                self.cmd('{} flexible-server show -g {} -n {}'.format(database_engine, resource_group, server_name), checks=list_checks)

        if database_engine == 'mysql':
            # set aad_auth_only=ON in primary server and replica 2
            for server_name in [server, replica[1]]:
                self.cmd('{} flexible-server parameter set -g {} -s {} -n aad_auth_only -v {}'
                         .format(database_engine, resource_group, server_name, 'ON'),
                         checks=[JMESPathCheck('value', 'ON')])

            # try to remove identity 2 from primary server
            self.cmd('{} flexible-server identity remove -g {} -s {} -n {} --yes'
                     .format(database_engine, resource_group, server, identity_id[1]),
                     expect_failure=True)

        # try to remove AAD admin from replica 2
        self.cmd('{} flexible-server ad-admin delete -g {} -s {} {} --yes'
                 .format(database_engine, resource_group, replica[1], admin_id_arg),
                 expect_failure=True)

        # remove AAD admin from primary server
        self.cmd('{} flexible-server ad-admin delete -g {} -s {} {} --yes'
                 .format(database_engine, resource_group, server, admin_id_arg))

        for server_name in [server, replica[0], replica[1]]:
            admins = self.cmd('{} flexible-server ad-admin list -g {} -s {}'
                              .format(database_engine, resource_group, server_name)).get_output_in_json()
            self.assertEqual(0, len(admins))

        if database_engine == 'mysql':
            # verify that aad_auth_only=OFF in primary server and all replicas
            for server_name in [server, replica[0], replica[1]]:
                self.cmd('{} flexible-server parameter show -g {} -s {} -n aad_auth_only'
                         .format(database_engine, resource_group, server_name),
                         checks=[JMESPathCheck('value', 'OFF')])

        # add identity 3 to primary server
        self.cmd('{} flexible-server identity assign -g {} -s {} -n {}'
                 .format(database_engine, resource_group, server, identity_id[2]))
        if database_engine == 'postgres':
            # add identity 3 to replica 1 and 2
            for server_name in [replica[0], replica[1]]:
                self.cmd('{} flexible-server identity assign -g {} -s {} -n {}'
                         .format(database_engine, resource_group, server_name, identity_id[2]))

        for server_name in [server, replica[0], replica[1]]:
            self.cmd('{} flexible-server identity list -g {} -s {}'
                     .format(database_engine, resource_group, server_name),
                     checks=[
                         JMESPathCheckExists('userAssignedIdentities."{}"'.format(identity_id[0])),
                         JMESPathCheckExists('userAssignedIdentities."{}"'.format(identity_id[1])),
                         JMESPathCheckExists('userAssignedIdentities."{}"'.format(identity_id[2]))])

        # remove identities 1 and 2 from primary server
        self.cmd('{} flexible-server identity remove -g {} -s {} -n {} {} --yes'
                 .format(database_engine, resource_group, server, identity_id[0], identity_id[1]))
        if database_engine == 'postgres':
            # remove identities 1 and 2 from replica 1 and 2
            for server_name in [replica[0], replica[1]]:
                self.cmd('{} flexible-server identity remove -g {} -s {} -n {} {} --yes'
                         .format(database_engine, resource_group, server_name, identity_id[0], identity_id[1]))

        for server_name in [server, replica[0], replica[1]]:
            self.cmd('{} flexible-server identity list -g {} -s {}'
                     .format(database_engine, resource_group, server_name),
                     checks=[
                         JMESPathCheckNotExists('userAssignedIdentities."{}"'.format(identity_id[0])),
                         JMESPathCheckNotExists('userAssignedIdentities."{}"'.format(identity_id[1])),
                         JMESPathCheckExists('userAssignedIdentities."{}"'.format(identity_id[2]))])

        if database_engine == 'mysql':
            # remove identity 3 from primary server
            self.cmd('{} flexible-server identity remove -g {} -s {} -n {} --yes'
                     .format(database_engine, resource_group, server, identity_id[2]))

            for server_name in [server, replica[0], replica[1]]:
                self.cmd('{} flexible-server identity list -g {} -s {}'
                         .format(database_engine, resource_group, server_name),
                         checks=[
                             JMESPathCheckNotExists('userAssignedIdentities."{}"'.format(identity_id[0])),
                             JMESPathCheckNotExists('userAssignedIdentities."{}"'.format(identity_id[1])),
                             JMESPathCheckNotExists('userAssignedIdentities."{}"'.format(identity_id[2]))])

        # delete everything
        for server_name in [replica[0], replica[1], server]:
            self.cmd('{} flexible-server delete -g {} -n {} --yes'.format(database_engine, resource_group, server_name))

    @AllowLargeResponse()
    @ResourceGroupPreparer(location=postgres_location)
    def test_postgresql_flexible_server_identity_aad_admin_only_mgmt(self, resource_group):
        self._test_identity_aad_admin_mgmt('postgres', resource_group, 'disabled')
