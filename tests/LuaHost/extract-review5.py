"""Review-5: full production queues/dispatchers and three exact API selections.
Only engine availability/registration and object lookup/marshalling are substituted.
"""
import subprocess

def extract(repo,build,baseline,review6=False):
    import importlib.util
    spec=importlib.util.spec_from_file_location('review4_extract',repo/'tests/LuaHost/extract-review4.py')
    ex=importlib.util.module_from_spec(spec);spec.loader.exec_module(ex);ex.extract(repo,build,False)
    path='candidate/source/RE-UE4SS/UE4SS/src/Mod/LuaMod.cpp'
    s=subprocess.check_output(['git','show',('006ac18' if review6 else '770e89a')+':'+path],cwd=repo,text=True) if baseline else (repo/'UE4SS/src/Mod/LuaMod.cpp').read_text()
    body=s[s.index('    static void dispatch_error()'):s.index('    // Local convenience wrappers for Capabilities functions')]
    # Current test-only availability declarations precede the wrappers; harness supplies them.
    marker='#ifdef UE4SS_LUA_LIFECYCLE_GATE\n    static bool (*offline_shared_dispatcher_registration)'
    if marker in body:body=body[:body.index(marker)]
    body=body.replace('"../../../tests/LuaHost/Review3SimpleActionsBaseline.inl"','"'+str(repo/'tests/LuaHost/Review3SimpleActionsBaseline.inl')+'"')
    if baseline and not review6:body='static void (*offline_notify_argument)(const LuaMadeSimple::Lua&){};\n'+body
    (build/'Review5ProductionDispatch.inl').write_text(body)
    a=s.index('    // Process-wide dispatchers belong to the host');b=s.index('    // Scope already owns Lua',a)
    shared=s[a:b]
    shared=shared.replace('    static bool (*offline_shared_dispatcher_registration)(bool engine_tick){};\n','')
    if baseline and not review6:
        shared=shared.replace('        if(offline_shared_dispatcher_registration) {tick();event();return;}\n','')
    a=s.index('    auto LuaMod::on_program_start()');b=s.index('        Unreal::UObjectArray::AddUObjectDeleteListener',a)
    (build/'Review5SharedDispatch.inl').write_text(shared+s[a:b]+'    }\n')
    selections=[]
    for name in ['ExecuteInGameThreadWithDelay','RetriggerableExecuteInGameThreadWithDelay','LoopInGameThreadWithDelay']:
        a=s.index('m_lua.register_function("'+name+'"')
        a=s.index('            // '+('Use default method from config, fall back to the other if unavailable' if baseline and not review6 else 'Select an available dispatcher installed by host setup, then fall back.'),a)
        b=s.index('\n\n',s.index('            else if (method ==',a) if baseline and not review6 else a)
        block=s[a:b].replace('LuaMod::m_default_game_thread_method','preferred')
        selections.append('if(std::string_view(api)=="'+name+'") {\n'+block+'\nreturn method; }')
    (build/'Review5Selection.inl').write_text('GameThreadExecutionMethod LuaMod::review5_select_api(const LuaMadeSimple::Lua& lua,LuaMod* mod,const char* api,GameThreadExecutionMethod preferred){\n'+''.join(selections)+'throw std::runtime_error("unknown delayed API");}\n')

    if review6:
        spec=importlib.util.spec_from_file_location('identity',repo/'tests/LuaHost/extract-identity.py');identity=importlib.util.module_from_spec(spec);spec.loader.exec_module(identity)
        _,body=identity.extract(repo,baseline)
        if baseline:
            body=body.replace('    bool GGameThreadIdInitialized{};','    bool GGameThreadIdInitialized{};\n    std::atomic<bool> GGameThreadIdentityProducerInstalled{};')
        (build/'ProductionIdentity.inl').write_text(body)
        # Exact real queue admission prefix, before engine-dependent coroutine setup.
        a=s.index('    static void queue_game_thread_action(');b=s.index('            auto [hook_lua, lua_thread_registry_index]',a)
        prefix=s[a:b].replace('static void queue_game_thread_action','static void review6_queue_prefix')
        (build/'Review6Queue.inl').write_text(prefix+"lua_pushvalue(L,callback_idx);auto ref=luaL_ref(L,LUA_REGISTRYINDEX);std::lock_guard lock{LuaMod::m_thread_actions_mutex};LuaMod::m_game_thread_actions.push_back({&lua,ref,LUA_NOREF});}\nstatic void review6_enqueue_simple(const LuaMadeSimple::Lua& lua,LuaMod* mod){review6_queue_prefix(lua,mod,GameThreadExecutionMethod::ProcessEvent,1); }\n")
        seam='static void review5_set_game_thread(bool established){auto& id=Unreal::UnrealInitializer::GGameThreadId;id=established?std::this_thread::get_id():std::thread::id{};'+('Unreal::UnrealInitializer::GGameThreadIdInitialized=established;' if baseline else 'Unreal::UnrealInitializer::GGameThreadIdInitialized.store(established,std::memory_order_release);')+'}\n'
        seam+='static void review6_set_identity_producer(bool value){Unreal::UnrealInitializer::GGameThreadIdentityProducerInstalled.store(value,std::memory_order_release);}\nstatic void review6_publish_first_tick(){Unreal::UnrealInitializer::establish_from_engine_tick();}\n'
        harness=(repo/'tests/LuaHost/Review5Harness.inl').read_text()
        a=harness.index('namespace Unreal {');b=harness.index('struct UObject',a)
        harness=harness[:a]+'#include "ProductionIdentity.inl"\nnamespace Unreal {\n'+harness[b:]
        a=harness.index('static void review5_set_game_thread(');b=harness.index('\n',a)
        harness=harness[:a]+seam+harness[b:]
        harness=harness.replace('#include "Review4ConsoleDispatch.inl"','#include "Review6Queue.inl"\n#include "Review4ConsoleDispatch.inl"')
        harness=harness.replace('#include "Review5DispatchTests.inl"','#include "Review5DispatchTests.inl"\n#include "Review6DispatchTests.inl"')
        harness=harness.replace('if(mode>=9) review5_gates(mode);','review6_set_identity_producer(true);if(mode>=12) review6_gates(mode);else if(mode>=9) review5_gates(mode);').replace('ROUND4 ACTUAL STACK','ROUND5 ACTUAL STACK').replace('ROUND4 FAIL','ROUND5 FAIL')
        (build/'Review6Harness.inl').write_text(harness)
