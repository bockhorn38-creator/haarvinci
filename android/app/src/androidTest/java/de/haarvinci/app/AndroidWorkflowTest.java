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
        String result = js("JSON.stringify({path:location.pathname,query:location.search,text:document.body?document.body.innerText:'',lang:document.documentElement.lang})");
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
        js("for(const [name,value] of Object.entries(" + fields + ")){const input=document.querySelector('[name=\"'+name+'\"]');if(input.type==='checkbox')input.checked=(value==='on'||value==='true');else input.value=value;}document.querySelector('form').requestSubmit();");
    }
    private String waitForText(String text) throws Exception {
        long deadline = System.currentTimeMillis() + 45000;
        while (System.currentTimeMillis() < deadline) {
            JSONObject current = state();
            if (current.getString("text").contains(text)) return current.getString("path");
            Thread.sleep(250);
        }
        throw new AssertionError("Erwarteter Text fehlt: " + text + "; letzte Seite: " + state());
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
        if (item == null) {
            screenshot("android-menue-fehler.png");
            java.io.ByteArrayOutputStream hierarchy = new java.io.ByteArrayOutputStream();
            device.dumpWindowHierarchy(hierarchy);
            throw new AssertionError("Programmmenü fehlt: " + label + "; UI: " + hierarchy.toString("UTF-8"));
        }
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

            String tomorrow = java.time.LocalDate.now(java.time.ZoneId.of("Europe/Berlin")).plusDays(1).toString();
            String pastDay = java.time.LocalDate.now(java.time.ZoneId.of("Europe/Berlin")).minusDays(2).toString();
            String customerId = detail.split("/")[2];
            open("/kalender/neu/?kundin=" + customerId);
            waitFor("/kalender/neu/", "Termin speichern");
            String typeId = js("Array.from(document.querySelector('[name=appointment_type]').options).find(o=>o.value).value");
            fill(new JSONObject().put("day", tomorrow).put("begin", "10:00").put("finish", "11:00").put("appointment_type", typeId).put("buffer_minutes", "15").put("status", "confirmed").put("notes", "Fiktiver Pixel-Termin vor der Sicherung."));
            String appointment = waitForText("Bearbeiten / verschieben");
            assertTrue(state().getString("text").contains("60 Minuten"));
            open(appointment + "bearbeiten/");
            waitFor(appointment + "bearbeiten/", "Termin speichern");
            fill(new JSONObject().put("begin", "12:00").put("finish", "13:00"));
            waitFor(appointment, "12:00");
            open("/kalender/neu/?kundin=" + customerId);
            waitFor("/kalender/neu/", "Termin speichern");
            fill(new JSONObject().put("day", tomorrow).put("begin", "13:00").put("finish", "14:00").put("appointment_type", typeId).put("buffer_minutes", "0"));
            waitFor("/kalender/neu/", "Zeit ist bereits belegt");
            fill(new JSONObject().put("allow_overlap", "on"));
            String cancelled = waitForText("Bearbeiten / verschieben");
            open(cancelled + "absagen/");
            waitFor(cancelled + "absagen/", "Termin verbindlich absagen");
            fill(new JSONObject());
            waitFor(cancelled, "Abgesagt");
            open("/kalender/neu/?kundin=" + customerId);
            waitFor("/kalender/neu/", "Termin speichern");
            fill(new JSONObject().put("day", pastDay).put("begin", "09:00").put("finish", "10:00").put("appointment_type", typeId).put("buffer_minutes", "0").put("status", "completed"));
            waitForText("Bearbeiten / verschieben");
            open(detail);
            waitFor(detail, "1 tatsächlich abgeschlossener Besuch");
            for (String mode : new String[]{"tag", "woche", "monat"}) {
                open("/kalender/?ansicht=" + mode + "&datum=" + tomorrow);
                long viewDeadline = System.currentTimeMillis() + 45000;
                boolean viewReady = false;
                while (System.currentTimeMillis() < viewDeadline) {
                    JSONObject current = state();
                    if (current.optString("query").contains("ansicht=" + mode) && current.getString("text").contains("Mila")) { viewReady = true; break; }
                    Thread.sleep(200);
                }
                assertTrue("Kalenderansicht " + mode + " fehlt: " + state(), viewReady);
                screenshot("android-kalender-" + mode + ".png");
            }
            open("/kalender/google/");
            waitFor("/kalender/google/", "Kalender auf deinem Pixel");
            android.content.Context context = InstrumentationRegistry.getInstrumentation().getTargetContext();
            GoogleVault.save(context, "fiktive-testbindung", "fiktiver-native-zugangstoken");
            assertEquals("fiktiver-native-zugangstoken", GoogleVault.load(context, "fiktive-testbindung"));
            String encrypted = context.getSharedPreferences("google-vault", android.content.Context.MODE_PRIVATE).getString("fiktive-testbindung", "");
            assertFalse(encrypted.contains("fiktiver-native-zugangstoken"));
            context.getSharedPreferences("google-vault", android.content.Context.MODE_PRIVATE).edit().putString("fremde-testbindung", encrypted).commit();
            boolean rejected = false;
            try { GoogleVault.load(context, "fremde-testbindung"); } catch (Exception expected) { rejected = true; }
            assertTrue("Tokenumschlag war nicht an die Kontobindung gebunden", rejected);
            GoogleVault.remove(context, "fiktive-testbindung");
            GoogleVault.remove(context, "fremde-testbindung");

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
            open(appointment + "bearbeiten/");
            waitFor(appointment + "bearbeiten/", "Termin speichern");
            fill(new JSONObject().put("begin", "15:00").put("finish", "16:00"));
            waitFor(appointment, "15:00");
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
            open(appointment);
            waitFor(appointment, "12:00");
            assertTrue(state().getString("text").contains("Fiktiver Pixel-Termin vor der Sicherung."));
            open(detail);
            waitFor(detail, "1 tatsächlich abgeschlossener Besuch");
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
            String tomorrow = java.time.LocalDate.now(java.time.ZoneId.of("Europe/Berlin")).plusDays(1).toString();
            open("/kalender/?ansicht=tag&datum=" + tomorrow);
            waitFor("/kalender/", "Mila Testgarten");
            assertTrue(state().getString("text").contains("12:00"));
            assertTrue(state().getString("text").contains("Abgesagt"));
            screenshot("android-nach-neustart.png");
        }
    }
    @Test public void c_shareAndClipboardImport() throws Exception {
        android.content.Context context = InstrumentationRegistry.getInstrumentation().getTargetContext();
        String day = java.time.LocalDate.now(java.time.ZoneId.of("Europe/Berlin")).plusDays(10).toString();
        JSONObject person = new JSONObject().put("ref", "k1").put("mode", "new").put("data", new JSONObject().put("first_name", "Lina").put("last_name", "Fiktivimport").put("email", "lina.android-import@example.com").put("natural_color", "Dunkelblond").put("desired_length", "50,5"));
        JSONObject extension = new JSONObject().put("customer_ref", "k1").put("data", new JSONObject().put("manufacturer", "Fiktivimport Atelier").put("extension_type", "Tape-Ins").put("color", "Blond").put("length_cm", "50,5").put("weight_g", "100,25").put("purchase_price", "149,90").put("assigned_on", day));
        JSONObject appointment = new JSONObject().put("customer_ref", "k1").put("data", new JSONObject().put("appointment_type", "Erstberatung").put("day", day).put("begin", "10:00").put("finish", "11:00").put("status", "planned").put("buffer_minutes", "15"));
        String payload = new JSONObject().put("format", "haarvinci.import").put("version", 1).put("id", java.util.UUID.randomUUID().toString()).put("customers", new org.json.JSONArray().put(person)).put("extensions", new org.json.JSONArray().put(extension)).put("appointments", new org.json.JSONArray().put(appointment)).toString();
        android.content.Intent share = new android.content.Intent(android.content.Intent.ACTION_SEND).setType("text/plain").putExtra(android.content.Intent.EXTRA_TEXT, payload).setClass(context, MainActivity.class).addFlags(android.content.Intent.FLAG_ACTIVITY_NEW_TASK);
        android.content.Intent implicit = new android.content.Intent(android.content.Intent.ACTION_SEND).setType("text/plain").setPackage(context.getPackageName());
        assertNotNull("Teilen-Empfänger ist nicht registriert", context.getPackageManager().resolveActivity(implicit, 0));
        try (ActivityScenario<MainActivity> active = ActivityScenario.launch(share)) {
            scenario = active;
            waitFor("/anmelden/", "Kundenbuch öffnen");
            fill(new JSONObject().put("username", USER).put("password", PASSWORD));
            String draft = waitForText("Deine Importvorschau");
            assertTrue(draft.startsWith("/uebernehmen/vorschau/"));
            assertTrue(state().getString("text").contains("NOCH NICHT GESPEICHERT"));
            screenshot("android-chatgpt-vorschau.png");
            open("/kundinnen/?q=Fiktivimport");
            waitFor("/kundinnen/", "0 Ergebnisse");
            open(draft);
            waitFor(draft, "Deine Importvorschau");
            js("document.querySelector('input[name=action]').form.requestSubmit();");
            waitFor(draft, "Jetzt verbindlich übernehmen");
            screenshot("android-chatgpt-bestaetigung.png");
            js("document.querySelector('input[name=confirmation]').form.requestSubmit();");
            String receipt = waitForText("Import bereits übernommen");
            assertTrue(receipt.startsWith("/uebernehmen/ergebnis/"));
            open("/kundinnen/?q=Fiktivimport");
            waitFor("/kundinnen/", "1 Ergebnis");
            js("document.querySelector('.customer-card').click();");
            waitForText("Fiktivimport Atelier");
            assertTrue(state().getString("text").contains("50,5 cm"));
            screenshot("android-chatgpt-ergebnis.png");
            // Zwischenablage darf erst bei bewusster Menüaktion gelesen werden.
            scenario.onActivity(activity -> ((android.content.ClipboardManager) activity.getSystemService(android.content.Context.CLIPBOARD_SERVICE)).setPrimaryClip(android.content.ClipData.newPlainText("Fiktiver Haarvinci-Import", payload)));
            menu("Aus ChatGPT einfügen");
            waitFor(receipt, "Import bereits übernommen");
            open("/kundinnen/?q=Fiktivimport");
            waitFor("/kundinnen/", "1 Ergebnis");
            context.startActivity(new android.content.Intent(android.content.Intent.ACTION_SEND).setClass(context, MainActivity.class).addFlags(android.content.Intent.FLAG_ACTIVITY_NEW_TASK).setType("text/plain").putExtra(android.content.Intent.EXTRA_TEXT, "https://chatgpt.com/share/fiktiver-testlink"));
            UiObject2 linkHint = device.wait(Until.findObject(By.textContains("Geteilt wurde nur ein Link")), 15000);
            assertNotNull("Link-Fallback fehlt", linkHint);
            device.findObject(By.res("android:id/button1")).click();
            scenario.onActivity(activity -> ((android.content.ClipboardManager) activity.getSystemService(android.content.Context.CLIPBOARD_SERVICE)).setPrimaryClip(android.content.ClipData.newPlainText("Fiktives unvollständiges Paket", "{\"format\":\"haarvinci.import\",\"version\":1,\"id\":\"" + java.util.UUID.randomUUID() + "\",\"customers\":[{\"ref\":\"k1\",\"mode\":\"new\",\"data\":{\"first_name\":\"Unvollständig\"}}]}")));
            menu("Aus ChatGPT einfügen");
            waitForText("Deine Importvorschau");
            assertTrue(state().getString("text").contains("Dieses Feld ist zwingend erforderlich"));
            open("/konto/");
            waitFor("/konto/", "Sicher abmelden");
            js("document.querySelector('form[action=\"/abmelden/\"]').requestSubmit();");
            waitFor("/anmelden/", "Kundenbuch öffnen");
            context.startActivity(new android.content.Intent(android.content.Intent.ACTION_SEND).setClass(context, MainActivity.class).addFlags(android.content.Intent.FLAG_ACTIVITY_NEW_TASK).setType("text/plain").putExtra(android.content.Intent.EXTRA_TEXT, payload));
            waitFor("/anmelden/", "Kundenbuch öffnen");
            fill(new JSONObject().put("username", USER).put("password", PASSWORD));
            waitFor(receipt, "Import bereits übernommen");
        }
    }
    private void confirmTreatmentPrice(String path) throws Exception {
        waitFor(path, "Deine Preisübersicht");
        js("document.querySelector('button[value=save]').click();");
    }
    private void enterMoney(String treatment, String amount, String purpose, String notes) throws Exception {
        open(treatment + "zahlungen/neu/");
        waitFor(treatment + "zahlungen/neu/", "Zahlung verbindlich buchen");
        fill(new JSONObject().put("amount", amount).put("purpose", purpose).put("notes", notes));
        waitFor(treatment, "Zahlung dokumentiert");
    }
    @Test public void d_fullSalonWorkflow() throws Exception {
        try (ActivityScenario<MainActivity> active = ActivityScenario.launch(MainActivity.class)) {
            scenario = active;
            signIn();
            open("/behandlungen/preise/");
            waitFor("/behandlungen/preise/", "Deine Preisliste");
            fill(new JSONObject().put("name", "Fiktive zwei Reihen").put("category", "weaving").put("rows", "2").put("price", "145,00").put("active", "on"));
            waitFor("/behandlungen/preise/", "Preis gespeichert");
            fill(new JSONObject().put("name", "Fiktive Haarwäsche").put("category", "service").put("rows", "").put("price", "20,00").put("active", "on"));
            waitFor("/behandlungen/preise/", "Fiktive Haarwäsche");
            open("/kundinnen/neu/");
            waitFor("/kundinnen/neu/", "Kundin speichern");
            fill(new JSONObject().put("first_name", "Nele").put("last_name", "Salonfiktiv").put("email", "nele.salon@example.com").put("natural_color", "Braun").put("natural_length", "25,5").put("desired_length", "50"));
            String customer = waitForText("Persönliche Notizen");
            for (int i=0; i<2; i++) {
                open(customer + "extensions/neu/");
                waitFor(customer + "extensions/neu/", "Extensions zuordnen");
                fill(new JSONObject().put("manufacturer", "Salonfiktiv Atelier " + i).put("extension_type", "Tressen").put("color", i==0 ? "Braun" : "Blond").put("length_cm", "50").put("weight_g", "100").put("purchase_price", "50,00").put("sale_price", "100,00").put("assigned_on", java.time.LocalDate.now(java.time.ZoneId.of("Europe/Berlin")).toString()));
                waitFor(customer, "Salonfiktiv Atelier " + i);
            }
            String yesterday = java.time.LocalDate.now(java.time.ZoneId.of("Europe/Berlin")).minusDays(1).toString();
            open("/kalender/neu/?kundin=" + customer.split("/")[2] + "&datum=" + yesterday);
            waitFor("/kalender/neu/", "Termin speichern");
            js("document.querySelector('[name=appointment_type]').selectedIndex=1;");
            fill(new JSONObject().put("begin", "10:00").put("finish", "11:00").put("status", "confirmed"));
            String appointment = waitForText("Bearbeiten / verschieben");
            String create = "/behandlungen/neu/";
            open(create + "?termin=" + appointment.split("/")[2]);
            waitFor(create, "Behandlung erfassen");
            assertEquals("Zwei vorhandene Extensions müssen verknüpft werden", "2", js("document.querySelectorAll('[name=extensions]:checked').length"));
            js("document.querySelector('[name=services]').checked=true;");
            fill(new JSONObject().put("description", "Weaving Salonfiktiv").put("rows", "2").put("status", "planned"));
            confirmTreatmentPrice(create);
            String treatment = waitForText("Vereinbarter Preis");
            assertTrue(state().getString("text").contains("165,00 €"));
            screenshot("android-behandlung-geplant.png");
            enterMoney(treatment, "50,00", "deposit", "Fiktive Anzahlung");
            assertTrue(state().getString("text").contains("115,00 €"));
            open(treatment + "bearbeiten/");
            waitFor(treatment + "bearbeiten/", "Behandlung bearbeiten");
            fill(new JSONObject().put("status", "completed").put("notes", "Weaving durchgeführt. Ausschließlich fiktive Dokumentation."));
            confirmTreatmentPrice(treatment + "bearbeiten/");
            waitFor(treatment, "Durchgeführt");
            open(customer);
            waitFor(customer, "1 tatsächlich abgeschlossener Besuch");
            assertEquals("Kein doppelter Besuch durch die Termin-Verknüpfung", "1", js("document.querySelectorAll('#behandlungen').length"));
            enterMoney(treatment, "65,00", "partial", "Fiktive Teilzahlung");
            assertTrue(state().getString("text").contains("50,00 €"));
            enterMoney(treatment, "50,00", "final", "Fiktive Restzahlung");
            assertTrue(state().getString("text").contains("0,00 €"));
            screenshot("android-behandlung-vollstaendig-bezahlt.png");
            open(treatment + "erstattung/");
            waitFor(treatment + "erstattung/", "Erstattung verbindlich buchen");
            fill(new JSONObject().put("amount", "20,00").put("notes", "Fiktive Teilrückgabe"));
            waitFor(treatment, "Rückerstattung dokumentiert");
            assertTrue(state().getString("text").contains("20,00 €"));
            enterMoney(treatment, "20,00", "final", "Ausgleich nach fiktiver Rückgabe");
            open(treatment + "stornieren/");
            waitFor(treatment + "stornieren/", "Stornierung bestätigen");
            fill(new JSONObject().put("reason", "Fiktiver Stornofall"));
            waitFor(treatment, "Noch zu erstatten");
            for (int i=0; i<4; i++) {
                open(treatment + "erstattung/");
                waitFor(treatment + "erstattung/", "Erstattung verbindlich buchen");
                fill(new JSONObject().put("notes", "Fiktive vollständige Rückgabe " + i));
                waitFor(treatment, "Rückerstattung dokumentiert");
            }
            assertFalse("Nach vollständiger Rückgabe darf keine weitere Erstattung angeboten werden", state().getString("text").contains("Rückerstattung dokumentieren"));
            open(create + "?kundin=" + customer.split("/")[2]);
            waitFor(create, "Behandlung erfassen");
            fill(new JSONObject().put("description", "Individuelle Salonpflege").put("price_mode", "individual").put("custom_price", "90,00").put("status", "planned"));
            confirmTreatmentPrice(create);
            String individual = waitForText("Vereinbarter Preis");
            enterMoney(individual, "30,00", "deposit", "Fiktiver Erfassungsfehler");
            String voidPath = js("Array.from(document.querySelectorAll('a')).find(a=>a.textContent.includes('Fehlerhafte Buchung')).getAttribute('href')");
            open(voidPath);
            waitFor(voidPath, "Stornierung bestätigen");
            fill(new JSONObject().put("reason", "Fiktive Zahlung wurde versehentlich erfasst"));
            waitFor(individual, "Buchung storniert");
            assertTrue(state().getString("text").contains("90,00 €"));
            open("/behandlungen/statistik/");
            waitFor("/behandlungen/statistik/", "Deine Statistik");
            assertTrue(state().getString("text").contains("90,00 €"));
            assertTrue(state().getString("text").contains("Keine ausstehenden Erstattungen"));
            screenshot("android-finanzstatistik.png");
        }
    }

    @Test public void e_salonPersistenceAndImportV2() throws Exception {
        try (ActivityScenario<MainActivity> active = ActivityScenario.launch(MainActivity.class)) {
            scenario=active;
            signIn();
            open("/behandlungen/");
            waitFor("/behandlungen/", "Individuelle Salonpflege");
            assertTrue(state().getString("text").contains("Weaving Salonfiktiv"));
            assertTrue(state().getString("text").contains("90,00 €"));
            // Neues vollständiges Paket nach echtem Prozessneustart via Android-Zwischenablage.
            String day=java.time.LocalDate.now(java.time.ZoneId.of("Europe/Berlin")).plusDays(12).toString();
            JSONObject person=new JSONObject().put("ref","k2").put("mode","new").put("data",new JSONObject().put("first_name","Jana").put("last_name","Paketfiktiv").put("email","jana.paket@example.com"));
            JSONObject treatment=new JSONObject().put("ref","b2").put("mode","new").put("customer_ref","k2").put("data",new JSONObject().put("performed_on",day).put("description","Fiktiver Importvorgang").put("status","planned").put("price_mode","individual").put("custom_price","120,00"));
            JSONObject payment=new JSONObject().put("ref","z2").put("treatment_ref","b2").put("data",new JSONObject().put("amount","30,00").put("booked_on",java.time.LocalDate.now(java.time.ZoneId.of("Europe/Berlin")).toString()).put("method","cash").put("purpose","deposit"));
            String payload=new JSONObject().put("format","haarvinci.import").put("version",2).put("id",java.util.UUID.randomUUID().toString()).put("customers",new org.json.JSONArray().put(person)).put("treatments",new org.json.JSONArray().put(treatment)).put("payments",new org.json.JSONArray().put(payment)).toString();
            scenario.onActivity(activity -> ((android.content.ClipboardManager) activity.getSystemService(android.content.Context.CLIPBOARD_SERVICE)).setPrimaryClip(android.content.ClipData.newPlainText("Fiktives Paket Version 2",payload)));
            menu("Aus ChatGPT einfügen");
            String draft=waitForText("Deine Importvorschau");
            assertTrue(state().getString("text").contains("Behandlung · b2"));
            open("/kundinnen/?q=Paketfiktiv");
            waitFor("/kundinnen/","0 Ergebnisse");
            open(draft);
            waitFor(draft,"Deine Importvorschau");
            js("document.querySelector('input[name=action]').form.requestSubmit();");
            waitFor(draft,"Jetzt verbindlich übernehmen");
            screenshot("android-import-v2-bestaetigung.png");
            js("document.querySelector('input[name=confirmation]').form.requestSubmit();");
            waitForText("Import bereits übernommen");
            open("/behandlungen/");
            waitFor("/behandlungen/","Fiktiver Importvorgang");
            assertTrue(state().getString("text").contains("180,00 €"));
        }
    }

}
