import logging
from datetime import datetime
try:
    import simplejson as json
except ImportError:
    import json
import certifi
import requests
from redo import retry


log = logging.getLogger(__name__)


def is_csrf_token_expired(token):
    """Method to check csrf token validity"""
    expiry = token.split('##')[0]
    # this comparison relies on ship-it running on UTC-based systems
    if expiry <= datetime.utcnow().strftime('%Y%m%d%H%M%S'):
        return True
    return False


class API(object):
    """A class that knows how to make requests to a Ship It server, including
    pre-retrieving CSRF tokens.

    url_template: The URL to submit to when request() is called. Standard
                    Python string interpolation can be used here
    """

    auth = None
    url_template = None

    def __init__(self, auth, api_root, ca_certs=certifi.where(), timeout=60,
                 raise_exceptions=True, retry_attempts=5, csrf_token_prefix=''):
        self.api_root = api_root.rstrip('/')
        self.auth = auth
        self.verify = ca_certs
        self.timeout = timeout
        self.raise_exceptions = raise_exceptions
        self.session = requests.session()
        self.csrf_token = None
        self.retries = retry_attempts
        self.csrf_token_prefix = csrf_token_prefix

    def request(self, params=None, data=None, method='GET',
                url_template_vars={}):
        """Before submitting the real request, a HEAD operation will be done
        on this URL. If the HEAD request succeeds, it is expected that there
        will be X-CSRF-Token and X-Data-Version headers in the response. If
        the HEAD request results in a 404, another HEAD request to /csrf_token
        will be made in attempt to get a CSRF Token.
        """
        url = self.api_root + self.url_template % url_template_vars
        if method != 'GET' and method != 'HEAD':
            if not self.csrf_token or is_csrf_token_expired(self.csrf_token):
                res = self.session.request(
                    method='HEAD', url=self.api_root + '/csrf_token',
                    verify=self.verify, timeout=self.timeout, auth=self.auth)
                if self.raise_exceptions:
                    res.raise_for_status()
                self.csrf_token = res.headers['X-CSRF-Token']
            # Some forms require the CSRF prefixed, usually with the product name
            data['{}csrf_token'.format(self.csrf_token_prefix)] = self.csrf_token
        log.debug('Request to %s', url)
        log.debug('Data sent: %s', data)

        try:
            def _req():
                req = self.session.request(
                    method=method, url=url, data=data, timeout=self.timeout,
                    verify=self.verify, auth=self.auth, params=params)
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


class Release(API):
    """Wrapper class over shipitapi API class that defines the sole method
    to update the status of the release to 'shipped'.
    """

    url_template = '/releases/%(name)s'

    def getRelease(self, name):
        resp = None
        try:
            resp = self.request(url_template_vars={'name': name})
            return json.loads(resp.content)
        except:
            log.error('Caught error while getting release', exc_info=True)
            if resp:
                log.error(resp.content)
                log.error('Response code: %d', resp.status_code)
            raise

    def update(self, name, **data):
        """Update method to change release status"""
        url_template_vars = {'name': name}
        return self.request(method='POST', data=data,
                            url_template_vars=url_template_vars).content


class NewRelease(API):
    """Wrapper class over shipitapi API class that defines the sole method
    to create a release.
    """

    url_template = '/submit_release.html'

    def submit(self, **data):
        """Submit a new release"""
        # Every form key should be prefixed with the product name. E.g "branch"
        # becomes "firefox-branch".
        product = data['product']
        prefixed_data = {}
        for key, value in data.items():
            prefixed_data['{}-{}'.format(product, key)] = value

        # We get a hard-to-parse HTML page. The consumers are to decide whether
        # they want to use the status or the content.
        return self.request(method='POST', data=prefixed_data)
