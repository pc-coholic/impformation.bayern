#!/usr/bin/env python3
import io
import json
import sys
from datetime import datetime
from urllib.parse import urlparse, parse_qs
from uuid import uuid4

import requests as requests
from bs4 import BeautifulSoup


class C19Impformation(object):
    def __init__(self, configfile='config.json'):
        self.session = []
        self.config = self.read_from_file(configfile)
        self.tokens = []
        self.lastset = -1

        if isinstance(self.config, dict):
            self.config = [self.config]
        elif isinstance(self.config, list):
            pass
        else:
            print("something might be of with the config file...")
            sys.exit()
        """
        if self.config['abusecontact']:
            self.session.headers.update({
                'X-Abuse-Contact': self.config['abusecontact']
            })
        """

    def get_sets_and_session(self):
        self.lastset += 1
        if self.lastset == len(self.config):
            self.lastset = 0

        return self.config[self.lastset], self.tokens[self.lastset], self.session[self.lastset]

    def get_env(self, iam=False, configset=None):
        if not configset:
            configset = self.config[0]

        if 'env' not in configset or configset['env'] == 'prod':
            return '{}impfzentren.bayern'.format('ciam.' if iam else '')
        else:
            return '{}{}impfzentren.bayern'.format(configset['env'], '-ciam.' if iam else '')

    def login(self):
        for configset in self.config:
            self.session.append(requests.Session())

            # Get the login-form
            resp = self.session[-1].get(
                'https://{env}/auth/realms/C19V-Citizen/protocol/openid-connect/auth'.format(
                    env=self.get_env(iam=True, configset=configset)
                ),
                params={
                    'client_id': 'c19v-frontend',
                    'redirect_uri': 'https://{env}/citizen/'.format(
                        env=self.get_env(configset=configset)
                    ),
                    'response_mode': 'fragment',
                    'response_type': 'code',
                    'scope': 'openid',
                    'nonce': uuid4()
                }
            )

            # Parse the login-form and retrieve the submit-action which includes all kinds of query-parameters
            soup = BeautifulSoup(resp.content, 'html.parser')
            auth_url = soup.find(id='kc-form-login').attrs['action']

            # Post to the parsed Authorization URL using our credentials
            resp = self.session[-1].post(
                auth_url,
                data={
                    'username': configset['username'],
                    'password': configset['password'],
                    'credentialId': configset['credentialId'],
                },
                allow_redirects=False
            )

            # Retrieve the location we are being redirected and get the code-attribute
            url = urlparse(resp.headers['location'])
            code = parse_qs(url.fragment)['code']

            # Request a new token using the code we just received
            resp = self.session[-1].post(
                'https://{env}/auth/realms/C19V-Citizen/protocol/openid-connect/token'.format(
                    env=self.get_env(iam=True, configset=configset)
                ),
                data={
                    'client_id': 'c19v-frontend',
                    'grant_type': 'authorization_code',
                    'code': code,
                    'redirect_uri': 'https://{env}/citizen/'.format(
                        env=self.get_env(configset=configset)
                    )
                }
            )

            # Store the tokens for later use.
            self.tokens.append(resp.json())

    def get_authorization_header(self, tokenset=None):
        if not tokenset:
            tokenset = self.tokens[0]

        if 'access_token' not in tokenset:
            raise Exception('No access_token available!')

        return {
            'Authorization': 'Bearer {access_token}'.format(
                # We should use the access token and track the `expires_in`-time (300sec/5min).
                # But I'm feeling lazy today and so we're using the refresh_token, which only expires in 1800sec/30min.
                #access_token=tokenset['access_token']
                access_token=tokenset['refresh_token']
            )
        }

    def read_from_file(self, filename):
        with io.open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)

    def write_to_file(self, filename, data):
        with io.open(filename, 'w+', encoding='utf-8') as f:
            f.write(json.dumps(data))

    def get_vaccines(self):
        print("Getting vaccines")
        configset, tokenset, session = self.get_sets_and_session()

        resp = session.get(
            'https://{env}/api/v1/vaccines/'.format(
                env=self.get_env(configset=configset)
            ),
            headers=self.get_authorization_header(tokenset=tokenset)
        )

        return resp.json()

    def get_districts(self):
        print("Getting districts")
        configset, tokenset, session = self.get_sets_and_session()

        resp = session.get(
            'https://{env}/api/v1/districts/'.format(
                env=self.get_env(configset=configset)
            ),
            headers=self.get_authorization_header(tokenset=tokenset)
        )

        return resp.json()

    def make_centers_list(self, districts):
        centers = {}
        for district in districts:
            centers[district['name']] = [center['id'] for center in district['centers']]

        return centers

    def get_sites_for_center(self, centerId):
        print("Getting Sites for center {centerId}".format(
            centerId=centerId
        ))
        configset, tokenset, session = self.get_sets_and_session()

        resp = session.get(
            'https://{env}/api/v1/centers/{centerId}/sites'.format(
                env=self.get_env(configset=configset),
                centerId=centerId
            ),
            headers=self.get_authorization_header(tokenset=tokenset)
        )

        sites = {}
        for site in resp.json():
            print(site)
            sites[site['id']] = {
                'center': centerId,
                'name': site['name'],
                'address': site['address'] if 'address' in site else None,
                'type': site['type']
            }

        return sites

    def get_sites(self, centers):
        sites = {}
        for district, centerIds in centers.items():
            for center in centerIds:
                sites.update(
                    self.get_sites_for_center(center)
                )

        return sites

    def get_appointments_for_site(self, siteId, siteData):
        print("Getting appointments for site {siteId}".format(
            siteId=siteId
        ))

        configset, tokenset, session = self.get_sets_and_session()

        try:
            resp = session.get(
                'https://{env}/api/v1/citizens/{userUUID}/appointments/next'.format(
                    env=self.get_env(configset=configset),
                    userUUID=configset['userUUID']
                ),
                params={
                    'timeOfDay': 'ALL_DAY',
                    'lastDate': datetime.today().strftime('%Y-%m-%d'),
                    'lastTime': '00:00',
                    'possibleSiteId': siteId
                },
                headers=self.get_authorization_header(tokenset=tokenset)
            )
        except:
            print("Request failed")
            siteData['first_available'] = None
        else:
            if resp.status_code == 404:
                print("No appointments available")
                siteData['first_available'] = None
            elif resp.status_code in [200, 201, 202]:
                print("Appointments available")
                data = resp.json()
                siteData['first_available'] = {
                    'date': data['firstVaccinationDate'],
                    'time': data['firstVaccinationTime'],
                    'vaccine': data['vaccineId']
                }
            else:
                print("Something went wrong...", resp.status_code)
                siteData['first_available'] = None
        finally:
            siteData['lastcheck'] = datetime.today().strftime('%Y-%m-%d %H:%M')

        return siteData

    def get_appointments(self, sites):
        appointments = {}
        for siteId, siteData in sites.items():
            appointments.update({
                siteId: self.get_appointments_for_site(siteId, siteData)
            })

        return appointments


if __name__ == '__main__':
    c19 = C19Impformation()

    c19.login()

    vaccines = c19.get_vaccines()
    c19.write_to_file('vaccines.json', vaccines)

    districts = c19.get_districts()
    c19.write_to_file('districts.json', districts)

    centers = c19.make_centers_list(districts)
    c19.write_to_file('centers.json', centers)

    sites = c19.get_sites(centers)
    c19.write_to_file('sites.json', sites)

    appointments = c19.get_appointments(sites)
    c19.write_to_file('appointments.json', appointments)
