"""Checked inventory of raw Lua callback publications in UE4SS + LMS.

This is a drift check, not a substitute for the real linked Windows gate.
Each inventoried raw site is reviewed in RawBindings.json. New sites fail closed.
"""
from pathlib import Path
import collections,json,re,sys
root=Path(__file__).resolve().parents[2]
pattern=re.compile(r'\b(?:lua_pushcfunction|lua_pushcclosure|lua_register|luaL_Reg|luaL_setfuncs|lua_atpanic|lua_sethook)\b|\[.*\]\s*\(\s*lua_State\s*\*')
def inventory():
    found={}
    for base in ['UE4SS','deps/first/LuaMadeSimple']:
        for p in sorted((root/base).rglob('*')):
            if p.suffix not in ('.c','.h','.cpp','.hpp'):continue
            matches=[line.strip() for line in p.read_text().splitlines() if pattern.search(line)]
            if matches:found[p.relative_to(root).as_posix()]=matches
    return found
manifest=json.loads((Path(__file__).with_name('RawBindings.json')).read_text())
actual=inventory();expected={k:v['sites'] for k,v in manifest.items()}
assert actual==expected,'Raw Lua callback inventory changed; review dispatch and update RawBindings.json'
s=(root/'UE4SS/src/Mod/LuaMod.cpp').read_text()
assert 'meta_table.set_has_userdata(false);\n#ifdef UE4SS_LUA_DIRECTORY_BASELINE' in s
assert '#else\n                            meta_table.add_pair("__index", [](const LuaMadeSimple::Lua& lua)' in s
assert all(v['reason'] for v in manifest.values())
print('RAW_BINDINGS PASS:',sum(map(len,actual.values())),'reviewed raw sites;',len(actual),'files; directory SDK callback uses protected LMS dispatch')
