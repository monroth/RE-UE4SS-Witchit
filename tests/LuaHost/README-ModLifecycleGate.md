The Windows `UE4SSLuaLifecycleGate` executable links the freshly built UE4SS DLL
and its actual bundled LuaMadeSimple/LuaRaw. It never initializes Unreal or
scans an executable. Only this exact test executable name suppresses DLL game
startup. `UE4SS_BUILD_LUA_LIFECYCLE_GATE` controls the build seam.

The gate constructs genuine LuaMod instances and calls their real `start_mod`
(preparation, library opening, require paths, main/async stacks, custom UTF-8
module loader and main.lua pcall). The original startup/ingress fixtures retain
substitute preparation bindings and exercise ConsoleCommandsMod plus the actual
WitchItRuntime main.lua only through its first engine call. They establish
lifetime/ingress behavior, not successful runtime discovery.

Round 6 adds real production binding preparation, directory traversal, ModRef,
userdata and scheduling APIs against a fake game directory tree. Engine lookup,
eager engine-backed FName/FText globals and detour patching alone have seams in
that fixture. It checks directory metadata/pairs from main, newly created and
resumed/nested coroutines, real EngineTick/ProcessEvent/frame/async/console
callbacks, and real OnUnload; exercises all no-engine wrapper representations;
starts genuine BPModLoaderMod main.lua and runs genuine WitchItRuntime atomic replacement, file listing and JSON-array operations.
The raw-directory baseline must fail both main and coroutine cases before the
fixed linked gate passes. See README.md, RealBindings/ and RawBindings.json.

Normal build/run (use the normal UE4SS Shipping configuration/toolchain):

```
cmake --build <host-build> --config Game__Shipping__Win64 --target UE4SSLuaLifecycleGate
<host-bin>/UE4SSLuaLifecycleGate.exe <candidate-root>
```

`review-tests/prepare_hostfix_build.py` reuses the existing compile-only VM
procedure. Before the positive build it configures
`UE4SS_LUA_LIFECYCLE_BASELINE=ON` for LuaMod.cpp alone. This omits the new ingress
adapter while preserving the same actual lifecycle: the ordinary gate must exit
1, and `--expect-baseline-failure` must verify startup never became started and
the failed VM can close. It reproduces main's unscoped binding-preparation SDK rejection. Library opening
has its own temporary LMS scope, which ends before require/binding preparation.
The final configuration must set BASELINE=OFF and pass the ordinary gate after
link, before producer/probe builds are accepted.

`ModLuaEntry` is the common host ingress adapter. It obtains cached actual/root
identity, admits the registered VM and acquires the real bundled gate before
any registry/stack work. The scope covers the entire operation, including raw
Lua calls, result decoding and cleanup. It grants no Native module authority.
Factory allocation is protected separately by LuaMadeSimple's unpublished-root
gate; attach publishes its host lifetime before preparation. Finalization uses
the existing exclusive LuaFinalizationScope after stop notification/draining.

Ingress coverage: direct preparation and complete startup; C++ Lua start/stop
notifications; native RegisterHook PRE/POST; Blueprint/custom-event dispatch;
NotifyOnNewObject immediate and deferred delivery; game-thread simple/delayed
and frame actions; keybinds; LoopAsync/delayed async callbacks; console/global
commands and engine lifecycle callbacks; OnUnload. Console executor and
signature VM already have explicit outer scopes. LMS host-function trampolines,
Native API dispatch and registered engine/input callback ownership remain the
existing protected host boundaries. Script-created coroutines inherit/adopt
cached VM identity through the actual protected LMS/Raw execution path.

The global script detour's immutable FScriptNameFilter rejects unrelated names
before once/executor accounting, owner dispatch, VM/callback-stack allocation,
and consumer reflection. SaveLoad/ UIKit callbacks retain all exact path,
schema and ownership checks. The gate records the pure shortlist cost and zero
admitted unrelated calls; that timing is not a complete detour/game benchmark.

