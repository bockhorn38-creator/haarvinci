package de.haarvinci.app;

import android.graphics.Bitmap;
import android.net.Uri;
import android.webkit.WebView;
import androidx.test.core.app.ActivityScenario;
import androidx.test.ext.junit.runners.AndroidJUnit4;
import androidx.test.platform.app.InstrumentationRegistry;
import androidx.test.uiautomator.By;
import androidx.test.uiautomator.UiDevice;
import androidx.test.uiautomator.UiObject2;
import androidx.test.uiautomator.Until;
import org.json.JSONObject;
import org.json.JSONTokener;
import org.junit.Test;
import org.junit.runner.RunWith;
import java.io.File;
import java.io.FileOutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicReference;
import java.util.regex.Pattern;
import static org.junit.Assert.*;

@RunWith(AndroidJUnit4.class)
public class AndroidWorkflowTest {
    private static final String USER = "conny-android-test";
    private static final String PASSWORD = "Fiktives-Android-Testpasswort-2026!";
    private ActivityScenario<MainActivity> scenario;
    private final UiDevice device = UiDevice.getInstance(InstrumentationRegistry.getInstrumentation());

    private String js(String script) throws Exception {
        CountDownLatch done = new CountDownLatch(1);
        AtomicReference<String> response = new AtomicReference<>();
        scenario.onActivity(activity -> {
            WebView web = activity.appView();
            if (web == null) { response.set("null"); done.countDown(); return; }
            web.evaluateJavascript(script, result -> { response.set(result); done.countDown(); });
        });
        assertTrue("WebView-Antwort fehlt", done.await(10, TimeUnit.SECONDS));
        Object value = new JSONTokener(response.get()).nextValue();
        return value == JSONObject.NULL ? "" : value.toString();
    }
    private JSONObject state() throws Exception {
        String result = js("JSON.stringify({path:location.pathname,text:document.body?document.body.innerText:'',lang:document.documentElement.lang})");
        return result.isEmpty() ? new JSONObject().put("path", "").put("text", "") : new JSONObject(result);
    }
    private void waitFor(String path, String text) throws Exception {
        long deadline = System.currentTimeMillis() + 45000;
        JSONObject current = null;
        while (System.currentTimeMillis() < deadline) {
            current = state();
            if (current.getString("path").equals(path) && current.getString("text").contains(text)) return;
            Thread.sleep(250);
        }
        throw new AssertionError("Erwartete Seite " + path + " mit " + text + "; letzte Seite: " + current);
    }
    private void fill(JSONObject fields) throws Exception {
        js("for(const [name,value] of Object.entries(" + fields + ")){document.querySelector('[name=\"'+name+'\"]').value=value;}document.querySelector('form').requestSubmit();");
    }
    private void open(String path) {
        scenario.onActivity(activity -> activity.appView().loadUrl(activity.appOrigin() + path));
    }
    private void screenshot(String name) throws Exception {
        File directory = InstrumentationRegistry.getInstrumentation().getTargetContext().getExternalFilesDir("test-results");
        assertNotNull(directory);
        directory.mkdirs();
        Bitmap image = InstrumentationRegistry.getInstrumentation().getUiAutomation().takeScreenshot();
        assertNotNull(image);
        try (FileOutputStream output = new FileOutputStream(new File(directory, name))) { image.compress(Bitmap.CompressFormat.PNG, 100, output); }
        image.recycle();
    }
    private void menu(String label) throws Exception {
        scenario.onActivity(activity -> activity.openOptionsMenu());
        UiObject2 item = device.wait(Until.findObject(By.text(label)), 10000);
        assertNotNull("Programmmenü fehlt: " + label, item);
        item.click();
    }
    private void signIn() throws Exception {
        waitFor("/anmelden/", "Kundenbuch öffnen");
        fill(new JSONObject().put("username", USER).put("password", PASSWORD));
        waitFor("/", "Schön, dass du da bist, Conny.");
    }

