#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Version : 0.0.1
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2020/12/15 11:16 
Desc    : ETCD  version v3.4 调用
"""

import requests
import base64
import json
import random


class Etcd3Client:
    def __init__(self, host="localhost", port=2379, hosts=None, user=None, passwd=None, timeout=2000):
        self.__version__ = 'v3.4_9'
        self.host = host
        self.port = port
        if hosts:  self.host, self.port = random.choice(hosts)
        self.user = user
        self.passwd = passwd
        self.timeout = timeout
        self.error = ""
        self.conn = requests.session()

    def GetToken(self):
        try:
            url = "http://{0}:{1}/v3/auth/authenticate".format(self.host, self.port)
            params = {
                "name": self.user,
                "password": self.passwd
            }
            res = self.conn.post(url=url, data=json.dumps(params), timeout=self.timeout)
            if res.status_code == 200:
                self.token = res.json()['token']
        except Exception as e:
            self.error = str(e)

    def _enbase64(self, value):
        return base64.b64encode(value.encode("utf-8"))

    def _debase64(self, value):
        return base64.b64decode(value)

    def Connect(self):
        try:
            self.conn = requests.session()
            if self.user:
                self.GetToken()
        except Exception as e:
            self.error = str(e)

    def Close(self):
        self.conn.close()

    def increment_last_byte(self, byte_string):
        s = bytearray(byte_string)
        s[-1] = s[-1] + 1
        return bytes(s)

    def to_bytes(self, maybe_bytestring):
        if isinstance(maybe_bytestring, bytes):
            return maybe_bytestring
        else:
            return maybe_bytestring.encode('utf-8')

    def lease_to_id(self, lease):
        """Figure out if the argument is a Lease object, or the lease ID."""
        lease_id = 0
        if hasattr(lease, 'id'):
            lease_id = lease.id
        else:
            try:
                lease_id = int(lease)
            except TypeError:
                pass
        return lease_id

    def _get_range(self, key, range_end=None, limit=None, revision=None, sort_order=None, sort_target='key',
                   serializable=False, keys_only=False, count_only=None, min_mod_revision=None, max_mod_revision=None,
                   min_create_revision=None, max_create_revision=None):

        try:
            url = "http://{0}:{1}/v3/kv/range".format(self.host, self.port)

            params = {}
            key = self._enbase64(key)

            params['key'] = key.decode("utf-8")
            params['keys_only'] = keys_only

            if range_end is not None:
                params['range_end'] = self._enbase64(range_end)

            if sort_order is None:
                params['sort_order'] = 'NONE'
            elif sort_order == 'ascend':
                params['sort_order'] = 'ASCEND'
            elif sort_order == 'descend':
                params['sort_order'] = 'DESCEND '

            if sort_order is None:
                params['sort_order'] = 'NONE'
            elif sort_order == 'ascend':
                params['sort_order'] = 'ASCEND'
            elif sort_order == 'descend':
                params['sort_order'] = 'DESCEND '

            if sort_target is None or sort_target == 'key':
                params['sort_target'] = 'KEY'
            elif sort_target == 'version':
                params['sort_target'] = 'VERSION '
            elif sort_target == 'create':
                params['sort_target'] = 'CREATE '
            elif sort_target == 'mod':
                params['sort_target'] = 'MOD '
            elif sort_target == 'value':
                params['sort_target'] = 'VALUE '
            params['limit'] = limit
            params['revision'] = revision
            params['serializable'] = serializable
            params['count_only'] = count_only
            params['min_mod_revision'] = min_mod_revision
            params['max_mod_revision'] = max_mod_revision
            params['min_create_revision'] = min_create_revision
            params['max_create_revision'] = max_create_revision
            data = self.conn.post(
                url=url,
                data=json.dumps(params), timeout=self.timeout)
            return data
        except Exception as e:
            # print(e)
            self.error = str(e)

    def get_response(self, key, serializable=False):
        return self._get_range(key=key, serializable=serializable)

    def get(self, key, **kwargs):
        try:
            resp = self.get_response(
                key=key,
                **kwargs
            )
            if resp.status_code == 200:
                data = resp.json()
                if int(data['count']) < 1:
                    return (
                        True,
                        None
                    )
                else:
                    return (
                        True,
                        self._debase64(data['kvs'][0]['value'])
                    )
            else:
                return (False, None)
        except Exception as e:
            self.error = str(e)

    def get_prefix_response(self, key_prefix, sort_order=None, sort_target='key', keys_only=False):
        return self._get_range(key=key_prefix, range_end=self.increment_last_byte(self.to_bytes(key_prefix)),
                               sort_order=sort_order, sort_target=sort_target, keys_only=keys_only)

    def get_prefix(self, key_prefix, **kwargs):
        try:
            resp = self.get_prefix_response(key_prefix=key_prefix, **kwargs)
            if resp.status_code == 200:
                data = resp.json()
                if not data.has_key('count'):
                    return (0, None)
                else:
                    res = []
                    for i in data['kvs']:
                        item = {}
                        if i.has_key('value'):
                            item['key'] = self._debase64(i['key'])
                            item['value'] = self._debase64(i['value'])
                            res.append(item)
                        else:
                            res.append(self._debase64(i['key']))
                    return (True, res)
            else:
                return (False, None)
        except Exception as e:
            self.error = str(e)

    def ttl(self, ttl_id=123, ttl=60) -> bool:
        try:
            url = "http://{0}:{1}/v3/lease/grant".format(self.host, self.port)

            headers = {
            }

            params = {"ID": ttl_id, "TTL": ttl}

            resp = self.conn.post(url=url, headers=headers, data=json.dumps(params), timeout=self.timeout)
            # print(resp.text)

            return True if resp.status_code == 200 else False

        except Exception as e:
            print(e)
            self.error = str(e)

    def put(self, key, value, lease=None, prev_kv=False):
        try:
            url = "http://{0}:{1}/v3/kv/put".format(self.host, self.port)

            headers = {
                # "Authorization": self.token,
                # "Connection": 'keep-alive'
            }

            params = {
                "key": self._enbase64(key).decode("utf-8"),
                "value": self._enbase64(value).decode('utf-8'),
                "lease": self.lease_to_id(lease),
                "prev_kv": prev_kv
            }

            resp = self.conn.post(url=url, headers=headers, data=json.dumps(params), timeout=self.timeout)
            return True if resp.status_code == 200 else False

        except Exception as e:
            print(e)
            self.error = str(e)

    def delete(self, key, value, lease=None, prev_kv=False):
        try:
            url = "http://{0}:{1}/v3/kv/del".format(self.host, self.port)

            headers = {
                # "Authorization": self.token,
                # "Connection": 'keep-alive'
            }

            params = {
                "key": self._enbase64(key).decode("utf-8"),
                "value": self._enbase64(value).decode('utf-8'),
                "lease": self.lease_to_id(lease),
                "prev_kv": prev_kv
            }

            resp = self.conn.post(url=url, headers=headers, data=json.dumps(params), timeout=self.timeout)
            return True if resp.status_code == 200 else False

        except Exception as e:
            print(e)
            self.error = str(e)


if __name__ == "__main__":
    client = Etcd3Client()

    b = client.put("asd", "asd")
    print(b)

    _, c = client.get("asd")
    print(c)
