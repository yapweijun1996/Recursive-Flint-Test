import json, subprocess, time, statistics, pathlib, tempfile, datetime, shutil
import argparse

parser = argparse.ArgumentParser(description='Run the fixed Flint/Pi custom benchmark.')
parser.add_argument('--thinking', choices=['high', 'off'], default='high')
parser.add_argument('--compare', action='store_true', help='Interleave high/off for every case.')
parser.add_argument('--output', type=pathlib.Path)
args = parser.parse_args()
MODEL = 'recursive/flint-v1.0:free'
ROOT = str(pathlib.Path(__file__).resolve().parents[2])
PI = shutil.which('pi.cmd')
cases = [
('arithmetic', 'Return {"value": <1009 multiplied by 997>}.', {'value':1005973}, False),
('python_closures', 'For Python 3, determine a and b: fs=[lambda: i for i in range(3)]; a=[f() for f in fs]; gs=[lambda i=i: i for i in range(3)]; b=[g() for g in gs]. Return {"a": [...], "b": [...]}.', {'a':[2,2,2],'b':[0,1,2]}, False),
('javascript_microtasks', 'In modern JavaScript, console.log("A"); Promise.resolve().then(()=>console.log("B")); queueMicrotask(()=>console.log("C")); console.log("D"); Return {"order": [the four strings in execution order]}.', {'order':['A','D','B','C']}, False),
('interval_merge', 'Merge overlapping OR touching closed intervals [[8,10],[1,4],[4,5],[12,15],[9,12],[20,20]]. Return {"intervals": [...]} sorted by start.', {'intervals':[[1,5],[8,15],[20,20]]}, False),
('shortest_path', 'Directed weighted edges: S->A 4, S->B 1, B->A 2, A->C 1, B->C 5, C->T 3, A->T 9, B->T 12. Return {"distance": shortest S-to-T cost, "path": [node names in that path]}.', {'distance':7,'path':['S','B','A','C','T']}, False),
('sql_left_join_null', 'SQL tables customers(id) has (1),(2); orders(id,customer_id,amount) has (10,1,10),(11,1,NULL). Evaluate SELECT c.id,COUNT(*) AS rows,COUNT(o.id) AS orders,COUNT(o.amount) AS amounts,SUM(o.amount) AS sum FROM customers c LEFT JOIN orders o ON o.customer_id=c.id GROUP BY c.id ORDER BY c.id. Return {"result": [objects with id,rows,orders,amounts,sum]}, using JSON null for SQL NULL.', {'result':[{'id':1,'rows':2,'orders':2,'amounts':1,'sum':10},{'id':2,'rows':1,'orders':0,'amounts':0,'sum':None}]}, False),
('binary_search_repair', 'A binary search on ascending a uses inclusive bounds lo=0,hi=len(a)-1; while lo < hi: mid=(lo+hi)//2; if a[mid]==x return mid; elif a[mid]<x set lo=mid; else set hi=mid; after loop return -1. Which patch is fully correct, terminating and handles empty/singleton arrays? A: only change loop to lo<=hi. B: loop lo<=hi, set lo=mid+1 and hi=mid-1. C: loop lo<hi, set lo=mid+1 and hi=mid-1. D: only change hi initialization to len(a). Return {"choice":"A/B/C/D"}.', {'choice':'B'}, False),
('tenant_predicate', 'Assume SQL boolean precedence AND before OR. Security requirement: every returned row must have tenant_id=:tenant. Select unsafe query numbers: 1) WHERE tenant_id=:tenant AND status=\'open\' OR is_public=1; 2) WHERE tenant_id=:tenant AND (status=\'open\' OR is_public=1); 3) WHERE id=:id; 4) WHERE tenant_id=:tenant AND id=:id. Return {"unsafe":[numbers ascending]}.', {'unsafe':[1,3]}, False),
('lru_trace', 'An initially empty LRU cache capacity 2 executes put(A,1),put(B,2),get(A),put(C,3),get(B),put(D,4),get(A),get(C),get(D). A get hit makes that entry most recent; misses return -1. Return {"gets":[all get return values],"keys":[final keys least-to-most recent]}.', {'gets':[1,-1,-1,3,4],'keys':['C','D']}, False),
('read_tool', 'You MUST call the read tool exactly once to read only .gitattributes in the current directory. Do not access any other file. Return {"textAuto":true} if the returned file contains the line * text=auto, otherwise false.', {'textAuto':True}, True),
]
results=[]
runs = [(name, prompt, expected, tool, level)
        for index, (name, prompt, expected, tool) in enumerate(cases)
        for level in ((('high', 'off') if index % 2 == 0 else ('off', 'high'))
                      if args.compare else (args.thinking,))]
