# coding: utf-8
from __future__ import unicode_literals
import os
import email
import pytest
import emails
from emails import Message
from emails.compat import NativeStringIO, to_bytes, to_native, is_py26
from emails.exc import DKIMException
from emails.utils import load_email_charsets
import emails.packages.dkim
from .helpers import common_email_data



PRIV_KEY = b"""-----BEGIN RSA PRIVATE KEY-----
MIICXAIBAAKBgQDKHKzbg7LwpSJVfy9h8YQciVuIiexJ6OKJcCc6akJuLx+qPJGr
t0chdV92slT9Lm1DUAjQEd8r9kVKa8FrWrnThMWx5HoXkGOIW2NqC0vrTZUgvhWy
mlnwiysIylCirStZvA2uszYiFQK8slYD3H25UFTIOqLgB6AvV6URo26iJQIDAQAB
AoGAOHt5B0Ov3zaW+MO5byq6m+r7DJZW1XTi0jvoipelhvteYwnYP9/RXhVaH2bI
/5RY7qXQQK2t67BAPwMMI79QDL+jWsgwE0hly/qloOgEuX1+D/yGBShlYNQXvjAY
UgkNYtp5JBVr8byz7upzvIyDsWJGoUrBindYnEiAVgwzZuECQQDKsKRwQhTCOZjW
tkrockxDKMlXyKRLpOdqmwH0hwUdcWklxlmE+IJz4NVlz5qCVJz/oT+TgBNex8I5
spxWAmdNAkEA/0UdnlXYueGVDIe5SUQGlXb8U8fTYtA/NsduFwq8QEWMrVBXK+uH
4upq70kFlyfP5mpTOZwUgY2jH/qrXD8qOQJAdx1L5bTP4jxa94N1jhjtfGJRwMbm
1pV4cgvaIEvg06a8djiUjzJD57lvbz+Lu5/iC9BFPnd76q1WFPZELb+H2QJBAK8y
DWDlBEiW5QfjgqwhDu+36PfLNm4kBK6g8xLHYGowEZvFfv56uRloz5mIoVibj1lR
ceshDwXXYrSJAuDdzSkCQDkx2TeKLUqKSxJNUYSrakQIo/41AOFvFBTbJuH3RZoy
W/1DFMld7rC2gVHYW3m/LNd1qbi5QR9/buGxE7Y8ylI=
-----END RSA PRIVATE KEY-----"""

PUB_KEY = b"""MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDKHKzbg7LwpSJVfy9h8YQciVuI
iexJ6OKJcCc6akJuLx+qPJGrt0chdV92slT9Lm1DUAjQEd8r9kVKa8FrWrnThMWx
5HoXkGOIW2NqC0vrTZUgvhWymlnwiysIylCirStZvA2uszYiFQK8slYD3H25UFTI
OqLgB6AvV6URo26iJQIDAQAB"""


def _generate_key(length=1024):
    # From: http://stackoverflow.com/questions/3504955/using-rsa-in-python
    try:
        from Crypto.PublicKey import RSA
        key = RSA.generate(length)
        return to_bytes(key.exportKey()), to_bytes(key.publickey().exportKey())
    except ImportError:
        return PRIV_KEY, PUB_KEY


def _check_dkim(message, pub_key=PUB_KEY):
    def _plain_public_key(s):
        return b"".join([l for l in s.split(b'\n') if not l.startswith(b'---')])
    message = message.as_string()
    o = emails.packages.dkim.DKIM(message=to_bytes(message))
    return o.verify(dnsfunc=lambda name: b"".join([b"v=DKIM1; p=", _plain_public_key(pub_key)]))


def test_dkim():

    priv_key, pub_key = _generate_key(length=1024)

    DKIM_PARAMS = [dict(key=NativeStringIO(to_native(priv_key)),
                        selector='_dkim',
                        domain='somewhere1.net'),

                   dict(key=priv_key,
                        selector='_dkim',
                        domain='somewhere2.net'),

                   # legacy key argument name
                   dict(privkey=priv_key,
                        selector='_dkim',
                        domain='somewhere3.net'),
                   ]

    if is_py26:
        load_email_charsets()

    for dkimparams in DKIM_PARAMS:
        message = Message(**common_email_data())
        message.dkim(**dkimparams)
        # check DKIM header exist
        assert message.as_message()['DKIM-Signature']
        #print(__name__, "type message.as_string()==", type(message.as_string()))
        #print(message.as_string())
        #print(type(message.as_string()))
        #print(email.__file__)
        #print(email.charset.CHARSETS)
        #print('adding utf-8 charset...')
        #email.charset.add_charset('utf-8', email.charset.BASE64, email.charset.BASE64)
        #print(email.charset.CHARSETS)
        assert 'DKIM-Signature: ' in message.as_string()
        assert _check_dkim(message, pub_key)
        #assert 0



def test_dkim_error():

    m = emails.html(**common_email_data())

    # No key
    with pytest.raises(TypeError):
        m.dkim(selector='_dkim',
               domain='somewhere.net',
               ignore_sign_errors=False)


    # Error in invalid key
    invalid_key = 'X'
    with pytest.raises(DKIMException):
        m.dkim(key=invalid_key,
               selector='_dkim',
               domain='somewhere.net',
               ignore_sign_errors=False)

    # Error on invalid dkim parameters

    m.dkim(key=PRIV_KEY,
           selector='_dkim',
           domain='somewhere.net',
           include_headers=['To'])

    with pytest.raises(DKIMException):
        # include_heades must contain 'From'
        m.as_string()

    # Skip error on ignore_sign_errors=True
    m.dkim(key=PRIV_KEY,
           selector='_dkim',
           domain='somewhere.net',
           ignore_sign_errors=True,
           include_headers=['To'])

    m.as_string()
    m.as_message()


def test_dkim_sign_twice():

    # Test #44:
    # " if you put the open there and send more than one messages it fails
    #   (the first works but the next will not if you dont seek(0) the dkim file first)"
    # Actually not.

    priv_key, pub_key = _generate_key(length=1024)
    message = Message(**common_email_data())
    message.dkim(key=NativeStringIO(to_native(priv_key)), selector='_dkim', domain='somewhere.net')
    for n in range(2):
        message.subject = 'Test %s' % n
        assert _check_dkim(message, pub_key)
