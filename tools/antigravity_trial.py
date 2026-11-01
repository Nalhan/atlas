"""Blind, isolated Antigravity/Flash annotation trial. Never edits live addon data.

prepare copies only input maps/metadata into task directories (no reviewed answers).
run calls the installed agy CLI with a pinned model, plan mode and structured output.
evaluate compares candidates with the existing artwork-reviewed reference separately.
"""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
import argparse
import copy
import hashlib
import importlib.util
import json
import math
import re
import shutil
import subprocess
import time

ADDON=Path(__file__).resolve().parents[1]
DATA=ADDON/'annotations'
EXPERIMENT=DATA/'experiments/flash38'
MODEL='gemini-3.8-flash-medium'
spec=importlib.util.spec_from_file_location('atlas_annotations',ADDON/'tools/annotations.py')
pipeline=importlib.util.module_from_spec(spec);spec.loader.exec_module(pipeline)

def read(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def write(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_bytes((json.dumps(value,indent=2,ensure_ascii=False)+'\n').encode())
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def minimum_assignment(costs):
    """Minimum-cost rectangular assignment; no greedy entrance-pair swaps."""
    if not costs or not costs[0]:return []
    transposed=len(costs)>len(costs[0])
    matrix=list(map(list,zip(*costs))) if transposed else costs
    n,m=len(matrix),len(matrix[0]);u=[0]*(n+1);v=[0]*(m+1);p=[0]*(m+1);way=[0]*(m+1)
    for i in range(1,n+1):
        p[0]=i;j0=0;minimum=[float('inf')]*(m+1);used=[False]*(m+1)
        while True:
            used[j0]=True;i0=p[j0];delta=float('inf');j1=0
            for j in range(1,m+1):
                if used[j]:continue
                current=matrix[i0-1][j-1]-u[i0]-v[j]
                if current<minimum[j]:minimum[j]=current;way[j]=j0
                if minimum[j]<delta:delta=minimum[j];j1=j
            for j in range(m+1):
                if used[j]:u[p[j]]+=delta;v[j]-=delta
                else:minimum[j]-=delta
            j0=j1
            if p[j0]==0:break
        while True:
            j1=way[j0];p[j0]=p[j1];j0=j1
            if j0==0:break
    result=[(p[j]-1,j-1) for j in range(1,m+1) if p[j]]
    return [(j,i) for i,j in result] if transposed else result
def schema(job):
    coord={'type':'array','items':{'type':'number','minimum':0,'maximum':512},'minItems':2,'maxItems':2}
    badge={'type':'object','properties':{'at':coord,'code':{'type':['string','null']},'printed':{'type':'boolean'}},
        'required':['at','code','printed'],'additionalProperties':False}
    endpoint={'type':'object','properties':{'map':{'type':'string'},'exit':coord,'arrival':coord,'badge':badge,
        'component':{'type':'string'},'label':{'type':['string','null']}},
        'required':['map','exit','arrival','badge','component','label'],'additionalProperties':False}
    evidence={'type':'object','properties':{k:{'type':'string'} for k in ('kind','source','detail')},
        'required':['kind','source','detail'],'additionalProperties':False}
    passage={'type':'object','properties':{'id':{'type':'string'},'a':endpoint,'b':endpoint,
        'direction':{'type':'string','enum':['both','a_to_b']},'note':{'type':'string'},
        'evidence':{'type':'array','items':evidence,'minItems':1},'uncertainties':{'type':'array','items':{'type':'string'}}},
        'required':['id','a','b','direction','note','evidence','uncertainties'],'additionalProperties':False}
    observation={'type':'object','properties':{'label':{'type':'string'},'exit':coord,
        'destination_hint':{'type':['string','null']}},'required':['label','exit','destination_hint'],'additionalProperties':False}
    inventory={'type':'object','properties':{'map':{'type':'string'},'exits':{'type':'array','items':observation}},
        'required':['map','exits'],'additionalProperties':False}
    unresolved={'type':'object','properties':{k:{'type':'string'} for k in ('map','label','reason')},
        'required':['map','label','reason'],'additionalProperties':False}
    props={'schema_version':{'type':'integer','minimum':1,'maximum':1},'job_id':{'type':'string','enum':[job]},
        'worker':{'type':'string'},'inventory':{'type':'array','items':inventory},
        'passages':{'type':'array','items':passage},'unresolved':{'type':'array','items':unresolved},
        'inspected_images':{'type':'array','items':{'type':'string'}},'limitations':{'type':'array','items':{'type':'string'}}}
    return {'type':'object','properties':props,'required':list(props),'additionalProperties':False}

def prepare():
    if any((EXPERIMENT/'runs').glob('*/result.json')):
        raise ValueError('Trial already has results; preserve its original input bundles and design')
    manifest=read(DATA/'manifest.json');seed=read(DATA/'seed.json')
    for job,keys in manifest['jobs'].items():
        bundle=EXPERIMENT/'inputs'/job;bundle.mkdir(parents=True,exist_ok=True)
        context=read(DATA/'jobs'/f'{job}.json')['context']
        chosen=list(dict.fromkeys(keys+context))
        maps={k:copy.deepcopy(manifest['maps'][k]) for k in chosen}
        for key,m in maps.items():
            for field in ('image','original_image'):
                relative=Path(m['artwork'][field]);source=DATA/relative;dest=bundle/relative
                dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,dest)
            m['artwork'].pop('path',None)
        existing=[{'a':p['a']['map'],'b':p['b']['map']} for p in seed['passages']
            if p['a']['map'] in maps and p['b']['map'] in maps]
        write(bundle/'job.json',{'schema_version':1,'job_id':job,'assigned_maps':keys,'context_maps':context,
            'existing_pairs_do_not_duplicate':existing,'maps':maps})
        write(bundle/'output.schema.json',schema(job))
        prompt=f'''You are an FFXI map annotation worker, using Antigravity with {MODEL}.
This is a bounded read-only annotation experiment. Do not edit or create files.
Inspect only job.json and the PNGs under packets in the current working directory.
Do not read any parent directories, reviewed answers, other candidates, runtime Lua,
or past conversations. Do not spawn more agents or use game-control tools.
Use the provided file/image readers only. Do not execute shell commands, Python,
dependency checks or other optional tooling. Image dimensions are in job.json.
If a tool is denied, record the limitation and return the annotation object.

Read job.json. Inventory every apparent exit on EVERY assigned map. Inspect both
replacement and original images through an image-viewing tool, not file metadata
or filename guessing. Context maps help identify connections, but do not invent
connections to maps absent from this bundle. Existing pairs listed in job.json
are already handled and must not be proposed again.

All coordinates are 512x512 reference coordinates, origin top-left. Some PNGs are
1024x1024: normalize by the actual image dimensions. The actual passage mouth,
printed badge and destination arrival focus are SEPARATE positions. Avoid placing
exits on destination text or leader arrowheads. Preserve printed numbers/letters.
Pair both endpoint maps using named exits and geometry, not matching letters alone.
Original geometry determines native floor identity: some replacement images reuse
a full cave map on an isolated apparatus floor. Do not copy exits onto such a floor.
Distinct disconnected sections of a map need distinct component IDs. Use direction
both only when supported; use a_to_b for a one-way route. A local visible badge code
is not a global passage ID. Record ambiguous floor pairings, off-pilot exits and
transport services under unresolved rather than fabricating a pair.

Return the structured object matching output.schema.json. Evidence source is one
exact relative PNG path per artwork item, never concatenated file paths. List the
images you actually inspected in inspected_images. If image tools cannot inspect
these PNGs, explicitly say so in limitations and do not guess coordinates. Provide
the actual annotations now, not a plan. No follow-up questions are needed.
'''
        (bundle/'TASK.md').write_text(prompt,encoding='utf-8')
    write(EXPERIMENT/'design.json',{'model':MODEL,'effort':'medium','jobs':list(manifest['jobs']),
        'pilot_maps':manifest['pilot_maps'],'source_manifest_sha256':sha(DATA/'manifest.json'),
        'reference_review_sha256':sha(DATA/'reviews/decisions.json'),
        'runtime_data_baseline':{'catalog.lua':read(DATA/'build.json')['runtime_sha256'],
            'regions.lua':read(DATA/'build.json')['regions_sha256']},
        'notes':['Known-answer replication, not new tags or a live traversal test.',
            'Uses corrected native-floor metadata and original images; earlier Luna prompts/inputs differed.',
            'No direct model-only head-to-head or cost advantage is established by this trial.']})
    print('Prepared isolated Flash 3.8 input bundles; no reference coordinates copied into them.',flush=True)

def parse_run(log):
    events=[];result=None
    content=log.read_text(encoding='utf-8-sig',errors='replace')
    try:
        whole=json.loads(content)
        if isinstance(whole,dict) and whole.get('status'):return [whole],whole
    except json.JSONDecodeError:pass
    for line in content.splitlines():
        try:event=json.loads(line)
        except json.JSONDecodeError:continue
        events.append(event)
        if event.get('event')=='result':result=event.get('result',event)
        elif event.get('status') in ('SUCCESS','ERROR','CANCELED','WAITING'):result=event
    return events,result
def annotation_output(result,job):
    if not result:return None
    structured=result.get('structured_output')
    if isinstance(structured,str):
        try:structured=json.loads(structured)
        except json.JSONDecodeError:structured=None
    if structured is None:
        response=result.get('response','')
        if not isinstance(response,str):return None
        response=response.strip()
        if response.startswith('```'):response='\n'.join(response.splitlines()[1:-1])
        try:structured=json.loads(response)
        except (json.JSONDecodeError,TypeError):return None
    if not isinstance(structured,dict):return None
    if structured.get('schema_version')!=1 or structured.get('job_id')!=job or not structured.get('worker'):
        return None
    if not all(isinstance(structured.get(k),list) for k in ('inventory','passages','unresolved','inspected_images','limitations')):
        return None
    # Keep questionable geometry for the checker, but never treat an empty or
    # unrelated JSON object as a completed annotation turn.
    return structured

def run_one(job,model,retry_failed=False,resume_missing=False):
    bundle=EXPERIMENT/'inputs'/job;output=EXPERIMENT/'runs'/job;output.mkdir(parents=True,exist_ok=True)
    conversation=None
    if (output/'result.json').exists():
        previous=read(output/'result.json')
        if resume_missing and not (EXPERIMENT/'candidates'/f'{job}.json').exists():
            conversation=(previous.get('result') or {}).get('conversation_id')
            if not conversation:raise ValueError('No existing conversation to resume')
        elif not retry_failed or previous.get('exit_code')==0:
            raise ValueError(f'{job}: result exists; only failed runs may be explicitly retried')
        history=EXPERIMENT/'runs/history'/job/str(time.time_ns())
        history.mkdir(parents=True,exist_ok=True)
        if not output.resolve().is_relative_to(EXPERIMENT.resolve()) or not history.resolve().is_relative_to(EXPERIMENT.resolve()):
            raise ValueError('Unexpected experiment archive path')
        for path in output.iterdir():
            if path.is_file():shutil.copyfile(path,history/path.name)
    executable=shutil.which('agy')
    if not executable:raise RuntimeError('Antigravity agy CLI is not installed')
    prompt=(bundle/'TASK.md').read_text(encoding='utf-8')
    if conversation:
        prompt='''Finish the annotation task from the images you already inspected. The previous turn returned no final annotation object. Do not run any commands, perform optional Python checks, edit files, or repeat image reads already completed. Image sizes and native-floor metadata are in job.json. Return your final structured annotation object now; place any uncertainty or missing image capability in limitations/unresolved rather than waiting for another tool. Do not return a plan.'''
    arguments=[executable,'--model',model,'--mode','plan','--disable-slash-commands',
        '--output-format','json' if conversation else 'stream-json','--json-schema',str(bundle/'output.schema.json'),
        '--print-timeout','8m','--log-file',str(output/'agy.log')]
    if conversation:arguments+=['--conversation',conversation]
    arguments+=['-p',prompt]
    write(output/'request.json',{'model':model,'mode':'plan','cwd':str(bundle),'prompt_sha256':sha(bundle/'TASK.md'),
        'started_utc':datetime.now(timezone.utc).isoformat(),'timeout_seconds':480,'resumed_conversation':conversation})
    start=time.monotonic();print(f'Started {job} with {model}',flush=True)
    error=None;code=None
    with (output/'events.ndjson').open('w',encoding='utf-8') as stdout,(output/'stderr.log').open('w',encoding='utf-8') as stderr:
        try:
            completed=subprocess.run(arguments,cwd=bundle,stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr,timeout=540)
            code=completed.returncode
        except subprocess.TimeoutExpired:error='External process exceeded the 9-minute outer timeout'
    events,result=parse_run(output/'events.ndjson')
    record={'model_requested':model,'exit_code':code,'elapsed_seconds':round(time.monotonic()-start,2),
        'error':error,'result':result,'event_count':len(events)}
    write(output/'result.json',record)
    structured=annotation_output(result,job)
    if isinstance(structured,dict):write(EXPERIMENT/'candidates'/f'{job}.json',structured)
    record['annotation_complete']=isinstance(structured,dict)
    write(output/'result.json',record)
    summary={'job':job,'exit_code':code,'status':result.get('status') if result else None,
        'elapsed_seconds':record['elapsed_seconds'],'structured_output':isinstance(structured,dict),
        'usage':result.get('usage') if result else None,'error':error or (result.get('error') if result else 'No terminal result')}
    print(json.dumps(summary),flush=True)
    return summary
def run(jobs,model,retry_failed=False,resume_missing=False):
    design=read(EXPERIMENT/'design.json');design['model']=model;write(EXPERIMENT/'design.json',design)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(lambda job:run_one(job,model,retry_failed,resume_missing),jobs))
    summaries=[]
    for job in read(EXPERIMENT/'design.json')['jobs']:
        path=EXPERIMENT/'runs'/job/'result.json'
        if path.exists():
            record=read(path);result=record.get('result') or {}
            summaries.append({'job':job,'model':record.get('model_requested'),'status':result.get('status'),
                'exit_code':record.get('exit_code'),'annotation_complete':(EXPERIMENT/'candidates'/f'{job}.json').exists(),
                'usage':result.get('usage')})
    write(EXPERIMENT/'run-summary.json',summaries)

