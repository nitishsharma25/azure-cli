# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------

# pylint: disable=line-too-long
from azure.cli.core.commands import CliCommandType
from azure.cli.command_modules.test1._client_factory import cf_test1


def load_command_table(self, _):

    test1_sdk = CliCommandType(
        operations_tmpl='azure.mgmt.maps.operations#AccountsOperations.{}',
        client_factory=cf_test1)


    with self.command_group('test1', test1_sdk, client_factory=cf_test1) as g:
        g.custom_command('create', 'create_test1')
        g.command('delete', 'delete')
        g.custom_command('list', 'list_test1')
        g.show_command('show', 'get')
        g.generic_update_command('update', setter_name='update', custom_func_name='update_test1')


    with self.command_group('test1', is_preview=True):
        pass

