#!/usr/bin/env bash
set -euo pipefail
mkdir -p test-results/android
# Diagnose darf den Exit-Code der eigentlichen Prüfungen nicht verändern.
collect_diagnostics() {
  local test_exit=$?
  trap - EXIT
  set +e
  adb logcat -d > test-results/android/logcat.txt
  adb pull /sdcard/Android/data/de.haarvinci.app.preview/files/test-results test-results/android/screenshots
  exit "$test_exit"
}
trap collect_diagnostics EXIT
android/gradlew -p android --no-daemon --max-workers=2 :app:connectedDebugAndroidTest '-Pandroid.testInstrumentationRunnerArguments.class=de.haarvinci.app.AndroidWorkflowTest#a_fullWorkflow' 2>&1 | tee test-results/android/emulator.log
adb shell am force-stop de.haarvinci.app.preview
adb shell am instrument -w -e class 'de.haarvinci.app.AndroidWorkflowTest#b_persistenceAfterProcessRestart' de.haarvinci.app.preview.test/androidx.test.runner.AndroidJUnitRunner 2>&1 | tee test-results/android/restart.log
test "$(rg -c 'OK \(1 test\)' test-results/android/restart.log)" -ge 1
if rg -q 'FAILURES!!!|INSTRUMENTATION_FAILED' test-results/android/restart.log; then exit 1; fi
