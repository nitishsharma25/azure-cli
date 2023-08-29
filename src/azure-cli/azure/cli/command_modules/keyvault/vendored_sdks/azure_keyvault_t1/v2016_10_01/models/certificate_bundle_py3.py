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


class CertificateBundle(Model):
    """A certificate bundle consists of a certificate (X509) plus its attributes.

    Variables are only populated by the server, and will be ignored when
    sending a request.

    :ivar id: The certificate id.
    :vartype id: str
    :ivar kid: The key id.
    :vartype kid: str
    :ivar sid: The secret id.
    :vartype sid: str
    :ivar x509_thumbprint: Thumbprint of the certificate.
    :vartype x509_thumbprint: bytes
    :ivar policy: The management policy.
    :vartype policy: ~azure.keyvault.v2016_10_01.models.CertificatePolicy
    :param cer: CER contents of x509 certificate.
    :type cer: bytearray
    :param content_type: The content type of the secret.
    :type content_type: str
    :param attributes: The certificate attributes.
    :type attributes: ~azure.keyvault.v2016_10_01.models.CertificateAttributes
    :param tags: Application specific metadata in the form of key-value pairs
    :type tags: dict[str, str]
    """

    _validation = {
        'id': {'readonly': True},
        'kid': {'readonly': True},
        'sid': {'readonly': True},
        'x509_thumbprint': {'readonly': True},
        'policy': {'readonly': True},
    }

    _attribute_map = {
        'id': {'key': 'id', 'type': 'str'},
        'kid': {'key': 'kid', 'type': 'str'},
        'sid': {'key': 'sid', 'type': 'str'},
        'x509_thumbprint': {'key': 'x5t', 'type': 'base64'},
        'policy': {'key': 'policy', 'type': 'CertificatePolicy'},
        'cer': {'key': 'cer', 'type': 'bytearray'},
        'content_type': {'key': 'contentType', 'type': 'str'},
        'attributes': {'key': 'attributes', 'type': 'CertificateAttributes'},
        'tags': {'key': 'tags', 'type': '{str}'},
    }

    def __init__(self, *, cer: bytearray=None, content_type: str=None, attributes=None, tags=None, **kwargs) -> None:
        super(CertificateBundle, self).__init__(**kwargs)
        self.id = None
        self.kid = None
        self.sid = None
        self.x509_thumbprint = None
        self.policy = None
        self.cer = cer
        self.content_type = content_type
        self.attributes = attributes
        self.tags = tags
