"""真实 HTTP 传输测试，目标仅本机模拟接口，不消耗账户费用。"""
import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from zhiwei import ai


class Handler(BaseHTTPRequestHandler):
    received = None
    def log_message(self, *args):
        pass
    def do_POST(self):
        Handler.received = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        payload = {'choices': [{'message': {'content': '本机传输验收通过'}}], 'usage': {'prompt_tokens': 12, 'completion_tokens': 8}}
        body = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(body)


class LiveTransportTests(unittest.TestCase):
    def test_real_local_http_chat(self):
        server = HTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            result = ai.chat({'provider':'兼容接口', 'model':'test-model', 'url':f'http://127.0.0.1:{server.server_port}/v1'},
                [{'role':'user','content':'测试'}], '')
            self.assertEqual(result['text'], '本机传输验收通过')
            self.assertEqual(Handler.received['messages'][-1]['content'], '测试')
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)