    @Test public void a_fullWorkflow() throws Exception {
        try (ActivityScenario<MainActivity> active = ActivityScenario.launch(MainActivity.class)) {
            scenario = active;
            waitFor("/einrichten/", "Mach es zu deinem.");
            assertEquals("de", state().getString("lang"));
            AtomicReference<String> origin = new AtomicReference<>();
            scenario.onActivity(activity -> origin.set(activity.appOrigin()));
            HttpURLConnection outside = (HttpURLConnection) new URL(origin.get() + "/bereit/").openConnection();
            try { assertEquals(403, outside.getResponseCode()); } finally { outside.disconnect(); }
            fill(new JSONObject().put("first_name", "Conny").put("username", USER).put("password1", PASSWORD).put("password2", PASSWORD));
            waitFor("/", "Schön, dass du da bist, Conny.");
            screenshot("android-uebersicht.png");
            open("/kundinnen/neu/");
            waitFor("/kundinnen/neu/", "Kundin speichern");
            fill(new JSONObject().put("first_name", "Mila").put("last_name", "Testgarten").put("phone", "+49 151 0000 0199").put("email", "mila.android@example.com").put("first_consultation", "2026-10-01").put("notes", "Fiktive Android-Testkundin.").put("natural_color", "Dunkelblond").put("hair_structure", "Wellig").put("natural_length", "25,5").put("desired_length", "50").put("hair_wishes", "Natürliche Fülle"));
            String detail = "";
            long deadline = System.currentTimeMillis() + 30000;
            while (System.currentTimeMillis() < deadline) {
                JSONObject current = state();
                if (current.getString("text").contains("Mila Testgarten") && current.getString("text").contains("Persönliche Notizen")) { detail = current.getString("path"); break; }
                Thread.sleep(200);
            }
            assertFalse("Kundin wurde nicht angelegt", detail.isEmpty());
            open(detail + "bearbeiten/");
            waitFor(detail + "bearbeiten/", "Änderungen speichern");
            fill(new JSONObject().put("notes", "Auf Android bearbeitet und vor der Sicherung gespeichert."));
            waitFor(detail, "vor der Sicherung gespeichert");
            open(detail);
            waitFor(detail, "vor der Sicherung gespeichert");
            open("/kundinnen/?q=MILA+TESTGARTEN");
            waitFor("/kundinnen/", "1 Ergebnis");
            assertTrue(state().getString("text").contains("Mila Testgarten"));
            assertFalse(state().getString("text").contains("Marie Sommer"));
            screenshot("android-kundinnen.png");

            open(detail);
            waitFor(detail, "Natürliche Fülle");
            assertTrue(state().getString("text").contains("25,5 cm"));
            screenshot("android-haarprofil.png");
            open(detail + "extensions/neu/");
            waitFor(detail + "extensions/neu/", "Extensions zuordnen");
            fill(new JSONObject().put("manufacturer", "Fiktivhaar Atelier").put("extension_type", "Tape-Ins").put("color", "Naturblond").put("color_code", "#18/22").put("length_cm", "50,5").put("weight_g", "100,25").put("quantity", "4").put("quantity_unit", "packs").put("purchase_price", "149,90").put("sale_price", "249,95").put("assigned_on", "2026-10-01").put("delivery_status", "ordered").put("notes", "Erfundene Extensions auf Android."));
            waitFor(detail, "Fiktivhaar Atelier");
            String position = js("document.querySelector('[data-position]').dataset.position");
            String positionEdit = detail + "extensions/" + position + "/bearbeiten/";
            open(positionEdit);
            waitFor(positionEdit, "Extensions speichern");
            fill(new JSONObject().put("weight_g", "-1"));
            waitFor(positionEdit, "Bitte prüfe deine Angaben.");
            fill(new JSONObject().put("weight_g", "100,25").put("color", "Kupfer").put("delivery_status", "received"));
            waitFor(detail, "Kupfer");
            screenshot("android-extensions-kundenakte.png");
            open(detail + "extensions/neu/");
            waitFor(detail + "extensions/neu/", "Extensions zuordnen");
            fill(new JSONObject().put("manufacturer", "Zweites Fiktivatelier").put("extension_type", "Bondings").put("color", "Braun").put("length_cm", "40").put("weight_g", "50").put("purchase_price", "75,20").put("assigned_on", "2026-10-02"));
            waitFor(detail, "Zweites Fiktivatelier");
            String secondPosition = js("document.querySelector('[data-position]').dataset.position");
            assertNotEquals(position, secondPosition);
            String deletePath = detail + "extensions/" + secondPosition + "/loeschen/";
            open(deletePath);
            waitFor(deletePath, "Position endgültig löschen");
            fill(new JSONObject());
            waitFor(detail, "wurde gelöscht");
            js("document.querySelector('#historie').open=true;");
            assertTrue(state().getString("text").contains("Extensions gelöscht"));
            assertTrue(state().getString("text").contains("Extensions geändert"));
            screenshot("android-kundenhistorie.png");
            open("/extensions/?q=MILA&status=received");
            waitFor("/extensions/", "1 Position");
            assertTrue(state().getString("text").contains("149,90"));
            assertTrue(state().getString("text").contains("Mila Testgarten"));
            screenshot("android-extensions-uebersicht.png");

            open("/konto/");
            waitFor("/konto/", "Deine Daten auf dem Pixel");
            menu("Datensicherung erstellen");
            UiObject2 filename = device.wait(Until.findObject(By.res(Pattern.compile(".*:id/edit_filename"))), 15000);
            if (filename == null) filename = device.findObject(By.clazz("android.widget.EditText"));
            assertNotNull("Android-Dateidialog fehlt", filename);
            filename.setText("Haarvinci-Test-Sicherung.haarvinci");
            UiObject2 save = device.wait(Until.findObject(By.res(Pattern.compile(".*:id/action_menu_save"))), 5000);
            if (save == null) save = device.findObject(By.text(Pattern.compile("(?i)save|speichern")));
            assertNotNull("Speichern-Schaltfläche fehlt", save);
            save.click();
            long savedDeadline = System.currentTimeMillis() + 20000;
            AtomicReference<Uri> exported = new AtomicReference<>();
            while (System.currentTimeMillis() < savedDeadline) {
                scenario.onActivity(activity -> exported.set(activity.lastExport));
                if (exported.get() != null) break;
                Thread.sleep(200);
            }
            assertNotNull("Sicherungsdatei nicht gespeichert", exported.get());

            open(detail + "bearbeiten/");
            waitFor(detail + "bearbeiten/", "Änderungen speichern");
            fill(new JSONObject().put("notes", "Dieser spätere Stand soll durch die Sicherung ersetzt werden."));
            waitFor(detail, "spätere Stand");
            open(positionEdit);
            waitFor(positionEdit, "Extensions speichern");
            fill(new JSONObject().put("color", "Schwarz nach Sicherung"));
            waitFor(detail, "Schwarz nach Sicherung");
            menu("Sicherung wiederherstellen");
            UiObject2 backup = device.wait(Until.findObject(By.text("Haarvinci-Test-Sicherung.haarvinci")), 15000);
            assertNotNull("Gespeicherte Sicherung fehlt in der Android-Dateiauswahl", backup);
            backup.click();
            UiObject2 confirm = device.wait(Until.findObject(By.res("android:id/button1")), 20000);
            if (confirm == null) {
                screenshot("android-restore-fehler.png");
                java.io.ByteArrayOutputStream hierarchy = new java.io.ByteArrayOutputStream();
                device.dumpWindowHierarchy(hierarchy);
                throw new AssertionError("Wiederherstellungsbestätigung fehlt. UI: " + hierarchy.toString("UTF-8"));
            }
            if (device.findObject(By.textContains("7 Kundenakten")) == null) {
                screenshot("android-restore-fehler.png");
                java.io.ByteArrayOutputStream hierarchy = new java.io.ByteArrayOutputStream();
                device.dumpWindowHierarchy(hierarchy);
                throw new AssertionError("Sicherungsinhalt fehlt. UI: " + hierarchy.toString("UTF-8"));
            }
            confirm.click();
            signIn();
            open(detail);
            waitFor(detail, "vor der Sicherung gespeichert");
            assertFalse(state().getString("text").contains("spätere Stand"));
            assertTrue(state().getString("text").contains("Kupfer"));
            assertFalse(state().getString("text").contains("Schwarz nach Sicherung"));
            screenshot("android-kundenakte.png");
            open("/konto/");
            waitFor("/konto/", "Sicher abmelden");
            js("document.querySelector('form[action=\"/abmelden/\"]').requestSubmit();");
            waitFor("/anmelden/", "Kundenbuch öffnen");
            open(detail);
            waitFor("/anmelden/", "Kundenbuch öffnen");
        }
    }

    @Test public void b_persistenceAfterProcessRestart() throws Exception {
        try (ActivityScenario<MainActivity> active = ActivityScenario.launch(MainActivity.class)) {
            scenario = active;
            signIn();
            open("/kundinnen/?q=Mila+Testgarten");
            waitFor("/kundinnen/", "1 Ergebnis");
            assertTrue(state().getString("text").contains("Mila Testgarten"));
            open("/extensions/?q=Mila+Testgarten");
            waitFor("/extensions/", "1 Position");
            assertTrue(state().getString("text").contains("Kupfer"));
            assertTrue(state().getString("text").contains("149,90"));
            screenshot("android-nach-neustart.png");
        }
    }
}
