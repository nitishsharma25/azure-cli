# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
#
# Code generated by aaz-dev-tools
# --------------------------------------------------------------------------------------------

# pylint: skip-file
# flake8: noqa

from azure.cli.core.aaz import *


@register_command(
    "vm generalize",
)
class Generalize(AAZCommand):
    """Mark a VM as generalized, allowing it to be imaged for multiple deployments.

    For an end-to-end tutorial, see https://docs.microsoft.com/azure/virtual-machines/linux/capture-image

    :example: Deallocate, generalize, and capture a stopped virtual machine.
        az vm deallocate -g MyResourceGroup -n MyVm
        az vm generalize -g MyResourceGroup -n MyVm
        az vm capture -g MyResourceGroup -n MyVm --vhd-name-prefix MyPrefix

    :example: Deallocate, generalize, and capture multiple stopped virtual machines.
        az vm deallocate --ids vms_ids
        az vm generalize --ids vms_ids
        az vm capture --ids vms_ids --vhd-name-prefix MyPrefix
    """

    _aaz_info = {
        "version": "2017-12-01",
        "resources": [
            ["mgmt-plane", "/subscriptions/{}/resourcegroups/{}/providers/microsoft.compute/virtualmachines/{}/generalize", "2017-12-01"],
        ]
    }

    def _handler(self, command_args):
        super()._handler(command_args)
        self._execute_operations()
        return self._output()

    _args_schema = None

    @classmethod
    def _build_arguments_schema(cls, *args, **kwargs):
        if cls._args_schema is not None:
            return cls._args_schema
        cls._args_schema = super()._build_arguments_schema(*args, **kwargs)

        # define Arg Group ""

        _args_schema = cls._args_schema
        _args_schema.resource_group = AAZResourceGroupNameArg(
            required=True,
        )
        _args_schema.vm_name = AAZStrArg(
            options=["-n", "--name", "--vm-name"],
            help="The name of the Virtual Machine. You can configure the default using `az configure --defaults vm=<name>`",
            required=True,
            id_part="name",
            configured_default="vm",
        )
        return cls._args_schema

    def _execute_operations(self):
        self.pre_operations()
        self.VirtualMachinesGeneralize(ctx=self.ctx)()
        self.post_operations()

    @register_callback
    def pre_operations(self):
        pass

    @register_callback
    def post_operations(self):
        pass

    def _output(self, *args, **kwargs):
        result = self.deserialize_output(self.ctx.vars.instance, client_flatten=True)
        return result

    class VirtualMachinesGeneralize(AAZHttpOperation):
        CLIENT_TYPE = "MgmtClient"

        def __call__(self, *args, **kwargs):
            request = self.make_request()
            session = self.client.send_request(request=request, stream=False, **kwargs)
            if session.http_response.status_code in [200]:
                return self.on_200(session)

            return self.on_error(session.http_response)

        @property
        def url(self):
            return self.client.format_url(
                "/subscriptions/{subscriptionId}/resourceGroups/{resourceGroupName}/providers/Microsoft.Compute/virtualMachines/{vmName}/generalize",
                **self.url_parameters
            )

        @property
        def method(self):
            return "POST"

        @property
        def error_format(self):
            return "MgmtErrorFormat"

        @property
        def url_parameters(self):
            parameters = {
                **self.serialize_url_param(
                    "resourceGroupName", self.ctx.args.resource_group,
                    required=True,
                ),
                **self.serialize_url_param(
                    "subscriptionId", self.ctx.subscription_id,
                    required=True,
                ),
                **self.serialize_url_param(
                    "vmName", self.ctx.args.vm_name,
                    required=True,
                ),
            }
            return parameters

        @property
        def query_parameters(self):
            parameters = {
                **self.serialize_query_param(
                    "api-version", "2017-12-01",
                    required=True,
                ),
            }
            return parameters

        @property
        def header_parameters(self):
            parameters = {
                **self.serialize_header_param(
                    "Accept", "application/json",
                ),
            }
            return parameters

        def on_200(self, session):
            data = self.deserialize_http_content(session)
            self.ctx.set_var(
                "instance",
                data,
                schema_builder=self._build_schema_on_200
            )

        _schema_on_200 = None

        @classmethod
        def _build_schema_on_200(cls):
            if cls._schema_on_200 is not None:
                return cls._schema_on_200

            cls._schema_on_200 = AAZObjectType()

            _schema_on_200 = cls._schema_on_200
            _schema_on_200.end_time = AAZStrType(
                serialized_name="endTime",
                flags={"read_only": True},
            )
            _schema_on_200.error = AAZObjectType()
            _schema_on_200.name = AAZStrType(
                flags={"read_only": True},
            )
            _schema_on_200.start_time = AAZStrType(
                serialized_name="startTime",
                flags={"read_only": True},
            )
            _schema_on_200.status = AAZStrType(
                flags={"read_only": True},
            )

            error = cls._schema_on_200.error
            error.code = AAZStrType()
            error.details = AAZListType()
            error.innererror = AAZObjectType()
            error.message = AAZStrType()
            error.target = AAZStrType()

            details = cls._schema_on_200.error.details
            details.Element = AAZObjectType()

            _element = cls._schema_on_200.error.details.Element
            _element.code = AAZStrType()
            _element.message = AAZStrType()
            _element.target = AAZStrType()

            innererror = cls._schema_on_200.error.innererror
            innererror.errordetail = AAZStrType()
            innererror.exceptiontype = AAZStrType()

            return cls._schema_on_200


class _GeneralizeHelper:
    """Helper class for Generalize"""


__all__ = ["Generalize"]
