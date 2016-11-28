#!/usr/bin/env python3
"""
A library & CLI tool to work with the ADP website.

Has a PayCheckFetcher class that will do what you'd expect and download PDFs of
your pay checks.
"""

import json
import locale
import os
import shutil

import click
import requests


class PayCheckFetcher:
    """
    This works by going through roughly the same routine a human would go
    through to log in to my.adp.com, get a list of all their paystubs, and
    download the ones that they need.

    Those steps are roughly:
    1. Give username & password to
        https://agateway.adp.com/siteminderagent/forms/login.fcc
    2. Go to https://my.adp.com/static/redbox/ to load resources
    3. Go to https://my.adp.com/redboxapi/identity/v1/self to figure out your
        ADP 'Associate OID'.
    4. Go to https://my.adp.com/v1_0/O/A/payStatements to get a list of
        available pay stubs
    5. Download whatever's needed.
    """
    LOGIN_URL = 'https://agateway.adp.com/siteminderagent/forms/login.fcc'
    LANDING_URL = 'https://my.adp.com/static/redbox/'
    UID_LOOKUP_URL = 'https://my.adp.com/redboxapi/identity/v1/self'
    PAYSTUB_LIST_URL = 'https://my.adp.com/v1_0/O/A/payStatements'

    def __init__(self, username, password, session):
        self.username = username
        self.password = password
        self.session = session
        self.paystub_url_by_date = {}  # to be populated below

    def log_in(self):
        """
        Log in to "Redbox" or whatever by passing in the expected parameters,
        and also where we intend to go next ('target').

        This will give us back a 302 to 'target', but more importantly will set
        up a FORMCRED cookie to say we logged in properly.
        """
        req_data = {
            'user': self.username,
            'password': self.password,
            'target': self.LANDING_URL
        }
        self.session.post(self.LOGIN_URL, data=req_data)

    def get_all_the_cookies(self):
        """
        Header over to the landing page like a human. This will get us even
        more cookies that we'll end up needing later.

        This will fetch us some very important cookies including a Session ID
        (SMSESSION) and various keep-alive (I guess?) cookies (TS*).
        """
        self.session.get(self.LANDING_URL)

    def get_uid(self):
        """
        Now that we have a session established we need to figure out our
        "associateoid" which is a unique identifier for the human in question.
        We'll need this later to get a list of paystub URLs by setting the
        'idtoken' cookie to the value we find here.
        """
        response = self.session.get(self.UID_LOOKUP_URL)
        info = json.loads(response.text)

        new_cookies = {
            'idtoken': info['associateoid'],
            'ADPLangLocalCookie': locale.getdefaultlocale()[0]
        }
        requests.utils.add_dict_to_cookiejar(self.session.cookies, new_cookies)

    def get_paystub_urls(self, limit, adjustments='yes'):
        """
        At this point we should know everything about ourselves and have all
        the cookies we need to get info about the available paystubs.

        I'm not sure what the 'adjustments' parameter does, but it seems sane
        to leave it set to 'yes'.
        """
        payload = {'adjustments': adjustments, 'numberoflastpaydates': limit}
        response = self.session.get(self.PAYSTUB_LIST_URL, params=payload)
        info = json.loads(response.text)

        self.paystub_url_by_date = {
            statement['payDate']: statement['statementImageUri']['href']
            for statement in info['payStatements']
        }

    def get_needed_paystubs(self):
        """
        Now that we have a dict of paystubs available and the date they're for,
        let's figure out which ones we don't currently have and return a list.

        We check:
          1. The file isn't in the current directory already
          2. The file isn't in a directory named after the year
        """
        need = []
        for date, url in self.paystub_url_by_date.items():
            artifact = PayCheckFetcher._expected_file_name(date)
            if os.path.exists(artifact):
                # We have it for sure, right here. Don't need it.
                continue

            year = date.split('-')[0]

            if os.path.exists(os.path.join(year, artifact)):
                # Oh, it's in a year folder. Cool.
                continue

            # We probably need this one.
            need.append([date, url])
        return sorted(need)

    @staticmethod
    def _transform_download_url(url):
        if not url.startswith('/l2'):
            return url

        return url.replace('/l2', 'https://my.adp.com')

    @staticmethod
    def _expected_file_name(date):
        return '{}.pdf'.format(date)

    def download_paystub(self, date, url):
        """
        Given a date to download and the URL to download it from, store the
        content in date.pdf in the current directory.
        """
        url = PayCheckFetcher._transform_download_url(url)

        response = self.session.get(url, stream=True)
        if response.status_code != 200:
            print("Got back {} when trying to fetch {} at {}".format(
                response.status_code, date, url
            ))
            return

        out_f_name = PayCheckFetcher._expected_file_name(date)
        with open(out_f_name, 'wb') as out_f:
            response.raw.decode_content = True
            shutil.copyfileobj(response.raw, out_f)
            print("Downloaded {}".format(out_f_name))

    def download_needed(self, limit):
        """
        The main method that looks at the <limit> most recent paystubs
        available and sees which (if any) we need to download copies of.
        """
        self.log_in()
        self.get_all_the_cookies()
        self.get_uid()
        self.get_paystub_urls(limit)

        for date, url in self.get_needed_paystubs():
            self.download_paystub(date, url)


@click.command()
@click.option('--limit', default=30, help='How many paystubs back to look')
@click.option('--creds', default='./.adp-pass', help='Path to ADP credentials')
def cli(creds, limit):
    """
    After finding a file of credentials, create a requests Session and
    PayCheckFetcher and ask the PayCheckFetcher to do its thing.
    """
    if not os.path.exists(creds):
        print("Couldn't find creds!")
        return -1

    username, password = open(creds).read().split('\n')[0:2]

    with requests.Session() as session:
        fetcher = PayCheckFetcher(username, password, session)
        fetcher.download_needed(limit)
