"""Loopback-only, read-only host for the upstream RNL viewer and drawing inputs.

The viewer is cached unchanged from its official site, pinned per file. The
repository records the lock, not a second vendored frontend or its binary WASM.
Only explicitly listed public circuit/display inputs are served; never the
whole workspace, PDK, simulation results, SSH configuration, or OA databases.
"""
from concurrent.futures import ThreadPoolExecutor
import hashlib
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import json
import mimetypes
from pathlib import Path
from urllib.parse import unquote,urlsplit
from urllib.request import urlopen

def cache(root):
    lock=json.loads((root/'tools/saradc/rnl_viewer.lock.json').read_text(encoding='utf-8'))
    folder=root/('work/tools/rnl-viewer-'+lock['version'])
    def restore(item):
        rel,row=item;path=(folder/rel).resolve()
        if not path.is_relative_to(folder.resolve()):raise ValueError('Invalid viewer lock path')
        if path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest()==row['sha256']:return
        data=urlopen(lock['url']+rel,timeout=30).read()
        if len(data)!=row['size'] or hashlib.sha256(data).hexdigest()!=row['sha256']:
            raise ValueError('Upstream viewer changed: '+rel+'. Keep the pinned cache or explicitly update the lock.')
        path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
    with ThreadPoolExecutor(max_workers=4) as pool:list(pool.map(restore,lock['files'].items()))
    return folder,lock

def public_files(root,folder,lock):
    workspace=json.loads((root/'design/rnl/workspace.json').read_text(encoding='utf-8'))
    files={'/':root/'docs/schematics/index.html','/index.html':root/'docs/schematics/index.html'}
    for row in workspace['files']:
        path=(root/row['path']).resolve()
        if not path.is_relative_to(root.resolve()):raise ValueError('Invalid schematic workspace path')
        files['/repo/'+row['path']]=path
    files['/repo/design/rnl/workspace.json']=root/'design/rnl/workspace.json'
    for rel in lock['files']:files['/viewer/'+rel]=folder/rel
    files['/viewer/']=folder/'index.html'
    candidate_index=root/'work/drawings/candidates/index.json'
    if candidate_index.is_file():
        for url,rel in json.loads(candidate_index.read_text(encoding='utf-8')).items():
            p=(root/rel).resolve()
            if not p.is_relative_to((root/'work/drawings/candidates').resolve()):raise ValueError('Invalid candidate display path')
            files[url]=p
    return files

def serve(root,port=8875):
    root=Path(root).resolve();folder,lock=cache(root);files=public_files(root,folder,lock)
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            path=files.get(unquote(urlsplit(self.path).path))
            if not path or not path.is_file():self.send_error(404);return
            data=path.read_bytes()
            if path.name=='workspace.json':
                manifest=json.loads(data)
                manifest['base']='http://127.0.0.1:%d/'%port+('repo/' if path==root/'design/rnl/workspace.json' else 'candidate/'+path.parent.name+'/')
                data=json.dumps(manifest).encode('utf-8')
            mime={'.js':'text/javascript','.wasm':'application/wasm','.scs':'text/plain','.rnl':'text/plain'}.get(path.suffix,mimetypes.guess_type(str(path))[0] or 'application/octet-stream')
            self.send_response(200);self.send_header('Content-Type',mime)
            self.send_header('Content-Length',str(len(data)));self.send_header('Cache-Control','no-cache')
            self.end_headers();self.wfile.write(data)
        def log_message(self,format,*args):
            if args and str(args[1]) not in {'200','304'}:super().log_message(format,*args)
    server=ThreadingHTTPServer(('127.0.0.1',port),Handler)
    print('SAR8 RNL: http://127.0.0.1:%d/ (read-only; Ctrl+C stops this viewer)'%port,flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()
