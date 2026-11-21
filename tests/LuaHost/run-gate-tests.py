from pathlib import Path
import subprocess,concurrent.futures,json,datetime,os
repo=Path(__file__).resolve().parents[2]
root=Path(os.environ.get('LUA_HOST_GATE_TEST_RESULTS',str(repo/'../bridge-gate-checkpoint-20261013')))
root=root.resolve();root.mkdir(exist_ok=True)
raw=repo/'deps/first/LuaRaw';shim=repo/'tests/LuaHost/GateShim'
files=[p for p in (raw/'src').glob('*.c') if p.name not in ['lua.c','luac.c','ltests.c']]
def compile_one(p):
 obj=root/(p.stem+'.o');cmd=['gcc','-std=gnu11','-O1','-DLUA_USE_LINUX','-I'+str(raw/'include'),'-I'+str(shim),'-c',str(p),'-o',str(obj)]
 if p.name=='luauser.c':cmd.insert(1,'-D_WIN32') # Exercise Win32 gate through the existing OS shim.
 r=subprocess.run(cmd,capture_output=True,text=True);(root/(p.stem+'.log')).write_text(r.stdout+r.stderr)
 return p,r.returncode,obj
begin=datetime.datetime.now(datetime.timezone.utc)
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(compile_one,files))
errors=[(str(p),c) for p,c,o in results if c]
if errors:print('COMPILE_ERRORS',errors);raise SystemExit(1)
cmd=['g++','-std=c++20','-O1','-pthread','-I'+str(raw/'include'),'-I'+str(shim),str(repo/'tests/LuaHost/LuaGateTests.cpp'),str(shim/'WindowsGateShim.cpp')]+[str(o) for p,c,o in results]+['-ldl','-lm','-o',str(root/'gate-tests')]
r=subprocess.run(cmd,capture_output=True,text=True);(root/'link.log').write_text(r.stdout+r.stderr)
if r.returncode:print(r.stderr[-2500:]);raise SystemExit(r.returncode)
r=subprocess.run([str(root/'gate-tests')],capture_output=True,text=True,timeout=10);end=datetime.datetime.now(datetime.timezone.utc)
record={'begin_utc':begin.isoformat(),'end_utc':end.isoformat(),'exit_code':r.returncode,'stdout':r.stdout,'stderr':r.stderr,'boundary':'Actual bundled Lua source; Linux Windows-gate shim models OS primitives, not native Windows OS validation.'}
(root/'LATEST.json').write_text(json.dumps(record,indent=2)+'\n');print(r.stdout,r.stderr,'EXIT',r.returncode);raise SystemExit(r.returncode)