Round 2 lock order and cancellation (review-3):

* The blocking order is Lua gate -> callback/action publication mutex. Dispatch
  takes only the action mutex + short host cache/lifetime bookkeeping locks to
  copy registrations and obtain VmExecutionLease pins, then releases it before
  Lua admission. Host cache/lifecycle locks never cross LuaLock, callback code,
  engine calls, or waits. Pins are destroyed on the same thread that captured
  them. Close can mark admission closing while pins exist; finalization waits
  for their drain. Such detached work is cancelled, with registry cleanup left
  to the finalizer. It is never requeued into a closing VM.
* Script/custom-event and immediate/deferred notify deliveries own snapshots,
  not vector iterators/references. After Lua admission they briefly reacquire
  the action mutex to validate the registration, release it, and marshal/call.
  Notify cancellation removes the ID before unref, outside the action mutex.
* Simple actions pin before detaching; execution, error recovery and unref share
  one entry. Delayed/frame callbacks use stable handles, not vector indices;
  removal/unref work is detached and cancellation-aware. Executing/processing
  flags are RAII, including exceptions and nested engine delivery. Both shared
  detours catch all C++ exceptions so one mod cannot invalidate the dispatcher.
* Lua registration bindings enter from the existing LMS/native scope before
  taking container locks. Nested same-root ModLuaEntry borrows that scope and
  never waits on LuaLock. ExecuteInGameThread prepares coroutine/registry state
  before taking the action mutex to publish. Generic lifecycle/console lists
  also snapshot and pin before delivery; registration publication is locked.
* Async pending publication takes m_actions_lock under the already-held gate;
  the worker releases m_actions_lock before Lua admission. Async processing and
  stop flags unwind safely; stop/join occurs before unload takes any action or
  gate lock. Finalization occurs after admission closes and all pins drain,
  outside the action mutex. Input and UFunction callback brokers snapshot their
  owned callback managers before entering Lua and retain their VM owner; neither
  invokes Lua under an input/container lock. Lua keybind delivery no longer
  acquires the action mutex. Hook registration/removal runs under the existing
  Lua scope; the UFunction callback slot protects its captured owner. Unload's
  hook/input removal happens after closing admission/pin drain and outside the
  action mutex; the
  final Lua close gate is acquired after releasing the action mutex.

The Windows gate additionally uses the real LoopAsync registration and actual
LuaMod async OS thread, plus the production ExecuteInGameThread scheduling core
(engine capability checks alone are stubbed). A barrier holds the actual Lua
gate while game-thread script/notify snapshots reach admission. Each completes
and delivers the scheduled action. Marshalling is a nil argument, avoiding
Unreal initialization. A close-after-detach case invokes real uninstall with
an outstanding lifetime pin, verifies cancellation/no escaping exception/flag
restoration, then runs a live VM's successor and closing frame cleanup. Its
watchdog is confined to the gate executable and exits 86 only after both
contention markers have been reached.

