# Portable Lua host lifecycle tests

This suite compiles the real `UE4SS/src/LuaHost/Lifecycle.cpp` implementation
directly with the standard C++20 library and pthreads. It does not compile a
replacement implementation, load Lua, or build the Windows UE4SS application.
The public ABI header is also compiled and checked as C11.

Run from the checkout directory:

```sh
bash tests/LuaHost/run-tests.sh
```

The runner uses GCC with warnings treated as errors, runs the lifecycle suite
once with optimization and once with AddressSanitizer and UndefinedBehaviorSanitizer,
and limits each suite run to 45 seconds. Three concurrency tests each run 64
controlled races. Build logs, assertion output, binaries, and input SHA256 hashes
are written to `../test-results/` beside the checkout. `CXX`, `CC`, and
`LUA_HOST_TEST_RESULTS` can override the compilers or output directory.
LeakSanitizer is disabled by default because it cannot run under this executor's
tracing environment; the failed leak-detection attempt is preserved in
`tests-sanitized-lsan-blocked.log`. AddressSanitizer and UndefinedBehaviorSanitizer
remain enabled. Set `ASAN_OPTIONS=detect_leaks=1:halt_on_error=1` to enable leak
checks on an untraced host.

The tests cover registry identity validation, module and VM binding, admission
during close and retirement, lease ownership, deferred finalization, reentrant
retirement, and controlled concurrent initialization/retirement.

The actual-stack runner also checks callback failures against the bundled LuaRaw:
protected calls leave a stringified error and traceback above the caller's stack
base. Callers read it before restoring their stack. A failed call does not retire
the callback reference; the same closure can succeed on its next invocation.

Linux tests of the portable core cannot establish Windows export visibility,
real DLL lifetime, Lua VM access discipline, or integration with existing mod
callbacks. Those require separate application builds and integration tests.

The linked Windows lifecycle gate also has `--round6-bindings` (or the full
ordinary invocation). It installs production globals, ModRef, type bindings,
and real game-thread/async queues against a filesystem fixture. Only engine
lookup, eager engine-backed FName/FText globals, and detour patching have seams.
It reads directory metadata from main, resumed/nested Lua-created coroutines,
real ProcessEvent/EngineTick/frame/async/console callbacks, and OnUnload; checks
all wrapper types constructible without engine reflection; starts the unmodified
stock BPModLoaderMod; and runs the real WitchItRuntime discovery module.
TArray/TMap/TSet and their reflected iteration require live FProperty metadata,
so their dispatch is audited rather than executed by this no-engine gate.
`UE4SS_LUA_DIRECTORY_BASELINE=ON` restores only the original raw directory
metamethod. The build runner requires both `--round6-main` and
`--round6-coroutine` to fail with their specific metadata completion diagnostic,
then rebuilds with every baseline flag OFF and runs the full lifecycle gate.

Run `python tests/LuaHost/audit-raw-bindings.py` for the permanent raw-publication
inventory check. `RawBindings.json` explains each retained raw site. No LuaType
or LuaLibrary export uses a raw C callback; members, custom metamethods and
iterators go through `const Lua&` LMS dispatch. Raw destructor/token and internal
VM-operation callbacks intentionally use the raw C API and cannot use checked
SDK operations without first entering the normal protected dispatch.
The VM runner first runs the real-bindings gate as a preflight. MSBuild stops
on compilation errors, and a second compiler-error scan rejects a zero exit
status containing an MSVC error. A directory baseline is accepted only when its
specific actual-stack/coroutine-identity rejection appears in the log; a script
failure for an unrelated reason is insufficient.
