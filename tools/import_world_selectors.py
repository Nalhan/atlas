"""Validate world selector handbacks; --apply merges reviewed bounds and rebuilds world metadata."""
from pathlib import Path
import argparse
import importlib.util
import json

ADDON=Path(__file__).resolve().parents[1]
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value
P=module('selector_annotations',ADDON/'tools/annotations.py')

def validate(doc):
    lua=P.runtime();edits=lua.eval("require('src.world_selectors')")
    def table(v):
        if isinstance(v,dict):return lua.table_from({k:table(x) for k,x in v.items()})
        if isinstance(v,list):return lua.table_from([table(x) for x in v])
        return v
    return P.plain(edits.validate(table(doc),lua.eval("require('data.world_art')")))

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('file',type=Path);parser.add_argument('--apply',action='store_true')
    args=parser.parse_args();changes=validate(json.loads(args.file.read_text(encoding='utf-8-sig')))
    print(json.dumps(changes,indent=2,sort_keys=True))
    if args.apply:
        path=ADDON/'annotations/world-selectors/corrections.json'
        previous=validate(json.loads(path.read_text(encoding='utf-8'))) if path.exists() else {}
        doc={'schema_version':1,'kind':'world_selectors','selectors':previous|changes}
        validate(doc);path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps(doc,indent=2,sort_keys=True)+'\n',encoding='utf-8',newline='\n')
        module('selector_world_builder',ADDON/'tools/build_world_art.py').build()
    else:print('Check only: no files changed. Review the bounds, then use --apply to ship them.')

if __name__=='__main__':main()
