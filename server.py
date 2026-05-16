#!/usr/bin/env python3
# Run: python3 server.py  →  open http://localhost:8080

import json, socket, os, ssl, urllib.request, urllib.error
from http.server import HTTPServer, SimpleHTTPRequestHandler

ssl._create_default_https_context = ssl._create_unverified_context

PORT = int(os.environ.get('PORT', 8080))

class Handler(SimpleHTTPRequestHandler):
    def log_message(self, fmt, *args): pass

    def send_cors(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_cors()
        self.end_headers()

    def do_POST(self):
        if self.path != '/api/claude':
            self.send_error(404)
            return
        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length)
        try:
            data = json.loads(body)
            api_key = data.get('apiKey', '').strip()
            word    = data.get('word', '').strip()
            context = data.get('context', '').strip()[:500]
            if not api_key:
                return self._err(400, 'API key required')
            result = self._call_claude(api_key, word, context)
            self._ok(result)
        except urllib.error.HTTPError as e:
            self._err(e.code, f'Anthropic error: {e.read().decode()}')
        except Exception as e:
            self._err(500, str(e))

    def _call_claude(self, api_key, word, context):
        prompt = f'''Look up the English word "{word}" used in this context:
"{context}"

Return ONLY valid JSON with exactly these fields:
{{
  "ipa": "IPA transcription e.g. /wɜːrd/",
  "translation": "Russian translation for this context",
  "synonyms": ["syn1", "syn2", "syn3"],
  "collocations": ["collocation 1", "collocation 2", "collocation 3"]
}}'''
        payload = json.dumps({
            'model': 'claude-haiku-4-5-20251001',
            'max_tokens': 400,
            'messages': [{'role': 'user', 'content': prompt}]
        }).encode()
        req = urllib.request.Request(
            'https://api.anthropic.com/v1/messages', data=payload,
            headers={'Content-Type': 'application/json',
                     'x-api-key': api_key,
                     'anthropic-version': '2023-06-01'})
        with urllib.request.urlopen(req, timeout=15) as resp:
            text = json.loads(resp.read())['content'][0]['text'].strip()
            if text.startswith('```'):
                text = text.split('```')[1]
                if text.startswith('json'): text = text[4:]
            return json.loads(text.strip())

    def _ok(self, data):
        body = json.dumps(data).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_cors()
        self.end_headers()
        self.wfile.write(body)

    def _err(self, code, msg):
        body = json.dumps({'error': msg}).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_cors()
        self.end_headers()
        self.wfile.write(body)

def local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]; s.close(); return ip
    except: return '127.0.0.1'

if __name__ == '__main__':
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    ip = local_ip()
    print(f'\n  Article Reader')
    print(f'  Desktop : http://localhost:{PORT}')
    print(f'  iPad    : http://{ip}:{PORT}')
    print(f'  Ctrl+C to stop\n')
    try: HTTPServer(('0.0.0.0', PORT), Handler).serve_forever()
    except KeyboardInterrupt: print('Stopped.')
