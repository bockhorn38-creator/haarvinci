#!/usr/bin/env bash
set -euo pipefail
mkdir -p test-results/android
exec > >(tee test-results/android/device.log) 2>&1
# Diagnose darf den Exit-Code der eigentlichen Prüfungen nicht verändern.
collect_diagnostics() {
  local test_exit=$?
  trap - EXIT
  set +e
  adb logcat -d > test-results/android/logcat.txt
  if [[ -n "${app_package:-}" ]]; then
    adb pull "/sdcard/Android/data/$app_package/files/test-results" test-results/android/screenshots
  fi
  exit "$test_exit"
}
trap collect_diagnostics EXIT
# Manuell installieren: connectedAndroidTest würde die Pakete nach dem Test
# entfernen und damit einen anschließenden echten Prozess-Neustart verhindern.
apk_path=android/app/build/outputs/apk/debug/app-debug.apk
test_apk_path=android/app/build/outputs/apk/androidTest/debug/app-debug-androidTest.apk
find android/app/build/outputs/apk -type f -name '*.apk'
app_package=$("$ANDROID_HOME/build-tools/36.0.0/aapt" dump badging "$apk_path" | grep '^package:' | cut -d "'" -f2)
test_package=$("$ANDROID_HOME/build-tools/36.0.0/aapt" dump badging "$test_apk_path" | grep '^package:' | cut -d "'" -f2)
adb install -r "$apk_path"
adb install -r -t "$test_apk_path"
adb shell pm list instrumentation
instrumentation_runner=$(adb shell pm list instrumentation | tr -d '\r' | grep -F "instrumentation:$test_package/" | cut -d ' ' -f1 | sed 's/^instrumentation://')
test -n "$instrumentation_runner"

adb shell am instrument -w -e class 'de.haarvinci.app.AndroidWorkflowTest#a_fullWorkflow' "$instrumentation_runner" 2>&1 | tee test-results/android/emulator.log
if ! grep -Fq 'OK (1 test)' test-results/android/emulator.log || grep -Eq 'FAILURES!!!|INSTRUMENTATION_FAILED' test-results/android/emulator.log; then
  echo 'Der vollständige Android-Test wurde nicht erfolgreich abgeschlossen.'
  exit 1
fi
adb shell am force-stop "$app_package"
adb shell am instrument -w -e class 'de.haarvinci.app.AndroidWorkflowTest#b_persistenceAfterProcessRestart' "$instrumentation_runner" 2>&1 | tee test-results/android/restart.log
if ! grep -Fq 'OK (1 test)' test-results/android/restart.log || grep -Eq 'FAILURES!!!|INSTRUMENTATION_FAILED' test-results/android/restart.log; then
  echo 'Die Android-Neustartprüfung wurde nicht erfolgreich abgeschlossen.'
  exit 1
fi

adb shell am instrument -w -e class 'de.haarvinci.app.AndroidWorkflowTest#c_shareAndClipboardImport' "$instrumentation_runner" 2>&1 | tee test-results/android/import.log
if ! grep -Fq 'OK (1 test)' test-results/android/import.log || grep -Eq 'FAILURES!!!|INSTRUMENTATION_FAILED' test-results/android/import.log; then
  echo 'Android-Teilen-/Zwischenablageprüfung fehlgeschlagen.'
  exit 1
fi
adb shell am instrument -w -e class 'de.haarvinci.app.CalendarProviderTest' "$instrumentation_runner" 2>&1 | tee test-results/android/provider.log
if ! grep -Fq 'OK (1 test)' test-results/android/provider.log || grep -Eq 'FAILURES!!!|INSTRUMENTATION_FAILED' test-results/android/provider.log; then
  echo 'CalendarContract-Prüfung mit echten Provider-Testdaten fehlgeschlagen.'
  exit 1
fi