def novel_review(job,doc,unmatched,manifest):
    path=EXPERIMENT/'reviews'/f'{job}_novel.json'
    if not path.exists():return {'status':'unreviewed','pending':len(unmatched)}
    review=read(path)
    if review.get('candidate_sha256')!=sha(EXPERIMENT/'candidates'/f'{job}.json'):
        raise ValueError(f'{job}: stale novel review candidate fingerprint')
    if review.get('manifest_sha256')!=sha(DATA/'manifest.json'):
        raise ValueError(f'{job}: stale novel review manifest fingerprint')
    if not review.get('reviewer') or review['reviewer']==doc.get('worker'):
        raise ValueError(f'{job}: independent reviewer required')
    decisions=review.get('decisions',[])
    ids=[d.get('id') for d in decisions]
    if len(ids)!=len(set(ids)) or set(ids)!=set(unmatched):
        raise ValueError(f'{job}: novel decision coverage mismatch')
    sources={e['source'] for d in decisions for e in d.get('evidence',[]) if e['kind']=='artwork'}
    if sources!=set(review.get('packet_sha256',{})):
        raise ValueError(f'{job}: novel review artwork fingerprint coverage mismatch')
    for source,expected in review['packet_sha256'].items():
        if sha(DATA/source)!=expected:raise ValueError(f'{job}: novel review artwork changed: {source}')
    counts=dict(accept=0,reject=0,needs_work=0,corrected=0,pending=0)
    proposals={p['id']:p for p in doc['passages']}
    for d in decisions:
        if d.get('decision') not in ('accept','reject','needs_work') or not d.get('reason'):
            raise ValueError(f'{job}: invalid novel decision')
        counts[d['decision']]+=1
        if d['decision']=='accept':
            corrected=pipeline.corrected(proposals[d['id']],d)
            pipeline.validate_passage(corrected,manifest['maps'],f'novel/{job}/{d["id"]}')
            if d.get('corrections'):counts['corrected']+=1
    return {'status':'reviewed','reviewer':review['reviewer'],'path':path.relative_to(EXPERIMENT).as_posix(),**counts,
        'publication':'Separate trial review; requires explicit import and fresh main-pipeline review before publication.'}