UE4SS_LUA_DISPATCH_BASELINE is OFF in accepted artifacts. The build runner first
enables it for LuaMod.cpp alone: simple actions use the exact 5afc63d function
(with only the review's after-detach interleaving), while script/notify admission
restores the reviewed container -> gate order. Close must exit 1 and each
contention process must time out with exit 86. This is a controlled reproduction
of review-3, not execution of the old DLL. The final ordinary gate must pass.

Portable real-LMS regression commands (Linux gate shim; no engine):

```
LUA_HOST_FMT_INCLUDE=<pinned-fmt/include> python tests/LuaHost/run-actual-stack-tests.py --dispatch
LUA_HOST_FMT_INCLUDE=<pinned-fmt/include> python tests/LuaHost/run-actual-stack-tests.py --dispatch --review3-baseline
```

The runner extracts the actual current action body and delivery admission helper
from LuaMod.cpp for compilation; it does not maintain a fixed dispatch model.
The baseline action file is source-checked against 5afc63d with the one declared
interleaving removed. Baseline mode requires both the closing-action assertion
failure and the independently bounded cross-VM lock-order deadlock. Positive
mode requires normal completion with balanced gate depth and zero VM leaks.


Review 4 / Round 3: notify cancellation claims removal by callback ID while
holding only the action mutex. Only that claimant releases the saved function
and thread refs, under its existing Lua entry after unlocking. Nested delivery
may cancel first and reuse both slots; the outer invocation then owns no cleanup.

Shared EngineTick and ProcessEvent registration runs in `on_program_start`,
after engine initialization and before `start_lua_mods`, outside every VM scope.
The ensure helpers reuse process-wide registration state (including ProcessEvent)
and reject a missing registration attempt from inside Lua. Per-mod ProcessEvent
state remains only a mirror for SDK layout compatibility. A failed engine hook
registration does not set the shared installed flag. Shared host dispatchers
carry no VM ownership; their leaf snapshots retain individual VM pins. Setup
precedes worker threads, and does not hold the action or async/container mutex.
The existing gate -> short action-mutex order is unchanged.

Both command forms use `dispatch_command_callbacks`: all retained per-reference
snapshots run, and the last admitted handler's boolean remains the result.

`Review4DispatchTests.inl` runs in the Windows linked lifecycle gate and the
Linux actual-stack harness. It checks nested notify slot reuse (both function
and thread refs), registered EngineTick/ProcessEvent owner-slot delivery after
closing the first scheduling VM, a live continuation and repeated scheduling,
one shared ProcessEvent registration, and both command forms with repeated
handlers and the last-result policy. Windows uses real LuaMod startup/unload;
Linux extracts the production helpers and uses real LMS/host lifecycle/broker.
Engine patching is replaced with the underlying real `TCallbackSlot` registration
and invocation. Notify object and output-device marshalling use nil. These are
real owner-slot delivery tests, not execution of an Unreal detour or game code.

`run-actual-stack-tests.py --review4-baseline` extracts exact bodies from reviewed
85311be and requires each of the five correctness cases to fail with its specific
diagnostic. `--review4` runs current production; `--sanitize` adds ASan/UBSan.
The Windows build procedure also builds `UE4SS_LUA_REVIEW4_BASELINE=ON`, restoring
the three reviewed behaviors, and requires those same five failures. The final
build has all baseline switches OFF and runs every new case after link.

Round 4 (review 5): `--round4-worker` delivers the real host-owned ProcessEvent
slot first with unknown GT identity, then from a real worker, and finally twice
from the established GT. The production dispatcher must preserve the queued
notification until GT and deliver exactly once. The Windows gate sets the actual
initializer's identity storage explicitly; no ProcessEvent caller establishes it.
Only object lookup/marshalling uses nil because there is no Unreal object array.
`--round4-tick-fallback` and `--round4-event-fallback` exercise the shared production
selection helper with all three API names, real VM scopes and registered owner
slots. Each direction covers missing/failed preferred registration, neither hook
available, both registrations failed, mixed failure, and preferred success.
The Linux `--review5` harness additionally extracts each of the three binding
selection blocks and the complete queue/dispatcher bodies unchanged.
`--review5-baseline` extracts those bodies from exactly `770e89a` and requires
three specific failing diagnostics. `UE4SS_LUA_REVIEW5_BASELINE=ON` is the Windows
negative control restoring unguarded ProcessEvent and ensure-before-selection;
the final build must have every baseline option OFF. Build media runs the three
negative cases after a separate link, then all positive cases after the final
link. No engine detour, live game, complete runtime initialization or FPS result
is claimed by these tests.

Round 5 (review 6): `--round5-producer` and `--round5-delayed` require refusal
of simple and all three delayed ProcessEvent scheduling forms when the trusted
identity producer was not installed. Cases model disabled/missing EngineTick,
detour failure, and failed initializer registration with a live Lua tick slot;
the latter retains EngineTick fallback. Rejection precedes queue/ref creation.
`--round5-first-tick` accepts work with an installed producer before identity is
known, rejects 100 pre-tick events and concurrent worker delivery, then publishes
identity and delivers simple/delayed/notify work once. It runs with and without
the optional Lua tick dispatcher. Windows uses the real initializer storage and
getters with a quiescent reset seam; its first-tick publication seam matches the
production assignment. Linux `--review6` extracts actual assignment/getters and
queue-admission code; engine-dependent coroutine creation uses a real registry
reference on the existing VM instead. `--review6-baseline` extracts `006ac18`
exactly and requires both admission defects to fail. The Windows equivalent
negative control is `UE4SS_LUA_REVIEW6_BASELINE`; the final build disables it.

`LUA_HOST_IDENTITY_TEST_RESULTS=<owned-dir> python run-identity-tests.py` extracts
the actual initializer registration-result statement, storage, trusted identity
assignment and every getter. It checks disabled/failed/successful registration
with a substituted engine backend and runs the publication probe under TSan.
`--baseline` requires the ignored-result failure and a specific TSan data race
from exact `006ac18`. Address-layout startup failures are retried and retained;
a sanitizer race is never retried as a startup failure. These are isolated
publication tests, not a whole-host TSan or physical engine-detour test.

Round 6 also retains repeated FName/FText argument errors before and during real
async callbacks. On MSVC these detect a completed error-recording lock guard
being unwound again by a later Lua longjmp (mutex count becomes negative and
async execution blocks). Error recording must finish in a non-inlined helper
before raising the Lua error. The executable has a 120-second deadline, exit 87,
so a blocking regression cannot strand the build runner.

Round 7 compiles `SerialNumberAllocation.inl` into the Windows executable with
reflection/call doubles, alongside the exact `0c2bef2` allocation entry as a
negative control. It requires serial creation without an SDK soft-reference
return copy, reflected initialization/destruction across three engine sizes,
cleanup on exception, invalid-bound rejection, and no repeated engine call for
an existing serial. This isolates the helper/lifecycle; it does not simulate an
Unreal ProcessEvent implementation. The retired UIKit typed-notify adapter is no
longer called from the linked gate; real-binding startup, callback, directory,
console and unload checks above remain unchanged.

`ROUND7_TEST_RESULTS=<owned-dir> python run-round7-regressions.py` runs on Linux
(including ASan/UBSan for the C++ helper), checks the serial negative entry exactly
matches `0c2bef2`, and runs the current Construct/Settings Lua event fixtures.
Windows retains the same C++ serial positive/negative controls in its lifecycle
executable. These checks cannot certify live UMG behavior.


NATIVE4 adds `Native4LinkedGate` and `Native4Counted` for the rebuilt host/Producer
acceptance receipt. The test starts the real Producer through CppMod, verifies
scalar preflight and the real primitives accessor, and cycles 25 real LuaMod VMs.
Four controlled counted executors model hook/asset/input/update completion at
pre-Lua entry. Stop runs under the actual VM gate; drain runs through the actual
CppMod callback after it is released. Engine-only listeners remain disabled in
this disposable no-engine process. This does not certify cooked engine callback
or replication behavior. Two injected host SDK exceptions must retain their exact
reason. Each positive stop has a five-second bound. A separate `negative` run
holds an outer real VM gate over uninstall and must terminate at the five-second
watchdog (exit 86); a successful return rejects the control.

```
Native4LinkedGate.exe <disposable-directory> <Producer.dll> <Native4Counted.dll> positive
Native4LinkedGate.exe <other-disposable-directory> <Producer.dll> <Native4Counted.dll> negative
```

Only the two exact CMake test executable names suppress normal game startup.
