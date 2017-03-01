#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2017 CNRS and University of Strasbourg
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import os
import sys

import argparse
import ConfigParser
import socket
import requests

from six.moves import urllib


def get_os_params(config_file):
    '''Return OpenStack parameters
    '''
    os_params = {'username': None, 'password': None, 'project_name': None,
                 'user_domain_name': None, 'project_domain_name': None,
                 'auth_uri': None, 'cacert': None}
    config_parser = ConfigParser.ConfigParser()
    config_parser.read(config_file)
    if not config_parser.has_section('keystone_authtoken'):
        return {}
    for param in os_params.keys():
        if config_parser.has_option('keystone_authtoken', param):
            os_params[param] = config_parser.get('keystone_authtoken', param)
    return os_params


def main():
    parser = argparse.ArgumentParser(description="Check Keystone API.",
                                     version="0.1")
    parser.add_argument('config_file', metavar='CONFIG_FILE', type=str,
                        help=('Configuration file'))
    args = parser.parse_args()
    config_file = args.config_file

    params = get_os_params(config_file)
    parsed_url = urllib.parse.urlparse(params['auth_uri'])
    keystone_host = parsed_url.hostname
    keystone_port = int(parsed_url.port)
    try:
        # Verify that the port is reachable
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex((keystone_host, keystone_port))
        if result != 0:
            print("CRITICAL - cannot connect to keystone server %s "
                  "on port %s" % (keystone_host, keystone_port))
            sys.exit(2)

        # Check that the API is working
        headers = {'Content-Type': 'application/json'}
        data = '''{
"auth": {
  "identity": {
    "methods": ["password"],
      "password": {
        "user": {
          "name": "%s",
          "domain": {"name": "%s"},
          "password": "%s"
        }
      }
    }
  }
}''' % (params['username'], params['user_domain_name'], params['password'])

        url = params['auth_uri'] + '/auth/tokens'

        if params['cacert']:
            if os.path.isfile(params['cacert']):
                ca_check = params['cacert']
            else:
                print("UNKNOWN - No such CA Cert: %s" % (params['cacert']))
                sys.exit(3)
        else:
            ca_check = False

        req = requests.post(url, data, headers=headers, verify=ca_check)
        if req.status_code == 201 and u'token' in req.json():
            print("OK - Keystone API successfully tested.")
            sys.exit(0)
        else:
            print("CRITICAL - Failed to get token from Keystone"
                  " server: %s" % (keystone_host))
            sys.exit(2)

    except Exception as ex: # pylint: disable=broad-except
        # All other exceptional conditions, we report as 'UNKNOWN' probe status
        print("UNKNOWN - Unexpected error while testing "
              "Keystone API: %s" % (str(ex)))
        sys.exit(3)

if __name__ == '__main__':
    main()
