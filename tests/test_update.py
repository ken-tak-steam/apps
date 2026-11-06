import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('catalog',Path(__file__).parents[1]/'scripts/update.py')
catalog=importlib.util.module_from_spec(spec);spec.loader.exec_module(catalog)
class CatalogTests(unittest.TestCase):
    def test_render_escapes_names_and_provides_download_fallback(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            (root/'template.html').write_text('{{COUNT}} {{CARDS}} {{DATE}}')
            with patch.object(catalog,'ROOT',root):
                catalog.render([dict(repo='sample',name='<script>alert(1)</script>',description='<img>',url=None,download=None)])
            html=(root/'index.html').read_text()
            self.assertNotIn('<script>',html)
            self.assertIn('&lt;script&gt;',html)
            self.assertIn('Web版は未公開',html)
            self.assertIn('/sample/blob/HEAD/index.html',html)
    def test_discovery_filters_and_uses_pages_status(self):
        repos=[dict(name='apps',fork=False,archived=False),dict(name='fork',fork=True,archived=False),dict(name='old',fork=False,archived=True)]
        repos += [dict(name=n,fork=False,archived=False,default_branch='main',has_pages=p,description='') for n,p in [('published',True),('unpublished',False)]]
        def fake_get(path):
            if path.startswith('/users/'): return repos
            return [dict(name='index.html'),dict(name='download.html')]
        import io
        def fake_open(*args,**kwargs): return io.BytesIO('<title>見本君｜案内</title>'.encode())
        with patch.object(catalog,'get',fake_get),patch.object(catalog.urllib.request,'urlopen',fake_open):
            result=catalog.discover()
        self.assertEqual(len(result),2)
        self.assertEqual(result[0]['name'],'見本君')
        self.assertEqual(result[0]['download'],'https://ken-tak-steam.github.io/published/download.html')
        self.assertIsNone(result[1]['url'])
        self.assertIsNone(result[1]['download'])
if __name__=='__main__': unittest.main()
