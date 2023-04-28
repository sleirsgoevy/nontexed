import nontexedweb, urllib.request, json, random, PIL.Image, subprocess, base64, io, numpy, os, sys

with open(sys.argv[1]) as file: botapikey = file.read().strip()

def do_request(method, arg):
    return json.loads(urllib.request.urlopen(urllib.request.Request('https://api.telegram.org/bot'+botapikey+'/'+method, json.dumps(arg).encode('utf-8'), headers={'Content-Type': 'application/json'}), timeout=10).read().decode('utf-8'))

def do_request_multipart(method, arg, param, filename, doc):
    mpart = [b'']+[('"%s"\r\n\r\n%s\r\n'%(k, v)).encode('utf-8') for k, v in arg.items()]+[('"%s"; filename="%s"\r\n\r\n'%(param, filename)).encode('utf-8')+doc+b'\r\n']
    r = b''
    while any(r in i for i in mpart):
        r = bytes(random.randrange(48, 58) for i in range(20))
    ans = (b'--'+r+b'\r\nContent-Disposition: form-data; name=').join(mpart)+b'--'+r+b'--\r\n'
    return json.loads(urllib.request.urlopen(urllib.request.Request('https://api.telegram.org/bot'+botapikey+'/'+method, ans, headers={'Content-Type': 'multipart/form-data; boundary='+r.decode('ascii')})).read().decode('utf-8'))

def render_page(html):
    html = html.split('<')
    html = html[0]+'<'+'<'.join(i.replace('black', 'white')+'>'+j for x in html[1:] for i, j in (x.split('>', 1),))
    url = 'data:text/html;charset=utf-8,'+urllib.parse.urlencode({'x': html})[2:].replace('+', '%20')
    p = subprocess.Popen(('phantomjs', 'render-it.js'), stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    data = p.communicate(url.encode('ascii'))[0].split(b'\n')
    print(data[1])
    fp = io.BytesIO(base64.b64decode(data[0]))
    img = PIL.Image.open(fp).convert("RGBA")
    wh, hh = img.size
    np = numpy.array(img.getdata()).reshape(hh, wh, 4)[::-1,::-1,:]
    h = hh - (np != 0).argmax() // (wh * 4)
    w = wh # - (np.transpose((1, 0, 2)) != 0).argmax() // (hh * 4)
    print(w, h)
    #wl = 0
    #while wh - wl > 1:
    #    m = (wh + wl) // 2
    #    if (np[:,m:] != 0).any():
    #        wl = m
    #    else:
    #        wh = m
    #hl = 0
    #while hh - hl > 1:
    #    m = (hh + hl) // 2
    #    if (np[m:,:wh] != 0).any():
    #        hl = m
    #    else:
    #        hh = m
    ans = io.BytesIO()
    img.crop((0, 0, w, h)).save(ans, 'webp')
    return ans.getvalue()

offset = 0

while True:
    try: data = do_request('getUpdates', {'offset': offset, 'timeout': 30})
    except Exception: continue
    for i in data['result']:
        print(i)
        offset = max(offset, i['update_id']+1)
        if 'message' in i:
            chat_id = i['message']['chat']['id']
            try: text = i['message']['text']
            except KeyError:
                do_request('sendMessage', {'chat_id': chat_id, 'text': 'Я понимаю только текст!'})
                continue
            if len(text) > 4096:
                do_request('sendMessage', {'chat_id': chat_id, 'text': 'Сообщение слишком длинное!'})
                continue
            try: files = nontexedweb.inmem_fmt('[[data]]\n'+text)
            except Exception:
                do_request('sendMessage', {'chat_id': chat_id, 'text': 'Произошла ошибка, но стектрейс я не покажу.'})
                continue
            pic = render_page(files['/data/data.html'])
            print('sending...')
            do_request_multipart('sendSticker', {'chat_id': chat_id}, 'sticker', 'sticker.webp', pic)
            print('done')
        elif 'inline_query' in i:
            if not os.fork(): break
    else: continue
    break

print('ti govno')
query_id = i['inline_query']['id']
try: text = i['inline_query']['query']
except KeyError: pass
else:
    if len(text) <= 4096:
        try: files = nontexedweb.inmem_fmt('[[data]]\n'+text)
        except Exception: pass
        else:
            pic = render_page(files['/data/data.html'])
            file_id = do_request_multipart('sendSticker', {'chat_id': -1001179531226}, 'sticker', 'sticker.webp', pic)['result']['sticker']['file_id']
            try: do_request('answerInlineQuery', {'inline_query_id': query_id, 'results': [{'type': 'sticker', 'id': os.urandom(16).hex(), 'sticker_file_id': file_id}]})
            except Exception as e: print(e.read())
            exit()
do_request('answerInlineQuery', {'inline_query_id': query_id, 'results': []})
