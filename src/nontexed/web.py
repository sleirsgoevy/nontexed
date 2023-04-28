import http.server, nontexed, io, html, traceback, socketserver, threading, os.path

nontexed.print = object.__init__

class ErrorDict(dict):
    def __init__(self, code): self.code = code
    def __contains__(self, key): return True
    def __getitem__(self, key): return self.code

class StringIONonClose(io.StringIO):
    def close(self): pass
    def __exit__(self, *args): pass

def inmem_fmt(data):
    files = {}
    def do_open(x, y):
        x = x.replace(os.path.sep, '/')
        assert y == 'w'
        files[x] = StringIONonClose()
        return files[x]
    nontexed.main(io.StringIO(data), '/data', do_open=do_open)
    return {k: v.getvalue() for k, v in files.items()}

HTML = b"""\
<html>
<head>
<title>NontexedWeb</title>
</head>
<body style="padding: 0">
<table style="margin: 0; width: 100%; height: 100%">
<tr>
<td width="50%" style="position: relative; padding: 0">
<textarea id="nontexed_in" style="margin: 0; width: 100%; height: 100%" onkeyup="update(); return true" onmouseup="update(); return true">CUR_DATA</textarea>
</td>
<td width="50%" style="position: relative; padding: 0">
<iframe id="iframe" src="data/index.html" style="margin: 0; width: 100%; height: 100%"></iframe>
</td>
</tr>
</table>
<script>
function update()
{
    var xhr = new XMLHttpRequest();
    xhr.open('POST', 'update', true);
    xhr.onload = function()
    {
        var iframe = document.getElementById('iframe');
        if(xhr.responseText)
            iframe.contentWindow.document.location.href = document.location.href + xhr.responseText.substr(1);
        else
            iframe.contentWindow.document.location.href = iframe.contentWindow.document.location.href;
    }
    xhr.send(document.getElementById('nontexed_in').value);
}
</script>
</body>
</html>
"""

HTML_LIVE = b"""\
<html>
<head>
<title>NontexedWeb</title>
</head>
<body style="padding: 0">
<iframe id="iframe" src="data/index.html" style="margin: 0; width: 100%; height: 100%"></iframe>
<script>
function update()
{
    var xhr = new XMLHttpRequest();
    xhr.open('POST', 'longpoll', true);
    xhr.onload = function()
    {
        if(xhr.responseText == 'ok')
        {
            var iframe = document.getElementById('iframe');
            iframe.contentWindow.document.location.href = iframe.contentWindow.document.location.href;
        }
        update();
    }
    xhr.onerror = update.bind(window);
    xhr.send('');
}
update();
</script>
</body>
</html>
"""

class NontexedRequestHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            if self.client_address[0] != '127.0.0.1':
                self.send_response(302)
                self.send_header('Location', 'live')
                self.end_headers()
                return
            data = HTML.replace(b'CUR_DATA', html.escape(self.server.cur_data).encode('utf-8'))
        elif self.path == '/live':
            data = HTML_LIVE
        elif self.path.startswith('/data/') and self.path in self.server.files:
            ff = self.server.files
            data = self.server.files[self.path].encode('utf-8')
            if self.client_address[0] != '127.0.0.1' and isinstance(ff, ErrorDict):
                self.send_error(500)
                return
        else:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)
    def do_POST(self):
        if self.path == '/longpoll':
            lk = threading.Lock()
            lk.acquire()
            self.server.lp_queue.append(lk)
            if lk.acquire(timeout=15):
                ans = b'ok'
            else:
                ans = b'error'
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain')
            self.send_header('Content-Length', str(len(ans)))
            self.end_headers()
            self.wfile.write(ans)
        elif self.path != '/update':
            self.send_error(405)
        else:
            if self.client_address[0] != '127.0.0.1':
                self.send_error(403)
                return
            while True:
                try: self.server.lp_queue.pop().release()
                except IndexError: break
            with self.server.main_lock:
                l = int(self.headers.get('Content-Length', -1))
                data = b''
                while len(data) < l: data += self.rfile.read(l - len(data))
                data = data.decode('utf-8')
                self.server.cur_data = data
                try:
                    old_files = self.server.files
                    self.server.files = inmem_fmt(data)
                    keys1 = list(sorted(list(old_files)))
                    keys2 = list(sorted(list(self.server.files)))
                    if keys1 == keys2:
                        keys = [i for i in keys1 if old_files[i] != self.server.files[i]]
                        if len(keys) == 1:
                            ans = keys[0].encode('utf-8')
                            self.send_response(200)
                            self.send_header('Content-Type', 'text/plain; charset=utf-8')
                            self.send_header('Content-Length', str(len(ans)))
                            self.end_headers()
                            self.wfile.write(ans)
                            return
                except Exception as e:
                    self.server.files = ErrorDict('<pre>'+html.escape(traceback.format_exc())+'</pre>')
                self.send_response(200)
                self.send_header('Content-Type', 'text/plain')
                self.send_header('Content-Length', '0')
                self.end_headers()

class NontexedServer(socketserver.ThreadingMixIn, http.server.HTTPServer): pass

def create_server(addr, handler=NontexedRequestHandler):
    srv = NontexedServer(addr, handler)
    srv.files = {}
    srv.main_lock = threading.Lock()
    srv.lp_queue = []
    srv.cur_data = ''
    return srv

def main(*args):
    if '-b' in args:
        import webbrowser
        webbrowser.open('http://127.0.0.1:8080')
    if '--bind' in args:
        try: addr = ('', int(args[args.index('--bind')+1]))
        except IndexError: addr = ('', 8080)
    else: addr = ('127.0.0.1', 8080)
    srv = create_server(addr)
    srv.serve_forever()

if __name__ == '__main__':
    import sys
    main(*sys.argv[1:])
