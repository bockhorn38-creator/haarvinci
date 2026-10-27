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
# Manuell installieren: connectedAndroidTest würde die Pakete nach dem Test
# entfernen und damit einen anschließenden echten Prozess-Neustart verhindern.
adb install -r android/app/build/outputs/apk/debug/app-debug.apk
adb install -r -t android/app/build/outputs/apk/androidTest/debug/app-debug-androidTest.apk
runner=$(adb shell pm list instrumentation | tr -d '\r' | rg -F '(target=de.haarvinci.app.preview)' | cut -d ' ' -f1 | sed 's/^instrumentation://')
test -n "$runner"
adb shell am instrument -w -e class 'de.haarvinci.app.AndroidWorkflowTest#a_fullWorkflow' "$runner" 2>&1 | tee test-results/android/emulator.log
if ! rg -q 'OK \(1 test\)' test-results/android/emulator.log || rg -q 'FAILURES!!!|INSTRUMENTATION_FAILED' test-results/android/emulator.log; then
  echo 'Der vollständige Android-Test wurde nicht erfolgreich abgeschlossen.'
  exit 1
fi
adb shell am force-stop de.haarvinci.app.preview
adb shell am instrument -w -e class 'de.haarvinci.app.AndroidWorkflowTest#b_persistenceAfterProcessRestart' "$runner" 2>&1 | tee test-results/android/restart.log
if ! rg -q 'OK \(1 test\)' test-results/android/restart.log || rg -q 'FAILURES!!!|INSTRUMENTATION_FAILED' test-results/android/restart.log; then
  echo 'Die Android-Neustartprüfung wurde nicht erfolgreich abgeschlossen.'
  exit 1
fi
