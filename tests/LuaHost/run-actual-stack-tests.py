from pathlib import Path
import concurrent.futures,datetime,json,os,subprocess,sys
repo=Path(__file__).resolve().parents[2]
raw=repo/'deps/first/LuaRaw'; shim=repo/'tests/LuaHost/GateShim'
sanitize='--sanitize' in sys.argv
dispatch='--dispatch' in sys.argv
baseline='--review3-baseline' in sys.argv
review6='--review6' in sys.argv or '--review6-baseline' in sys.argv
review6_baseline='--review6-baseline' in sys.argv
review5=review6 or '--review5' in sys.argv or '--review5-baseline' in sys.argv
review5_baseline='--review5-baseline' in sys.argv
review4=review5 or '--review4' in sys.argv or '--review4-baseline' in sys.argv
review4_baseline='--review4-baseline' in sys.argv
lms='--lms' in sys.argv or dispatch or review4
fmt_include=Path(os.environ.get('LUA_HOST_FMT_INCLUDE',str(repo.parents[1]/'witchit-guest-devkit-20261012/source/deps/fmt/include')))
build=Path(os.environ.get('LUA_HOST_ACTUAL_TEST_RESULTS',str(repo/'tests/LuaHost/actual-stack-results')))
build.mkdir(parents=True,exist_ok=True)
common=['-DRC_LUA_MADE_SIMPLE_BUILD_STATIC','-I'+str(repo/'deps/first/LuaMadeSimple/include'),'-O1','-g','-ffunction-sections','-fdata-sections','-DLUA_USE_LINUX','-DLUA_USE_APICHECK','-I'+str(repo/'UE4SS/include'),'-I'+str(raw/'include'),'-I'+str(shim)]
common += ['-DFMT_HEADER_ONLY','-DRC_HELPERS_BUILD_STATIC','-I'+str(fmt_include),'-I'+str(repo/'deps/first/Helpers/include'),'-I'+str(repo/'deps/first/String/include')]
if sanitize: common+=['-fsanitize=address,undefined','-fno-omit-frame-pointer']
sources=[p for p in (raw/'src').glob('*.c') if p.name not in ('lua.c','luac.c','ltests.c')]+[repo/'UE4SS/src/LuaHost/LuaValueFrame.c',repo/'UE4SS/src/LuaHost/LuaEntryFrame.c',repo/'UE4SS/src/LuaHost/LuaReferenceFrame.c',repo/'UE4SS/src/LuaHost/LuaCallbackFrame.c',repo/'UE4SS/src/LuaHost/LuaTokenFrame.c',repo/'UE4SS/src/LuaHost/LuaNativeFrame.c']
def run(command,log):
 r=subprocess.run(command,capture_output=True,text=True);(build/log).write_text(r.stdout+r.stderr)
 if r.returncode: print(r.stdout+r.stderr);raise RuntimeError(str(command))
 return r
def compile_one(source):
 output=build/(source.stem+'.o');run(['gcc','-std=gnu11']+common+['-c',str(source),'-o',str(output)],source.stem+'.log');return output
if lms:
 sources.append(repo/'deps/first/LuaMadeSimple/src/HostFunctionFrame.c')
 sources.append(repo/'UE4SS/src/LuaHost/LuaThreadFrame.c')
 sources.append(repo/'deps/first/LuaMadeSimple/src/HostExecutionFrame.c')
 sources.append(repo/'UE4SS/src/LuaHost/LuaOwnedUserdataFrame.c')
 common += ['-ffunction-sections','-fdata-sections','-DRC_LUA_MADE_SIMPLE_BUILD_STATIC','-DRC_HELPERS_BUILD_STATIC','-DRC_UNREAL_BUILD_STATIC','-DFMT_HEADER_ONLY','-Dprintf_s=printf','-DHAS_INPUT','-DRC_INPUT_BUILD_STATIC','-DRC_DYNAMIC_OUTPUT_BUILD_STATIC','-DRC_FILE_BUILD_STATIC']
 common += ['-I'+str(repo/'deps/first/Input/include'),'-I'+str(repo/'deps/first/DynamicOutput/include'),'-I'+str(repo/'deps/first/File/include'),'-I'+str(repo/'deps/first/LuaMadeSimple/include'),'-I'+str(repo/'deps/first/Helpers/include'),'-I'+str(repo/'deps/first/String/include'),'-I'+str(repo/'deps/first/Unreal/include'),'-I'+str(fmt_include)]
