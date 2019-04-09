import json
import mock
import pytest
import redo
import requests


# mock redo library, to make test faster
real_retry = redo.retry


def fake(*args, **kwargs):
    kwargs.pop('sleeptime')
    kwargs.pop('max_sleeptime')
    return real_retry(sleeptime=1, max_sleeptime=1, jitter=1, *args, **kwargs)


redo.retry = fake


def test_release_v2_class(mocker):
    from src.shipitapi.shipitapi import Release_V2

    class MockResponse(requests.Response):
        content = json.dumps({'success': True, 'test': True})

        def __init__(self):
            super(MockResponse, self).__init__()
            self.status_code = 200

    # create release class
    release = Release_V2(
            taskcluster_client_id='some-id', taskcluster_access_token='some-token',
            api_root='https://www.apiroot.com/')
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
        data=None,
        headers=None,
        method='GET',
        timeout=mock.ANY,
        verify=mock.ANY,
        url=correct_url
    )
    assert release.session.request.call_count == api_call_count + 1
    api_call_count += 1

    # test that update call correct URL
    ret = release.update_status(release_name, status='success test', rebuild_product_details=False)
    ret_json = json.loads(ret)
    assert ret_json['test'] is True
    correct_url = 'https://www.apiroot.com/releases/releaseName'
    release.session.request.assert_called_with(
        data=json.dumps({'status': 'success test'}),
        headers=mock.ANY,
        method='PATCH',
        timeout=mock.ANY,
        verify=mock.ANY,
        url=correct_url
    )
    api_call_count += 1
    assert release.session.request.call_count == api_call_count

    # test that update triggers product details
    ret = release.update_status(release_name, status='success test', rebuild_product_details=True)
    ret_json = json.loads(ret)
    assert ret_json['test'] is True
    correct_url = 'https://www.apiroot.com/product-details'
    release.session.request.assert_called_with(
        data='{}',
        headers=mock.ANY,
        method='POST',
        timeout=mock.ANY,
        verify=mock.ANY,
        url=correct_url
    )
    api_call_count += 2
    assert release.session.request.call_count == api_call_count

    # test that exception raised if error, and retry api call
    release.session.request.return_value.status_code = 400
    with pytest.raises(requests.exceptions.HTTPError):
        release.getRelease(release_name)
    correct_url = 'https://www.apiroot.com/releases/releaseName'
    release.session.request.assert_called_with(
        data=None,
        headers=None,
        method='GET',
        timeout=mock.ANY,
        verify=mock.ANY,
        url=correct_url
    )
    assert release.session.request.call_count == api_call_count + release.retries

    release.session.request.return_value.status_code = 200
    release.session.request.return_value.content = "Not JSON at all"
    with pytest.raises(json.decoder.JSONDecodeError):
        release.getRelease(release_name)
