# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------

from knack.util import CLIError


def create_test1(cmd, client, resource_group_name, account_name, location=None, tags=None):
    raise CLIError('TODO: Implement `test1 create`')


def list_test1(cmd, client, resource_group_name=None):
    raise CLIError('TODO: Implement `test1 list`')


def update_test1(cmd, instance, tags=None):
    with cmd.update_context(instance) as c:
        c.set_param('tags', tags)
    return instance