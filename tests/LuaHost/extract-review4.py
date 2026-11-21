"""Extract current production dispatch or exact reviewed 85311be bodies.
Only engine registration/marshalling are replaced; LMS/registry/owner/lifecycle
are the real linked implementations. Both old console loops are extracted.
"""
from pathlib import Path
import subprocess

def extract(repo,build,baseline):
    path='candidate/source/RE-UE4SS/UE4SS/src/Mod/LuaMod.cpp'
    s=subprocess.check_output(['git','show','85311be:'+path],cwd=repo,text=True) if baseline else (repo/'UE4SS/src/Mod/LuaMod.cpp').read_text()
    section=s[s.index('    static void dispatch_error()'):s.index('    static auto process_pending_notify_on_new_object_callbacks()')]
    section=section.replace('"../../../tests/LuaHost/Review3SimpleActionsBaseline.inl"','"'+str(repo/'tests/LuaHost/Review3SimpleActionsBaseline.inl')+'"')
    (build/'Review4ProductionDispatch.inl').write_text(section)
    start=s.index('    // Helper to ensure engine tick hook is registered') if baseline else s.index('    // Process-wide dispatchers belong to the host')
    end=s.index('    static void queue_game_thread_action',start)
    shared=s[start:end]
    if not baseline:
        shared='static bool (*offline_shared_dispatcher_registration)(bool){};\n'+shared
    if baseline:
        shared='static bool shared_process_event_hooked{};\nstatic bool (*offline_shared_dispatcher_registration)(bool){};\nstatic void (*offline_ensure_shared_dispatcher)(bool,LuaMod*){};\nstatic void (*offline_reset_shared_dispatchers)(){};\n'+shared
        shared+='''void LuaMod::on_program_start() {
        offline_ensure_shared_dispatcher=[](bool tick,LuaMod* mod){if(tick) ensure_engine_tick_hooked();else ensure_process_event_hooked(mod);};
        offline_reset_shared_dispatchers=[] {m_is_engine_tick_hooked=false;shared_process_event_hooked=false;};
        }\n'''
    else:
        start=s.index('    auto LuaMod::on_program_start()')
        bootstrap=s[start:s.index('        Unreal::UObjectArray::AddUObjectDeleteListener',start)]
        assert 'prepare_shared_game_thread_dispatchers(' in bootstrap
        shared+=bootstrap+'    }\n'
    (build/'Review4SharedDispatch.inl').write_text(shared)
    helpers=s[s.index('    struct PinnedCallbackData'):s.index('    static auto script_hook(')]
    if baseline:
        custom=[]
        for container in ['m_custom_command_lua_pre_callbacks','m_global_command_lua_callbacks']:
            start=s.index('                for(auto& snapshot:snapshot_command_callbacks('+container)
            body=s[start:s.index('            });',start)]
            body=body.replace(container,'LuaMod::'+container)
            body=body.replace('LuaType::FOutputDevice::construct(*callback_data.lua, &ar);','callback_data.lua->set_nil();')
            custom.append(body)
        helpers+='''static bool review4_dispatch_console(bool global) {
const File::StringType command=STR("shared"),command_name=command;
const std::vector<File::StringType> command_parts{command};
return guarded_dispatch([&] {if(global) {
'''+custom[1]+''' } else {
'''+custom[0]+''' }});}
'''
    else:
        # Both public command forms must use this same all-handlers implementation.
        for container in ['m_custom_command_lua_pre_callbacks','m_global_command_lua_callbacks']:
            assert 'return dispatch_command_callbacks('+container+',command,command_parts,command_name,' in s
        helpers+='''static bool review4_dispatch_console(bool global) {
return dispatch_command_callbacks(global?LuaMod::m_global_command_lua_callbacks:LuaMod::m_custom_command_lua_pre_callbacks,
STR("shared"),{STR("shared")},STR("shared"),[](const auto& lua){lua.set_nil();});}
'''
    (build/'Review4ConsoleDispatch.inl').write_text(helpers)