begin=datetime.datetime.now(datetime.timezone.utc)
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool: objects=list(pool.map(compile_one,sources))
cxx=['clang++-17','-fms-extensions'] if lms else ['g++']
cpp=['Lifecycle.cpp','HostApiRuntime.cpp','LuaValueBackend.cpp','LuaReferences.cpp','LuaTokenBackend.cpp']
command=cxx+['-std=c++23','-Wall','-Wextra','-Werror','-pthread']+common+[str(repo/'UE4SS/src/LuaHost'/n) for n in cpp]+[str(repo/'tests/LuaHost/HostActualStackTests.cpp'),str(shim/'WindowsGateShim.cpp')]+[str(p) for p in objects]+[str(repo/'deps/first/LuaMadeSimple/src/HostExecutionHooks.cpp')]+['-ldl','-lm','-o',str(build/'actual-stack-tests')]
if not lms: command += [str(repo/'UE4SS/src/LuaHost/HostBindings.cpp'),'-Wl,--gc-sections']
if lms:
 command=[v for v in command if v not in ('-Werror',str(repo/'tests/LuaHost/HostActualStackTests.cpp'))]
 command += [str(repo/'tests/LuaHost/HostLmsIntegrationTests.cpp'),str(repo/'deps/first/LuaMadeSimple/src/LuaMadeSimple.cpp'),str(repo/'deps/first/LuaMadeSimple/src/HostUserdataObserver.cpp'),str(repo/'deps/first/LuaMadeSimple/src/HostTablePlan.cpp'),str(repo/'UE4SS/src/LuaHost/LuaExecutionBindings.cpp'),str(repo/'UE4SS/src/LuaHost/LmsAuxiliaryBindings.cpp'),str(repo/'UE4SS/src/LuaHost/HostBindings.cpp'),str(repo/'UE4SS/src/LuaHost/OwnedUserdataBindings.cpp'),str(repo/'deps/first/LuaMadeSimple/src/HostOwnedUserdataHooks.cpp'),str(repo/'UE4SS/src/LuaHost/HostIntegration.cpp'),str(repo/'UE4SS/src/LuaHost/EngineCallbackBindings.cpp'),str(repo/'UE4SS/src/LuaHost/HostApiExport.cpp'),str(repo/'deps/first/Unreal/src/Hooks/CallbackOwnerBridge.cpp'),str(repo/'deps/first/Input/src/Handler.cpp'),str(repo/'deps/first/Input/src/KeyDef.cpp'),str(repo/'deps/first/DynamicOutput/src/Output.cpp'),str(repo/'deps/first/DynamicOutput/src/OutputDevice.cpp'),'-Wl,--gc-sections','-Wl,--wrap=LuaLock,--wrap=LuaUnlock']
 fixture_sanitize=['-fsanitize=address,undefined','-fno-omit-frame-pointer'] if sanitize else []
 if dispatch:
  # Retain the exact reviewed body, excluding only its deterministic interleave.
  old=subprocess.check_output(['git','show','5afc63d:candidate/source/RE-UE4SS/UE4SS/src/Mod/LuaMod.cpp'],cwd=repo,text=True)
  old=old[old.index('    static auto process_simple_actions('):old.index('    // Process pending NotifyOnNewObject')]
  baseline_body=(repo/'tests/LuaHost/Review3SimpleActionsBaseline.inl').read_text().split('\n',1)[1]
  baseline_body=baseline_body.replace('        if(after_simple_actions_detached) after_simple_actions_detached();\n','')
  assert old==baseline_body,'review-3 baseline body changed'
  production=(repo/'UE4SS/src/Mod/LuaMod.cpp').read_text()
  section=production[production.index('    static void dispatch_error()'):production.index('    struct PinnedNotify')]
  section=section.replace('"../../../tests/LuaHost/Review3SimpleActionsBaseline.inl"','"'+str(repo/'tests/LuaHost/Review3SimpleActionsBaseline.inl')+'"')
  struct=production[production.index('    struct PinnedRegistryCallback'):production.index('    static std::vector<PinnedRegistryCallback> snapshot_script_callbacks')]
  helper=production[production.index('    template<class Valid, class Invoke> static void deliver_script_callback'):production.index('    struct PinnedCallbackData')]
  (build/'Review3ProductionDispatch.inl').write_text(section+struct+helper)
  original=(repo/'tests/LuaHost/HostLmsIntegrationTests.cpp').read_text()
  original=original.replace('int main(', '#include "'+str(repo/'tests/LuaHost/ModDispatchTests.inl')+'"\nint main(')
  marker='CHECK(install_lua_host_integration()); CHECK(install_engine_callback_bindings());'
  assert marker in original
  original=original.replace(marker,marker+' dispatch_tests::run(); return 0;')
  test=build/'HostLmsDispatchTests.cpp';test.write_text(original)
  command=[v for v in command if v!=str(repo/'tests/LuaHost/HostLmsIntegrationTests.cpp')]
  command += [str(test),'-DUE4SS_LUA_LIFECYCLE_GATE','-I'+str(build),'-I'+str(repo/'tests/LuaHost')]
  if baseline:command+=['-DUE4SS_LUA_DISPATCH_BASELINE']
 if review4:
  import importlib.util
  sys.dont_write_bytecode=True
  spec=importlib.util.spec_from_file_location('review4_extract',repo/('tests/LuaHost/extract-review5.py' if review5 else 'tests/LuaHost/extract-review4.py'));extractor=importlib.util.module_from_spec(spec);spec.loader.exec_module(extractor)
  extractor.extract(repo,build,review6_baseline,True) if review6 else extractor.extract(repo,build,review5_baseline if review5 else review4_baseline)
  original=(repo/'tests/LuaHost/HostLmsIntegrationTests.cpp').read_text()
  original=original.replace('int main(', '#include "'+(str(build/'Review6Harness.inl') if review6 else str(repo/('tests/LuaHost/Review5Harness.inl' if review5 else 'tests/LuaHost/Review4Harness.inl')))+'"\nint main(')
  marker='CHECK(install_lua_host_integration()); CHECK(install_engine_callback_bindings());'
  assert marker in original
  original=original.replace(marker,marker+" return review4_tests::run(std::getenv(\"ROUND3_CASE\")?std::atoi(std::getenv(\"ROUND3_CASE\")):0);")
  test=build/'HostLmsReview4Tests.cpp';test.write_text(original)
  command=[v for v in command if v!=str(repo/'tests/LuaHost/HostLmsIntegrationTests.cpp')]
  command += [str(test),'-DUE4SS_LUA_LIFECYCLE_GATE','-I'+str(build),'-I'+str(repo/'tests/LuaHost')]
 run(cxx+['-std=c++23','-shared','-fPIC']+fixture_sanitize+['-DRC_LUA_MADE_SIMPLE_BUILD_STATIC','-DHAS_INPUT','-DRC_INPUT_BUILD_STATIC','-I'+str(repo/'deps/first/Input/include'),'-I'+str(repo/'UE4SS/include'),'-I'+str(repo/'deps/first/LuaMadeSimple/include'),'-I'+str(repo/'deps/first/LuaRaw/include'),'-I'+str(repo/'deps/first/Helpers/include'),'-I'+str(repo/'deps/first/String/include'),'-I'+str(fmt_include),str(repo/'tests/LuaHost/NativeLmsFixture.cpp'),'-o',str(build/'native-lms-fixture.so')],'native-library.log')
 symbols=run(['nm','-u',str(build/'native-lms-fixture.so')],'native-imports.log').stdout
 # Export the real Native fixture imports only, so unused full-SDK platform
 # and logging code can be discarded rather than replaced by fake definitions.
 for line in symbols.splitlines():
  symbol=line.split()[-1]
  if symbol.startswith(('host_','UE4SS_','_ZN2RC','_ZNK2RC','lua_','luaL_')):
   command+=['-Wl,--export-dynamic-symbol='+symbol]