def compare():
    manifest,_,_,reference,_=pipeline.collect()
    gold=[p for p in reference]
    records=[];summaries=[]
    for job in read(EXPERIMENT/'design.json')['jobs']:
        path=EXPERIMENT/'candidates'/f'{job}.json'
        if not path.exists():summaries.append({'job':job,'error':'No structured candidate output'});continue
        doc=read(path);proposals=doc.get('passages',[]);expected=[p for p in gold if p['job_id']==job]
        invalid=[]
        for p in proposals:
            checked=copy.deepcopy(p)
            for e in checked.get('evidence',[]):
                if e.get('kind')=='artwork':e['source']=str(EXPERIMENT/'inputs'/job/e['source'])
            try:pipeline.validate_passage(checked,manifest['maps'],p.get('id','?'))
            except (ValueError,KeyError,TypeError) as exc:invalid.append({'id':p.get('id'),'error':str(exc)})
        pairs=[]
        for i,p in enumerate(proposals):
            for j,g in enumerate(expected):
                if p.get('a',{}).get('map')==g['a']['map'] and p.get('b',{}).get('map')==g['b']['map']:sides=('a','b')
                elif p.get('a',{}).get('map')==g['b']['map'] and p.get('b',{}).get('map')==g['a']['map']:sides=('b','a')
                else:continue
                try:cost=sum(math.dist(p[s]['exit'],g[t]['exit']) for s,t in zip(sides,('a','b')))
                except (KeyError,TypeError,ValueError):continue
                pairs.append((cost,i,j,sides))
        groups={}
        for cost,i,j,sides in pairs:
            key=tuple(sorted((expected[j]['a']['map'],expected[j]['b']['map'])))
            groups.setdefault(key,[]).append((cost,i,j,sides))
        chosen=[]
        for group in groups.values():
            pi=sorted({i for _,i,_,_ in group});gi=sorted({j for _,_,j,_ in group})
            lookup={(i,j):(cost,sides) for cost,i,j,sides in group}
            matrix=[[lookup.get((i,j),(1e9,None))[0] for j in gi] for i in pi]
            for a,b in minimum_assignment(matrix):
                i,j=pi[a],gi[b]
                if (i,j) in lookup:chosen.append((i,j,lookup[i,j][1]))
        used_p=set();used_g=set();matched=[]
        for i,j,sides in chosen:
            used_p.add(i);used_g.add(j);p,g=proposals[i],expected[j]
            exit_errors=[round(math.dist(p[s]['exit'],g[t]['exit']),2) for s,t in zip(sides,('a','b'))]
            badge_errors=[round(math.dist(p[s]['badge']['at'],g[t]['badge']['at']),2) for s,t in zip(sides,('a','b'))]
            focus_errors=[round(math.dist(p[s]['arrival'],g[t]['arrival']),2) for s,t in zip(sides,('a','b'))]
            direction=p['direction']==g['direction'] and not (sides==('b','a') and p['direction']=='a_to_b')
            codes=all(p[s]['badge']['code']==g[t]['badge']['code'] for s,t in zip(sides,('a','b')))
            row={'job':job,'proposed_id':p['id'],'reference_id':g['id'],
                'exit_error_pixels':exit_errors,'badge_error_pixels':badge_errors,'focus_error_pixels':focus_errors,
                'direction_matches':direction,'badge_codes_match':codes,
                'both_exits_within_12px':max(exit_errors)<=12,'both_badges_within_12px':max(badge_errors)<=12,
                'component_labels':{'proposed':[p[s]['component'] for s in sides],'reference':[g[t]['component'] for t in ('a','b')]}}
            matched.append(row);records.append(row)
        events,result=parse_run(EXPERIMENT/'runs'/job/'events.ndjson')
        history=EXPERIMENT/'runs/history'/job
        if history.exists():
            for previous in sorted(history.glob('*/events.ndjson')):
                earlier,_=parse_run(previous);events=earlier+events
        image_reads=set();tool_names=set();suspect=[]
        for event in events:
            step=event.get('step_update',{});tool=step.get('tool_info',{})
            name=tool.get('name') or step.get('tool_name')
            if name:tool_names.add(name)
            params=json.dumps(tool.get('parameters',{}))
            normalized=re.sub('/+','/',params.lower().replace('\\','/'))
            if '.png' in params.lower():image_reads.add(params)
            if any(term in normalized for term in ('reviews/decisions','data/catalog','pilot_report','seed.json')):suspect.append(params)
        errors=[n for row in matched for n in row['exit_error_pixels']]
        summary={'job':job,'proposed':len(proposals),'reference_passages':len(expected),'paired_map_matches':len(matched),
            'both_exits_within_12px':sum(row['both_exits_within_12px'] for row in matched),
            'both_badges_within_12px':sum(row['both_badges_within_12px'] for row in matched),
            'direction_matches':sum(row['direction_matches'] for row in matched),'badge_code_matches':sum(row['badge_codes_match'] for row in matched),
            'mean_exit_error_pixels':round(sum(errors)/len(errors),2) if errors else None,
            'missing_reference':[g['id'] for j,g in enumerate(expected) if j not in used_g],
            'unmatched_proposals':[p.get('id') for i,p in enumerate(proposals) if i not in used_p],
            'invalid':invalid,'inventory_maps':len(doc.get('inventory',[])),'unresolved':len(doc.get('unresolved',[])),
            'limitations':doc.get('limitations',[]),'claimed_inspected_images':doc.get('inspected_images',[]),
            'trace_image_tool_requests':len(image_reads),'trace_tool_names':sorted(tool_names),'reference_access_flags':suspect,
            'usage':result.get('usage') if result else None}
        summary['novel_review']=novel_review(job,doc,summary['unmatched_proposals'],manifest)
        summaries.append(summary)
    design=read(EXPERIMENT/'design.json')
    changed=any(sha(ADDON/'data'/name)!=expected for name,expected in design['runtime_data_baseline'].items())
    report={'model_requested':design['model'],'reference':'artwork-reviewed estimates, not live measured ground truth',
        'caveat':'Updated native-floor metadata and originals differ from earlier Luna inputs; not a controlled model-only comparison.',
        'jobs':summaries,'matches':records,'runtime_data_changed':changed}
    write(EXPERIMENT/'comparison.json',report)
    lines=['# Antigravity Flash 3.8 annotation trial','',report['caveat'],'',
        'Results are compared against the existing independently reviewed map estimates. No experiment tags enter the addon automatically.','',
        '| Job | Proposed | Reference | Paired maps | Both exits within 12 px | Mean exit error |','|---|---:|---:|---:|---:|---:|']
    for s in summaries:
        if s.get('error'):lines.append(f'| {s["job"]} | error: {s["error"]} | | | | |');continue
        lines.append(f'| {s["job"]} | {s["proposed"]} | {s["reference_passages"]} | {s["paired_map_matches"]} | {s["both_exits_within_12px"]} | {s["mean_exit_error_pixels"]} |')
    lines += ['','Coordinates use the 512-pixel reference. A paired-map match alone does not establish the correct entrance, floor, direction or component.',
        f'Both printed-badge anchors are within 12 pixels on {sum(s.get("both_badges_within_12px",0) for s in summaries)} of {len(records)} reference pairs. Badge placement still needs review.',
        '', '## Additional proposals', '']
    for s in summaries:
        review=s.get('novel_review',{})
        lines.append(f'- {s["job"]}: {review.get("accept",0)} accepted after artwork review ({review.get("corrected",0)} corrected), {review.get("needs_work",0)} need more work, {review.get("pending",0)} pending. See `{review.get("path","reviews/")}`.')
    lines += ['', 'The five corrected accepts are Ordelle stair links A–E. The F drop has transposed arrival focuses and an unverified direction; two Jugner/Landing proposals need paired entrance checks. These decisions do not publish tags or establish complete map coverage.',
        '', '## Running the worker', '',
        'Two isolated jobs used `gemini-3.8-flash-medium` through the installed `agy` CLI in read-only plan mode. Image reads were recorded. No reviewed-answer file access was flagged in the captured tool requests; this is a trace check, not a filesystem isolation guarantee.',
        'The provider initially rejected numeric enums in the output schema; a bounded integer works. Each image-reading turn later ended without annotations after an optional command was denied. Both conversations were resumed once to return the final structured results. Exit code zero or status SUCCESS alone is not sufficient: require annotation_complete.',
        'Usage in comparison.json is cumulative for each resumed conversation. Do not add archived-turn totals again. Billing/credit data were unavailable, so no monetary estimate is made.',
        '',
        'Usage and image-tool trace summaries are in comparison.json; full agent events and requests are under runs/.',
        'Runtime catalog and region data unchanged: '+str(not changed)+'. No live traversal or provider cost saving is claimed.']
    (EXPERIMENT/'REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'report':str(EXPERIMENT/'REPORT.md'),'jobs':[{k:s.get(k) for k in ('job','proposed','paired_map_matches','both_exits_within_12px','mean_exit_error_pixels','error')} for s in summaries]}))

def main():
    parser=argparse.ArgumentParser();parser.add_argument('command',choices=['prepare','run','evaluate'])
    parser.add_argument('--job',choices=['zulkheim','north_east','all'],default='all');parser.add_argument('--model',default=MODEL)
    parser.add_argument('--retry-failed',action='store_true')
    parser.add_argument('--resume-missing',action='store_true')
    args=parser.parse_args()
    if args.command=='prepare':prepare()
    elif args.command=='run':run(['zulkheim','north_east'] if args.job=='all' else [args.job],args.model,args.retry_failed,args.resume_missing)
    else:compare()
if __name__=='__main__':main()
