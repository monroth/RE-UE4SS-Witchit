#!/usr/bin/env bash
set -euo pipefail

test_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_dir="$(cd -- "$test_dir/../.." && pwd)"
result_dir="${LUA_HOST_TEST_RESULTS:-$repo_dir/../test-results}"
compiler="${CXX:-g++}"
c_compiler="${CC:-gcc}"
mkdir -p -- "$result_dir"

"$compiler" --version > "$result_dir/compiler.txt"
sha256sum "$repo_dir/UE4SS/include/LuaHost/Lifecycle.hpp" \
          "$repo_dir/UE4SS/src/LuaHost/Lifecycle.cpp" \
          "$repo_dir/UE4SS/include/LuaHost/UIKitLuaHost.h" \
          "$test_dir/LifecycleTests.cpp" \
          "$test_dir/AbiHeaderSmoke.c" \
          "$test_dir/TestSupport.hpp" > "$result_dir/test-input-sha256.txt"

"$c_compiler" -std=c11 -Wall -Wextra -Wpedantic -Werror -I"$repo_dir/UE4SS/include" \
    "$test_dir/AbiHeaderSmoke.c" -o "$result_dir/lua-host-abi-c-smoke" \
    2>&1 | tee "$result_dir/build-abi-c.log"
"$result_dir/lua-host-abi-c-smoke" 2>&1 | tee "$result_dir/tests-abi-c.log"

common_flags=(-std=c++20 -pthread -Wall -Wextra -Wpedantic -Werror -I"$repo_dir/UE4SS/include")
sources=("$test_dir/LifecycleTests.cpp" "$repo_dir/UE4SS/src/LuaHost/Lifecycle.cpp")

"$compiler" "${common_flags[@]}" -O2 "${sources[@]}" -o "$result_dir/lua-host-tests" \
    2>&1 | tee "$result_dir/build.log"
timeout 45s "$result_dir/lua-host-tests" \
    2>&1 | tee "$result_dir/tests.log"

"$compiler" "${common_flags[@]}" -g -O1 -fsanitize=address,undefined -fno-omit-frame-pointer \
    "${sources[@]}" -o "$result_dir/lua-host-tests-sanitized" \
    2>&1 | tee "$result_dir/build-sanitized.log"
ASAN_OPTIONS="${ASAN_OPTIONS:-detect_leaks=0:halt_on_error=1}" UBSAN_OPTIONS="${UBSAN_OPTIONS:-halt_on_error=1}" \
    timeout 45s "$result_dir/lua-host-tests-sanitized" \
    2>&1 | tee "$result_dir/tests-sanitized.log"
