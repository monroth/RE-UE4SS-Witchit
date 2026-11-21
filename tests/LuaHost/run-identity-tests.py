from pathlib import Path
import importlib.util,json,os,subprocess,sys
sys.dont_write_bytecode=True
repo=Path(__file__).resolve().parents[2]
build=Path(os.environ['LUA_HOST_IDENTITY_TEST_RESULTS']);build.mkdir(parents=True,exist_ok=True)
baseline='--baseline' in sys.argv
spec=importlib.util.spec_from_file_location('identity',repo/'tests/LuaHost/extract-identity.py');ex=importlib.util.module_from_spec(spec);spec.loader.exec_module(ex)
s,body=ex.extract(repo,baseline);(build/'ProductionIdentity.inl').write_text(body)
# Verify the actual registration statement, including config-disabled skip and
# ERROR_ID handling. The fake backend replaces engine patching only.
a=s.index('            '+('Hook::RegisterEngineTickPreCallback(HookedEngineTick' if baseline else 'GGameThreadIdentityProducerInstalled.store('))
b=s.index('\n        }',a)
statement=s[a:b]
backend='\nnamespace Hook {constexpr int ERROR_ID=0;static int result;struct Options{bool once,nested;const char* owner;const char* name;};template<class F> int RegisterEngineTickPreCallback(F,Options){return result;}}\nstatic void HookedEngineTick(){}\n'
if baseline:body=body.replace('    bool GGameThreadIdInitialized{};','    bool GGameThreadIdInitialized{};\n    std::atomic<bool> GGameThreadIdentityProducerInstalled{};')
registration=body+backend+'void install(bool enabled){if(enabled){'+statement.replace('HookedEngineTick','::HookedEngineTick').replace('GGameThreadIdentityProducerInstalled','Unreal::UnrealInitializer::GGameThreadIdentityProducerInstalled')+'}}\nint main(){using namespace Unreal::UnrealInitializer;install(false);if(GGameThreadIdentityProducerInstalled.load()) return 1;Hook::result=0;install(true);if(GGameThreadIdentityProducerInstalled.load())return 2;Hook::result=7;install(true);return GGameThreadIdentityProducerInstalled.load()?0:3;}\n'
preamble='#include <atomic>\n#include <thread>\n#include <stdexcept>\n#define STR(x) x\nenum class LogLevel{Error};namespace Output {template<LogLevel> void send(const char*){}}\n'
(build/'Registration.cpp').write_text(preamble+registration)
for name,src,flags in [('registration',build/'Registration.cpp',[]),('identity-race',repo/'tests/LuaHost/IdentityRace.cpp',['-fsanitize=thread','-fno-omit-frame-pointer','-fno-pie','-no-pie'])]:
    command=['g++','-std=c++20','-O1','-g','-pthread','-I'+str(build),str(src),'-o',str(build/name)]+flags
    c=subprocess.run(command,capture_output=True,text=True);(build/(name+'-build.log')).write_text(c.stdout+c.stderr);assert c.returncode==0,c.stderr
registration=subprocess.run([str(build/'registration')],capture_output=True,text=True)
assert registration.returncode==(3 if baseline else 0),registration.returncode
attempts=[];matched=False
for i in range(40):
    env=os.environ.copy();env['TSAN_OPTIONS']='halt_on_error=1:exitcode=66'
    run=subprocess.run([str(build/'identity-race')],capture_output=True,text=True,env=env,timeout=30)
    attempts.append({'attempt':i,'exit':run.returncode,'stdout':run.stdout,'stderr':run.stderr})
    # Retry only known sanitizer address-layout startup failure, never a race.
    if 'unexpected memory mapping' in run.stderr or (run.returncode==-11 and not run.stderr):continue
    matched=run.returncode==66 and 'WARNING: ThreadSanitizer: data race' in run.stderr if baseline else run.returncode==0
    break
record={'status':'PASS' if matched else 'FAIL','baseline':'006ac18' if baseline else None,'registration_exit':registration.returncode,'attempts':attempts}
(build/'RESULT.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record,indent=2));sys.exit(0 if matched else 1)
