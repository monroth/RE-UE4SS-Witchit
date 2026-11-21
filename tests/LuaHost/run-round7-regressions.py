"""Compile the exact serial-allocation implementation; exercise real UIKit Lua.
Engine reflection/calls are doubles. No live-engine behavior is claimed.
"""
from pathlib import Path
import os,subprocess,tempfile,json,hashlib
here=Path(__file__).resolve().parent; repo=here.parents[4]
out=Path(os.environ.get('ROUND7_TEST_RESULTS',tempfile.mkdtemp(prefix='ue4ss-round7-')));out.mkdir(exist_ok=True,parents=True)
results=[]
def run(name,args,expected=0,contains=None):
 r=subprocess.run(list(map(str,args)),cwd=repo,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);(out/(name+'.log')).write_text(r.stdout)
 assert r.returncode==expected,(name,r.returncode,r.stdout)
 if contains:assert contains in r.stdout,(name,r.stdout)
 results.append({'case':name,'exit_code':r.returncode,'expected':expected,'log':str(out/(name+'.log'))});print(name,'PASS',flush=True)
source=here/'SerialAllocationGate.cpp'
old=subprocess.check_output(['git','show','0c2bef2:candidate/source/RE-UE4SS/deps/first/Unreal/src/UObjectArray.cpp'],cwd=repo,text=True)
a=old.index('    int32 FUObjectArray::AllocateSerialNumber(');z=old.index('\n    void UObjectArray::LockGUObjectArray()',a)
assert (here/'SerialNumberBaseline.inl').read_text().split('\n',1)[1].rstrip()==old[a:z].rstrip(),'serial baseline drift'
for name,flags in [('serial',[]),('serial-sanitized',['-fsanitize=address,undefined','-fno-omit-frame-pointer'])]:
 exe=out/name;run(name+'-compile',['c++','-std=c++23','-DROUND7_SERIAL_STANDALONE',*flags,source,'-o',exe]);run(name,[exe],contains='ROUND7 PASS serial allocation:')
run('construct-settings',['python3','review-tests/run_task_d.py','review-tests/simple_construct.lua','review-tests/simple_settings.lua'],contains='PASS Settings events:')
(out/'RESULT.json').write_text(json.dumps({'status':'PASS','cases':results,'serial_baseline_sha256':hashlib.sha256(old[a:z].encode()).hexdigest(),'limits':'Actual shared serial helper/allocation entry with engine reflection doubles; actual Construct facade and Settings event module with engine doubles.'},indent=2)+'\n')
