"""Check a player's POI corrections; --apply merges reviewed corrections for shipping."""
from pathlib import Path
import argparse
import importlib.util
import json

ADDON=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('poi_builder',ADDON/'tools/build_pois.py')
B=importlib.util.module_from_spec(spec);spec.loader.exec_module(B)

def validate(document):
    lua=B.P.runtime();editor=lua.eval("require('src.poi_edits')")
    def table(v):
        if isinstance(v,dict):return lua.table_from({k:table(x) for k,x in v.items()})
        if isinstance(v,list):return lua.table_from([table(x) for x in v])
        return v
    changes=editor.validate(table(document),lua.eval("require('data.pois')"),lua.eval("require('src.catalog')"),lua.eval("require('data.world_art')"))
    result=B.P.plain(changes)
    # Lua's empty table has no array/object distinction; the interchange schema does.
    return {key:result[key] or {} for key in ('world','stops')}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('file',type=Path)
    parser.add_argument('--apply',action='store_true',help='merge corrections and rebuild shipped POIs after review')
    args=parser.parse_args()
    changes=validate(json.loads(args.file.read_text(encoding='utf-8-sig')))
    print(json.dumps(changes,indent=2,sort_keys=True))
    if args.apply:
        path=ADDON/'annotations/poi/corrections.json'
        existing=validate(json.loads(path.read_text())) if path.exists() else {'world':{},'stops':{}}
        for kind in changes:
            for key,value in changes[kind].items():existing[kind][key]=existing[kind].get(key,{})|value
        document={'schema_version':1,'changes':existing}
        validate(document)
        path.write_text(json.dumps(document,indent=2,sort_keys=True)+'\n',encoding='utf-8',newline='\n')
        B.build()
    else:print('Check only: no files changed. Review the values, then use --apply to ship them.')

if __name__=='__main__':main()
