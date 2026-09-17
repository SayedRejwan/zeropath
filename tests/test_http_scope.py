import httpx
import pytest

from zeropath.tools.http_tools import HttpTools


@pytest.mark.parametrize('url', ['ftp://127.0.0.1', 'http://user:pass@localhost', 'http://example.com', 'http://localhost/base', 'http://localhost?x=1'])
def test_invalid_base(url):
    with pytest.raises(ValueError):
        HttpTools(url)


@pytest.mark.parametrize('path', ['http://localhost/room/a', '//localhost/room/a', 'room/a', '/room/../other', '/room/%2e%2e/other', '/room/%252e%252e/other', '/room\\other', '/room/%5cother', '/room/%ZZ', '/room/%', '/room//other', '/room/a#fragment', '/room/a\n'])
def test_invalid_paths_never_sent(path):
    sent = []
    tool = HttpTools('http://localhost', scope_prefix='/room', transport=httpx.MockTransport(lambda req: sent.append(req)))
    with pytest.raises(ValueError):
        tool.get(path)
    assert sent == []
    tool.close()


@pytest.mark.parametrize('destination', ['http://example.com/room/a', 'http://127.0.0.1/room/a', 'http://localhost:9999/room/a', 'https://localhost/room/a', '/other/a', '/roommate/a', '/room/%2e%2e/other', '/room/../other', '/room/%252e%252e/other', 'http://user:pass@localhost/room/a'])
def test_redirects_blocked_before_destination_transport(destination):
    sent = []
    def handler(request):
        sent.append(str(request.url))
        return httpx.Response(302, headers={'location': destination})
    tool = HttpTools('http://localhost', scope_prefix='/room', transport=httpx.MockTransport(handler))
    with pytest.raises(ValueError):
        tool.get('/room/start')
    assert sent == ['http://localhost/room/start']
    tool.close()


def test_valid_redirect_cookie_and_auth():
    sent = []
    def handler(request):
        sent.append(request)
        if request.url.path == '/room/start':
            return httpx.Response(302, headers={'location': 'end', 'set-cookie': 'session=ok; Path=/'})
        return httpx.Response(200, json={'ok': True})
    tool = HttpTools('http://localhost', scope_prefix='/room', transport=httpx.MockTransport(handler))
    tool.memory.basic_auth_user, tool.memory.basic_auth_pass = 'user', 'pass'
    tool.memory.headers['X-Test'] = 'kept'
    assert tool.get('/room/start').status_code == 200
    assert len(sent) == 2
    assert sent[-1].url.path == '/room/end'
    assert sent[-1].headers['cookie'] == 'session=ok'
    assert sent[-1].headers['authorization'].startswith('Basic ')
    assert sent[-1].headers['X-Test'] == 'kept'
    tool.close()


def test_post_and_direct_client_calls_are_guarded():
    sent = []
    def handler(request):
        sent.append(request)
        return httpx.Response(200)
    tool = HttpTools('http://localhost', scope_prefix='/room', transport=httpx.MockTransport(handler))
    assert tool.post_json('/room/action', {'test': True}).status_code == 200
    with pytest.raises(ValueError):
        tool.post_json('/other/action', {})
    with pytest.raises(ValueError):
        tool.client.get('http://example.com/room/action')
    assert len(sent) == 1
    tool.close()