run(command,'link.log')
env=os.environ.copy()
if sanitize:env['ASAN_OPTIONS']='detect_leaks=0:halt_on_error=1';env['UBSAN_OPTIONS']='halt_on_error=1'
if review4:
 cases=[]
 for mode,reason in ([(12,'ProcessEvent accepted simple work without an identity producer'),(14,'delayed selection accepted ProcessEvent without an identity producer')] if review6_baseline else [(12,'unused'),(13,'unused'),(14,'unused')] if review6 else [(9,'ProcessEvent drained notification before game-thread identity was established'),(10,'delayed API rejected available installed fallback'),(11,'delayed API rejected available installed fallback')] if review5 else [(4,'nested notify cancellation released a reused registry slot'),(5,'closing first scheduler revoked shared registered dispatcher'),(6,'closing first scheduler revoked shared registered dispatcher'),(7,'console dispatch dropped the second handler'),(8,'console dispatch dropped the second handler')]):
  case_env=env.copy();case_env['ROUND3_CASE']=str(mode)
  case=subprocess.run([str(build/'actual-stack-tests'),str(build/'native-lms-fixture.so')],capture_output=True,text=True,timeout=20,env=case_env)
  (build/('case-'+str(mode)+'.log')).write_text(case.stdout+case.stderr)
  passed=(case.returncode==1 and (('ROUND5 FAIL ' if review6 else 'ROUND4 FAIL ' if review5 else 'ROUND3 FAIL ')+reason) in case.stderr) if (review6_baseline if review6 else review5_baseline if review5 else review4_baseline) else case.returncode==0
  cases.append({'case':mode,'exit_code':case.returncode,'expected_failure':review6_baseline if review6 else review5_baseline if review5 else review4_baseline,'status':'PASS' if passed else 'FAIL','stdout':case.stdout,'stderr':case.stderr})
  print(case.stdout,case.stderr)
 record={'status':'PASS' if all(c['status']=='PASS' for c in cases) else 'FAIL','reviewed_commit':'006ac18' if review6 else '770e89a' if review5 else '85311be','baseline':review6_baseline if review6 else review5_baseline if review5 else review4_baseline,'sanitizers':sanitize,'cases':cases}
 (build/'RESULT.json').write_text(json.dumps(record,indent=2)+'\n');sys.exit(0 if record['status']=='PASS' else 1)
