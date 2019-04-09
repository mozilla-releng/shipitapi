import logging
import json

import certifi
import mohawk
import requests
from redo import retry

log = logging.getLogger(__name__)


class Release_V2(object):
    """A class that knows how to make requests to a Ship It v2 server, including
    generating hawk headers.
    """

    def __init__(
        self, taskcluster_client_id, taskcluster_access_token, api_root,
        ca_certs=certifi.where(), timeout=60, raise_exceptions=True,
        retry_attempts=5
    ):
        self.taskcluster_client_id = taskcluster_client_id
        self.taskcluster_access_token = taskcluster_access_token
        self.api_root = api_root.rstrip('/')
        self.verify = ca_certs
        self.timeout = timeout
        self.raise_exceptions = raise_exceptions
        self.retries = retry_attempts
        self.session = requests.session()

    @staticmethod
    def _get_taskcluster_headers(request_url, method, content,
                                 taskcluster_client_id, taskcluster_access_token):
        hawk = mohawk.Sender(
            {
                'id': taskcluster_client_id,
                'key': taskcluster_access_token,
                'algorithm': 'sha256',
            },
            request_url,
            method,
            content,
            content_type='application/json',
        )
        return {
            'Authorization': hawk.request_header,
            'Content-Type': 'application/json',
        }

    def _request(self, api_endpoint, data=None, method='GET'):
        url = '{}{}'.format(self.api_root, api_endpoint)
        if method.upper() not in ('GET', 'HEAD'):
            headers = self._get_taskcluster_headers(
                url, method, data, self.taskcluster_client_id,
                self.taskcluster_access_token)
        else:
            headers = None
        try:
            def _req():
                req = self.session.request(
                    method=method, url=url, data=data, timeout=self.timeout,
                    verify=self.verify, headers=headers)
                if self.raise_exceptions:
                    req.raise_for_status()
                return req

            return retry(_req, sleeptime=5, max_sleeptime=15,
                         retry_exceptions=(requests.HTTPError,
                                           requests.ConnectionError),
                         attempts=self.retries)
        except requests.HTTPError as err:
            log.error('Caught HTTPError: %d %s',
                      err.response.status_code, err.response.content,
                      exc_info=True)
            raise

    def getRelease(self, name):
        resp = None
        try:
            resp = self._request(api_endpoint='/releases/{}'.format(name))
            return json.loads(resp.content)
        except Exception:
            log.error('Caught error while getting release', exc_info=True)
            if resp:
                log.error(resp.content)
                log.error('Response code: %d', resp.status_code)
            raise

    def update_status(self, name, status, rebuild_product_details=True):
        """Update release status"""
        data = json.dumps({'status': status})
        res = self._request(
            api_endpoint='/releases/{}'.format(name), method='PATCH', data=data).content
        if rebuild_product_details:
            self._request(api_endpoint='/product-details', method='POST', data='{}')
        return res