for name,prompt,expected,tool,level in runs:
    cmd=[PI,'--provider','openrouter','--model',MODEL,'--no-session','--no-extensions','--no-mcp','--thinking',level,'--mode','json']
    cmd += ['--tools','read'] if tool else ['--no-tools']
    cmd += ['Reply in English. Return only the requested JSON object in your final answer, without markdown. '+prompt]
    start=time.perf_counter()
    row={'name':name,'thinking':level,'prompt':prompt,'expected':expected,'passed':False}
    try:
        p=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=90)
        events=[]
        for line in p.stdout.splitlines():
            try: events.append(json.loads(line))
            except ValueError: pass
        messages=[e['message'] for e in events if e.get('type')=='message_end' and e.get('message',{}).get('role')=='assistant']
        final=messages[-1] if messages else {}
        answer=''.join(c.get('text','') for c in final.get('content',[]) if c.get('type')=='text')
        row.update(answer=answer,exit_code=p.returncode,stop_reason=final.get('stopReason'),model=final.get('model'),provider=final.get('provider'))
        calls=[c for m in messages for c in m.get('content',[]) if c.get('type')=='toolCall']
        row['tool_calls']=[{'name':c.get('name'),'arguments':c.get('arguments')} for c in calls]
        ends=[e for e in events if e.get('type')=='tool_execution_end']
        row['tool_errors']=sum(bool(e.get('isError')) for e in ends)
        row['thinking_characters']=sum(len(c.get('thinking','')) for m in messages for c in m.get('content',[]) if c.get('type')=='thinking')
        row['usage']={k:sum(m.get('usage',{}).get(k,0) for m in messages) for k in ['input','output','reasoning','totalTokens']}
        row['reported_cost_usd']=sum(m.get('usage',{}).get('cost',{}).get('total',0) for m in messages)
        try:
            parsed=json.loads(answer)
            row['parsed']=parsed
            row['passed']=p.returncode==0 and final.get('stopReason')=='stop' and parsed==expected
        except ValueError:
            row['error']='Final answer was not strict JSON'
        if tool:
            row['passed']=row['passed'] and len(calls)==1 and calls[0].get('name')=='read' and calls[0].get('arguments',{}).get('path')=='.gitattributes' and len(ends)==1 and not row['tool_errors']
        else:
            row['passed']=row['passed'] and not calls
        if final.get('errorMessage'): row['error']=final['errorMessage']
        if not messages: row['error']='No assistant message; '+p.stderr[-500:]
    except subprocess.TimeoutExpired:
        row['error']='90 second timeout'
    row['wall_seconds']=round(time.perf_counter()-start,3)
    results.append(row)
    print(json.dumps({k:row.get(k) for k in ['name','thinking','passed','wall_seconds','answer','error','usage','thinking_characters']},ensure_ascii=False),flush=True)
groups = {}
for level in dict.fromkeys(row['thinking'] for row in results):
    group = [row for row in results if row['thinking'] == level]
    groups[level] = {'cases':len(group),'passed':sum(row['passed'] for row in group),'total_wall_seconds':round(sum(row['wall_seconds'] for row in group),3),'median_wall_seconds':round(statistics.median(row['wall_seconds'] for row in group),3),'usage':{key:sum(row.get('usage',{}).get(key,0) for row in group) for key in ['input','output','reasoning','totalTokens']},'thinking_characters':sum(row.get('thinking_characters',0) for row in group),'reported_cost_usd':sum(row.get('reported_cost_usd',0) for row in group)}
summary={'model':MODEL,'pi_version':'1.4.0','thinking':'interleaved high/off' if args.compare else args.thinking,'timestamp_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'cases':len(results),'passed':sum(r['passed'] for r in results),'groups':groups,'limitations':['Single trial per case per setting; small custom benchmark, not SWE-bench.','Wall time includes Pi startup, network and all model/tool turns.','No code modification or execution benchmark.','No session persistence; extensions and built-in MCP disabled.','Existing Pi configuration and project context were retained.','Requested thinking levels may be normalized or ignored by the provider; output counters are observed separately.']}
out=args.output or pathlib.Path(__file__).resolve().with_name('comparison.json' if args.compare else 'results-'+args.thinking+'.json')
out.write_text(json.dumps({'summary':summary,'results':results},indent=2,ensure_ascii=False),encoding='utf-8')
print('SUMMARY '+json.dumps(summary),flush=True)
print('REPORT '+str(out),flush=True)
