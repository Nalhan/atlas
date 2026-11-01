from pathlib import Path
import hashlib
import importlib.util
import json
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from PIL import Image

ADDON=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('world_art_export',ADDON/'tools/export_world_art.py')
exporter=importlib.util.module_from_spec(spec);spec.loader.exec_module(exporter)

class WorldArtwork(unittest.TestCase):
    def test_pixel_crops_use_half_open_tile_bounds(self):
        self.assertEqual(exporter.tile_bounds((0,0,256,256)),(0,0,1,1))
        self.assertEqual(exporter.tile_bounds((255,255,257,257)),(0,0,2,2))
        self.assertEqual(exporter.tile_bounds((256,512,512,768)),(1,2,2,3))
        with self.assertRaises(ValueError):exporter.tile_bounds((0,0,0,256))

    def test_stitching_preserves_pixels_and_checks_source_integrity(self):
        with tempfile.TemporaryDirectory(prefix='_annotation_tmp_',dir=ADDON/'tests') as temp:
            root=Path(temp);rows=[]
            for x,y,color in ((0,0,(250,10,20)),(1,0,(10,250,20)),(0,1,(20,10,250)),(1,1,(240,220,10))):
                path=root/f'{x}-{y}.jpeg';Image.new('RGB',(256,256),color).save(path,quality=95)
                rows.append({'x':x,'y':y,'cached_path':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
            with patch.object(exporter,'ADDON',root):
                image=exporter.assemble(1,list(reversed(rows)))
                self.assertEqual(image.size,(512,512))
                for r in rows:
                    with Image.open(root/r['cached_path']) as tile:
                        self.assertEqual(image.getpixel((r['x']*256,r['y']*256)),tile.getpixel((0,0)))
                        self.assertEqual(image.getpixel((r['x']*256+255,r['y']*256+255)),tile.getpixel((255,255)))
                with self.assertRaisesRegex(ValueError,'Incomplete or duplicate'):exporter.assemble(1,rows[:-1])
                with self.assertRaisesRegex(ValueError,'Incomplete or duplicate'):exporter.assemble(1,rows+[rows[0]])
                (root/'0-0.jpeg').write_bytes(b'changed')
                with self.assertRaisesRegex(ValueError,'Source tile changed'):exporter.assemble(1,rows)

    @unittest.skipUnless(shutil.which('node'),'Node is needed for offline viewer interaction checks')
    def test_viewer_pointer_zoom_pan_and_region_jump(self):
        with tempfile.TemporaryDirectory(prefix='_annotation_tmp_',dir=ADDON/'tests') as temp:
            root=Path(temp);preview=root/'preview.jpg';Image.new('RGB',(8,8)).save(preview)
            exporter.write_viewer(root,preview,{'ronfaure-detail.png':{'bounds_pixels':[2100,2320,3900,3700]}})
            html=(root/'view-map.html').read_text(encoding='utf-8')
            self.assertNotIn('REGION_',html)
            self.assertNotIn('fetch(',html)
            program=r'''
            const vm=require('node:vm'),fs=require('node:fs'),assert=require('node:assert/strict');
            const html=fs.readFileSync(process.argv[1],'utf8');
            const script=html.match(/<script>([\s\S]*?)<\/script>/)[1];
            const events={},elements={};let draws=0;
            const ctx={setTransform(){},fillRect(){},drawImage(){draws++}};
            const canvas={style:{},getContext(){return ctx},addEventListener(name,fn){events[name]=fn},setPointerCapture(){}};
            for(const key of ['fit','actual','ronfaure','zoom'])elements[key]={};
            elements.map=canvas;
            class MockImage{constructor(){this.width=8192;this.height=8192}set src(v){this.onload()}}
            const context=vm.createContext({document:{getElementById:id=>elements[id]},Image:MockImage,
                innerWidth:1200,innerHeight:900,devicePixelRatio:1,window:{addEventListener(){}},Math});
            vm.runInContext(script,context);
            const state=()=>JSON.parse(vm.runInContext('JSON.stringify({scale,ox,oy})',context));
            const before=state(),point=[300,250];
            events.wheel({preventDefault(){},deltaY:-200,offsetX:point[0],offsetY:point[1]});
            const after=state();assert(after.scale>before.scale);
            assert(Math.abs((point[0]-before.ox)/before.scale-(point[0]-after.ox)/after.scale)<1e-8);
            assert(Math.abs((point[1]-before.oy)/before.scale-(point[1]-after.oy)/after.scale)<1e-8);
            events.pointerdown({clientX:10,clientY:20,pointerId:1});events.pointermove({clientX:60,clientY:80});
            const moved=state();assert.equal(moved.ox-after.ox,50);assert.equal(moved.oy-after.oy,60);events.pointerup();
            elements.actual.onclick();assert.equal(state().scale,1);
            elements.ronfaure.onclick();const region=state();assert.equal(region.scale,Math.min(1200/1800,842/1380));
            elements.fit.onclick();assert.equal(state().scale,Math.min(1200/8192,842/8192));assert(draws>=5);
            '''
            completed=subprocess.run([shutil.which('node'),'-e',program,str(root/'view-map.html')],capture_output=True,text=True)
            self.assertEqual(completed.returncode,0,completed.stderr)

if __name__=='__main__':unittest.main()
