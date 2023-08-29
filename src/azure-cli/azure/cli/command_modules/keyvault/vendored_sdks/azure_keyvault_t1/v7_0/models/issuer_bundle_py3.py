# coding=utf-8
# --------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
#
# Code generated by Microsoft (R) AutoRest Code Generator.
# Changes may cause incorrect behavior and will be lost if the code is
# regenerated.
# --------------------------------------------------------------------------
# pylint: skip-file
# flake8: noqa
from msrest.serialization import Model


class IssuerBundle(Model):
    """The issuer for Key Vault certificate.

    Variables are only populated by the server, and will be ignored when
    sending a request.

    :ivar id: Identifier for the issuer object.
    :vartype id: str
    :param provider: The issuer provider.
    :type provider: str
    :param credentials: The credentials to be used for the issuer.
    :type credentials: ~azure.keyvault.v7_0.models.IssuerCredentials
    :param organization_details: Details of the organization as provided to
     the issuer.
    :type organization_details:
     ~azure.keyvault.v7_0.models.OrganizationDetails
    :param attributes: Attributes of the issuer object.
    :type attributes: ~azure.keyvault.v7_0.models.IssuerAttributes
    """

    _validation = {
        'id': {'readonly': True},
    }

    _attribute_map = {
        'id': {'key': 'id', 'type': 'str'},
        'provider': {'key': 'provider', 'type': 'str'},
        'credentials': {'key': 'credentials', 'type': 'IssuerCredentials'},
        'organization_details': {'key': 'org_details', 'type': 'OrganizationDetails'},
        'attributes': {'key': 'attributes', 'type': 'IssuerAttributes'},
    }

    def __init__(self, *, provider: str=None, credentials=None, organization_details=None, attributes=None, **kwargs) -> None:
        super(IssuerBundle, self).__init__(**kwargs)
        self.id = None
        self.provider = provider
        self.credentials = credentials
        self.organization_details = organization_details
        self.attributes = attributes