result=subprocess.run([str(build/'actual-stack-tests')]+([str(build/'native-lms-fixture.so')] if lms else []),capture_output=True,text=True,timeout=20,env=env)
record={'begin_utc':begin.isoformat(),'end_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'exit_code':result.returncode,'stdout':result.stdout,'stderr':result.stderr,'sanitizers':sanitize,'boundary':'Actual bundled LuaRaw; real shared-VM coroutine, host API table and trusted dispatch. Linux OS shim, no Windows/full SDK/live claim.'}
if dispatch and baseline:
 record['baseline_close_failed']=result.returncode!=0
 lock_env=env.copy();lock_env['ROUND2_LOCK_ONLY']='1'
 try:
  locked=subprocess.run([str(build/'actual-stack-tests'),str(build/'native-lms-fixture.so')],capture_output=True,text=True,timeout=3,env=lock_env)
  record['baseline_lock_deadlocked']=False
 except subprocess.TimeoutExpired:
  record['baseline_lock_deadlocked']=True
 result_code=0 if record['baseline_close_failed'] and record['baseline_lock_deadlocked'] else 1
 print('REVIEW3_BASELINE_REPRODUCED' if result_code==0 else 'BASELINE CHECK FAILED',record)
else:result_code=result.returncode
(build/'RESULT.json').write_text(json.dumps(record,indent=2)+'\n');print(result.stdout,result.stderr);sys.exit(result_code)
