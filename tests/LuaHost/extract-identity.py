"""Exact identity storage, trusted assignment, getters and registration result."""
import subprocess

def extract(repo,baseline=False):
    path='candidate/source/RE-UE4SS/deps/first/Unreal/src/UnrealInitializer.cpp'
    s=subprocess.check_output(['git','show','006ac18:'+path],cwd=repo,text=True) if baseline else (repo/'deps/first/Unreal/src/UnrealInitializer.cpp').read_text()
    storage=s[s.index('    // These globals are explicitly'):s.index('    static Hook::GlobalCallbackId FNameConstructedHookId')]
    a=s.index('        if (GGameThreadId ==');b=s.index('        if (StaticStorage::FNameVerificationStatus',a)
    getters=s[s.index('    auto '+('GetGameThreadId()' if baseline else 'IsGameThreadIdentityProducerInstalled()')):s.rindex('\n}')]
    # Ignore the unrelated FName/unreal tail; preserve assignment/getters verbatim.
    body='namespace Unreal { namespace UnrealInitializer {\n'+storage+'static void establish_from_engine_tick() {\n'+s[a:b]+'}\n}\n'+getters+'\n}\n'
    return s,body
