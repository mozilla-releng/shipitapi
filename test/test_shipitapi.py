import datetime
import json
import mock
import pytest
import redo
import requests
from freezegun import freeze_time


# mock redo library, to make test faster
real_retry = redo.retry


def fake(*args, **kwargs):
    kwargs.pop('sleeptime')
    kwargs.pop('max_sleeptime')
    return real_retry(sleeptime=1, max_sleeptime=1, jitter=1, *args, **kwargs)


redo.retry = fake


def create_token(expiry):  # expiry is in UTC
    """
    csrf token format is %Y%m%d%H%M%S##...
    """
    return expiry.strftime('%Y%m%d%H%M%S') + '##....'


@freeze_time('2018-10-27 00:00:00')
def test_csrf_token_expired(mocker):
    from src.shipitapi.shipitapi import is_csrf_token_expired

    now = datetime.datetime.utcnow()
    tomorrow = now + datetime.timedelta(days=1)

    # assert token is not expired if expiry date is tomorrow
    token = create_token(expiry=tomorrow)
    assert is_csrf_token_expired(token) is False

    # assert token is not expired if expiry date is 1 second after now
    token = create_token(expiry=now + datetime.timedelta(seconds=1))
    assert is_csrf_token_expired(token) is False

    # assert token is expired if expiry date is now
    token = create_token(expiry=now)
    assert is_csrf_token_expired(token) is True

    # assert token is expired if expiry date is 1 second before now
    token = create_token(expiry=now - datetime.timedelta(seconds=1))
    assert is_csrf_token_expired(token) is True

    # assert token is expired if exipry date is yesterday
    token = create_token(expiry=now - datetime.timedelta(days=1))
    assert is_csrf_token_expired(token) is True


def test_release_class(mocker):
    from src.shipitapi.shipitapi import Release

    class MockResponse(requests.Response):
        content = json.dumps({'success': True, 'test': True})

        def __init__(self):
            super(MockResponse, self).__init__()
            self.headers = {
                'X-CSRF-Token': 'csrftoken'
            }
            self.status_code = 200

    # create release class
    release = Release(auth='authTest', api_root='https://www.apiroot.com/')
    # mock requests library
    mocker.patch.object(release, 'session')
    release_name = 'releaseName'
    release.session.request.return_value = MockResponse()
    api_call_count = 0

    # test that getRelease call correct URL
    ret = release.getRelease(release_name)
    assert ret['test'] is True
    correct_url = 'https://www.apiroot.com/releases/releaseName'
    release.session.request.assert_called_with(
        auth='authTest',
        data=mock.ANY,
        method='GET',
        params=mock.ANY,
        timeout=mock.ANY,
        verify=mock.ANY,
        url=correct_url
    )
    assert release.session.request.call_count == api_call_count + 1
    api_call_count += 1

    # test that update call correct URL
    ret = release.update(release_name, status='success test')
    ret_json = json.loads(ret)
    assert ret_json['test'] is True
    correct_url = 'https://www.apiroot.com/releases/releaseName'
    release.session.request.assert_called_with(
        auth='authTest',
        data={'status': 'success test', 'csrf_token': 'csrftoken'},
        method='POST',
        params=mock.ANY,
        timeout=mock.ANY,
        verify=mock.ANY,
        url=correct_url
    )
    assert release.session.request.call_count == api_call_count + 2
    api_call_count += 2

    # test that exception raised if error, and retry api call
    release.session.request.return_value.status_code = 400
    with pytest.raises(requests.exceptions.HTTPError):
        release.getRelease(release_name)
    correct_url = 'https://www.apiroot.com/releases/releaseName'
    release.session.request.assert_called_with(
        auth='authTest',
        data=mock.ANY,
        method='GET',
        params=mock.ANY,
        timeout=mock.ANY,
        verify=mock.ANY,
        url=correct_url
    )
    assert release.session.request.call_count == api_call_count + release.retries


def test_new_release_class(mocker):
    from src.shipitapi.shipitapi import NewRelease

    class MockResponse(requests.Response):
        content = json.dumps({'success': True, 'test': True})

        def __init__(self):
            super(MockResponse, self).__init__()
            self.headers = {
                'X-CSRF-Token': 'csrftoken'
            }
            self.status_code = 200

    # create release class
    release = NewRelease(auth='authTest', api_root='https://www.apiroot.com/')
    # mock requests library
    mocker.patch.object(release, 'session')
    product_name = 'product_name'
    release.session.request.return_value = MockResponse()
    api_call_count = 0

    # test that getRelease call correct URL
    resp = release.submit(product=product_name, testkey='testval')
    ret = json.loads(resp.content)
    assert ret['test'] is True
    correct_url = 'https://www.apiroot.com/submit_release.html'
    data = {
        product_name + '-product': product_name,
        product_name + '-testkey': 'testval',
        'csrf_token': 'csrftoken'
    }
    release.session.request.assert_called_with(
        auth='authTest',
        data=data,
        method='POST',
        params=mock.ANY,
        timeout=mock.ANY,
        verify=mock.ANY,
        url=correct_url
    )
    assert release.session.request.call_count == api_call_count + 2
    api_call_count += 2

    # test that exception raised if error, and retry api call
    release.session.request.return_value.status_code = 400
    with pytest.raises(requests.exceptions.HTTPError):
        release.submit(product=product_name, testkey='testval')
    correct_url = 'https://www.apiroot.com/submit_release.html'
    release.session.request.assert_called_with(
        auth='authTest',
        data=data,
        method='POST',
        params=mock.ANY,
        timeout=mock.ANY,
        verify=mock.ANY,
        url=correct_url
    )
    assert release.session.request.call_count == api_call_count + release.retries
