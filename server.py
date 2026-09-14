"""Loopback-only prototype. No cloud hosting or production authentication."""
import argparse,json,secrets
from http.server import HTTPServer,BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlsplit
from claim_app import predict
from evaluate_labels import score
ROOT=Path(__file__).resolve().parent
MAX_BYTES=2_000_000
MAX_CASES=1000

class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):pass # Do not log submitted evidence or labels.
    def respond(self,status,data,ctype='application/json'):
        body=data if isinstance(data,bytes) else json.dumps(data,allow_nan=False).encode()
        self.send_response(status);self.send_header('Content-Type',ctype)
        self.send_header('Content-Length',str(len(body)));self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; object-src 'none'; frame-ancestors 'none'")
        self.end_headers();self.wfile.write(body)
    def valid_host(self):
        return self.headers.get('Host') in (f'127.0.0.1:{self.server.server_port}',f'localhost:{self.server.server_port}')
    def do_GET(self):
        if not self.valid_host():return self.respond(403,{'error':'Invalid local host'})
        route=urlsplit(self.path).path
        if route=='/api/session':return self.respond(200,{'token':self.server.token,'max_cases':MAX_CASES})
        if route=='/api/demo':return self.respond(200,json.loads((ROOT/'demo/features.json').read_text()))
        if route=='/api/demo-labels':return self.respond(200,json.loads((ROOT/'demo/labels.json').read_text()))
        assets={'/':('index.html','text/html; charset=utf-8'),'/app.js':('app.js','text/javascript; charset=utf-8'),'/style.css':('style.css','text/css; charset=utf-8')}
        if route not in assets:return self.respond(404,{'error':'Not found'})
        name,mime=assets[route];return self.respond(200,(ROOT/'web'/name).read_bytes(),mime)
    def do_POST(self):
        if not self.valid_host() or self.headers.get('X-Session-Token')!=self.server.token:
            return self.respond(403,{'error':'Open the local app to start a session'})
        if self.headers.get('Origin') not in (None,f'http://127.0.0.1:{self.server.server_port}',f'http://localhost:{self.server.server_port}'):
            return self.respond(403,{'error':'Cross-origin request rejected'})
        if self.headers.get('Content-Type','').split(';')[0]!='application/json':return self.respond(415,{'error':'JSON required'})
        try:
            size=int(self.headers.get('Content-Length','0'))
            if size<=0 or size>MAX_BYTES:return self.respond(413,{'error':'Request must be at most 2 MB'})
            body=json.loads(self.rfile.read(size))
            if self.path=='/api/predict':
                if isinstance(body,dict) and isinstance(body.get('examples'),list) and len(body['examples'])>MAX_CASES:
                    return self.respond(413,{'error':'Use at most 1,000 examples per run'})
                result=predict(body)
            elif self.path=='/api/evaluate':
                if len(body['predictions']['records'])>MAX_CASES or len(body['labels']['labels'])>MAX_CASES:
                    return self.respond(413,{'error':'Use at most 1,000 examples'})
                result=score(body['predictions'],body['labels'])
            else:return self.respond(404,{'error':'Not found'})
            self.respond(200,result)
        except (ValueError,TypeError,KeyError,AttributeError,OverflowError) as exc:
            self.respond(400,{'error':str(exc)[:240]})
    def setup(self):
        super().setup();self.connection.settimeout(15)

def make_server(port=8765):
    server=HTTPServer(('127.0.0.1',port),Handler);server.token=secrets.token_urlsafe(32)
    return server

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--port',type=int,default=8765);args=parser.parse_args()
    server=make_server(args.port);print(f'Logic Mastery: http://127.0.0.1:{server.server_port}',flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()
