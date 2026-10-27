package de.haarvinci.app;

import android.Manifest;
import android.content.ContentResolver;
import android.content.ContentUris;
import android.content.ContentValues;
import android.content.Context;
import android.database.Cursor;
import android.net.Uri;
import android.provider.CalendarContract;
import android.provider.CalendarContract.Calendars;
import android.provider.CalendarContract.Events;
import androidx.test.core.app.ActivityScenario;
import androidx.test.ext.junit.runners.AndroidJUnit4;
import androidx.test.platform.app.InstrumentationRegistry;
import androidx.test.uiautomator.UiDevice;
import com.chaquo.python.Python;
import org.json.JSONArray;
import org.json.JSONObject;
import org.junit.Test;
import org.junit.runner.RunWith;
import java.time.Instant;
import java.time.LocalDate;
import java.time.ZoneId;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.UUID;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicReference;
import static org.junit.Assert.*;

/** Echte Provider-Transaktionen auf isolierten, ausschließlich fiktiven LOCAL-Kalendern. */
@RunWith(AndroidJUnit4.class)
public class CalendarProviderTest {
    private final Context context = InstrumentationRegistry.getInstrumentation().getTargetContext();
    private final ContentResolver resolver = context.getContentResolver();
    private final ArrayList<Uri> fixtures = new ArrayList<>();
    private Uri adapter(Uri base, String account) {
        // Nur für die Anlage/Entfernung isolierter Testkalender, nie Produktionscode.
        return base.buildUpon().appendQueryParameter(CalendarContract.CALLER_IS_SYNCADAPTER, "true")
            .appendQueryParameter(Calendars.ACCOUNT_NAME, account).appendQueryParameter(Calendars.ACCOUNT_TYPE, CalendarContract.ACCOUNT_TYPE_LOCAL).build();
    }
    private String calendar(String account, int access) {
        ContentValues values = new ContentValues();
        values.put(Calendars.ACCOUNT_NAME, account); values.put(Calendars.ACCOUNT_TYPE, CalendarContract.ACCOUNT_TYPE_LOCAL);
        values.put(Calendars.NAME, account); values.put(Calendars.OWNER_ACCOUNT, account);
        values.put(Calendars.CALENDAR_DISPLAY_NAME, account); values.put(Calendars.CALENDAR_ACCESS_LEVEL, access);
        values.put(Calendars.SYNC_EVENTS, 1); values.put(Calendars.VISIBLE, 1); values.put(Calendars.CALENDAR_TIME_ZONE, "Europe/Berlin");
        Uri created = resolver.insert(adapter(Calendars.CONTENT_URI, account), values);
        assertNotNull(created);
        fixtures.add(adapter(created, account));
        return Long.toString(ContentUris.parseId(created));
    }
    private String fingerprint(String id, String role) throws Exception {
        JSONArray list = new JSONArray(CalendarProviderBridge.calendars(role));
        for (int i=0; i<list.length(); i++) if (list.getJSONObject(i).getString("id").equals(id)) return list.getJSONObject(i).getString("fingerprint");
        throw new AssertionError("Testkalender nicht verfügbar: " + id);
    }
    private long event(String calendar, String title, String start, String end, boolean allDay, String rule) {
        ContentValues values = new ContentValues(); values.put(Events.CALENDAR_ID, Long.parseLong(calendar));
        values.put(Events.TITLE, title); values.put(Events.DESCRIPTION, "Fiktive vertrauliche Beschreibung");
        values.put(Events.DTSTART, Instant.parse(start).toEpochMilli()); values.put(Events.EVENT_TIMEZONE, allDay ? "UTC" : "Europe/Berlin");
        values.put(Events.ALL_DAY, allDay ? 1 : 0);
        if (rule == null) values.put(Events.DTEND, Instant.parse(end).toEpochMilli());
        else { values.put(Events.DURATION, "PT3600S"); values.put(Events.RRULE, rule); }
        Uri inserted = resolver.insert(Events.CONTENT_URI, values); assertNotNull(inserted); return ContentUris.parseId(inserted);
    }
    private void change(String id, ContentValues values) {
        assertEquals(1, resolver.update(Events.CONTENT_URI, values, Events._ID + "=?", new String[]{id}));
    }
    private JSONObject read(String cal, String fp, String marker, String id) throws Exception { return new JSONObject(CalendarProviderBridge.read(cal, fp, marker, id)); }
    private JSONObject write(String cal, String fp, String marker, String id, String revision, String action, JSONObject data) throws Exception { return new JSONObject(CalendarProviderBridge.write(cal, fp, marker, id, revision, action, data.toString())); }
    private void python(HaarvinciApplication app, String script) throws Exception {
        CountDownLatch done = new CountDownLatch(1); AtomicReference<Throwable> failure = new AtomicReference<>();
        app.worker.execute(() -> { try { Python.getInstance().getModule("builtins").callAttr("exec", script); } catch (Throwable error) { failure.set(error); } finally { done.countDown(); } });
        assertTrue("Python-Prüfung läuft zu lange", done.await(90, TimeUnit.SECONDS));
        if (failure.get() != null) throw new AssertionError("Native Backend-Prüfung fehlgeschlagen", failure.get());
    }

    @Test public void actualProviderAndNativeBackend() throws Exception {
        UiDevice device = UiDevice.getInstance(InstrumentationRegistry.getInstrumentation());
        assertFalse("Berechtigungen sollen erst ausdrücklich erteilt werden", new JSONObject(CalendarProviderBridge.permissions()).getBoolean("read"));
        assertEquals("permission", read("0", "fiktiv", "fiktiv", "").getString("status"));
        device.executeShellCommand("pm grant " + context.getPackageName() + " " + Manifest.permission.READ_CALENDAR);
        device.executeShellCommand("pm grant " + context.getPackageName() + " " + Manifest.permission.WRITE_CALENDAR);
        assertTrue(new JSONObject(CalendarProviderBridge.permissions()).getBoolean("write"));
        try (ActivityScenario<MainActivity> active = ActivityScenario.launch(MainActivity.class)) {
            HaarvinciApplication app = (HaarvinciApplication) context.getApplicationContext();
            CountDownLatch started = new CountDownLatch(1);
            app.ensureBackend((info, error) -> { assertNull(error); started.countDown(); });
            assertTrue(started.await(90, TimeUnit.SECONDS));
            String business = calendar("haarvinci-business@example.invalid", Calendars.CAL_ACCESS_OWNER);
            String privateCal = calendar("haarvinci-private@example.invalid", Calendars.CAL_ACCESS_OWNER);
            String readonly = calendar("haarvinci-readonly@example.invalid", Calendars.CAL_ACCESS_READ);
            String fp = fingerprint(business, "business"), privateFp = fingerprint(privateCal, "private");
            JSONArray choices = new JSONArray(CalendarProviderBridge.calendars("business"));
            for (int i=0; i<choices.length(); i++) assertNotEquals(readonly, choices.getJSONObject(i).getString("id"));
            assertEquals("local", CalendarProviderBridge.syncSettings(business, fp));
            assertEquals("calendar", read(business, "falscher-fingerprint", "test", "").getString("status"));
            String marker = UUID.randomUUID().toString().replace("-", "");
            JSONObject data = new JSONObject().put("title", "Lina Fiktiv – Beratung").put("notes", "Fiktive Geschäftsdaten").put("start", "2027-01-15T09:00:00Z").put("end", "2027-01-15T10:00:00Z").put("cancelled", false);
            JSONObject inserted = write(business, fp, marker, "", "", "insert", data);
            assertEquals("Provider-Anlage: " + inserted, "found", inserted.getString("status"));
            String id = inserted.getString("id");
            assertEquals("Marker darf nicht in den Notizen landen", "Fiktive Geschäftsdaten", inserted.getJSONObject("event").getString("notes"));
            assertEquals(id, write(business, fp, marker, "", "", "insert", data).getString("id"));
            String revision = inserted.getString("revision");
            ContentValues remote = new ContentValues(); remote.put(Events.TITLE, "Am Gerät geändert"); change(id, remote);
            assertEquals("race", write(business, fp, marker, id, revision, "update", data).getString("status"));
            JSONObject latest = read(business, fp, marker, id);
            JSONObject updated = write(business, fp, marker, id, latest.getString("revision"), "update", data.put("notes", "Bestätigte Änderung"));
            assertEquals("found", updated.getString("status"));
            // Marker bleibt über den Beschreibungstext erhalten, selbst wenn Google eigene App-Felder entfernt.
            ContentValues strip = new ContentValues(); strip.putNull(Events.CUSTOM_APP_URI); strip.putNull(Events.CUSTOM_APP_PACKAGE); change(id, strip);
            assertEquals(id, read(business, fp, marker, id).getString("id"));
            ContentValues lost = new ContentValues(); lost.put(Events.DESCRIPTION, "Fremde Beschreibung ohne Zuordnung"); change(id, lost);
            assertEquals("identity", read(business, fp, marker, id).getString("status"));
            assertEquals("race", write(business, fp, marker, id, updated.getString("revision"), "delete", data).getString("status"));
            // Private Wiederholungen über die Sommerzeit und ganztägige Sperren.
            long recurring = event(privateCal, "GEHEIM_PRIVAT_TITEL", "2027-03-27T09:00:00Z", null, false, "FREQ=DAILY;COUNT=3");
            event(privateCal, "GEHEIM_GANZTAG", "2027-03-28T00:00:00Z", "2027-03-29T00:00:00Z", true, null);
            ArrayList<String> privateQueries = new ArrayList<>();
            CalendarProviderBridge.audit = (uri, projection, selection, args) -> {
                if (uri.getPath().startsWith("/instances/")) privateQueries.add(String.join(",", projection));
            };
            String privateJson = CalendarProviderBridge.instances(privateCal, privateFp, true, Instant.parse("2027-03-26T00:00:00Z").toEpochMilli(), Instant.parse("2027-03-31T00:00:00Z").toEpochMilli(), "[]");
            CalendarProviderBridge.audit = null;
            assertEquals(4, new JSONArray(privateJson).length());
            assertEquals(Arrays.asList("begin,end,allDay"), privateQueries);
            assertFalse(privateJson.contains("GEHEIM")); assertFalse(privateJson.contains("title"));
            assertTrue("Ganztag muss um Berliner Mitternacht beginnen", privateJson.contains("2027-03-27T23:00:00Z"));
            assertTrue("Sommerzeit am Folgetag", privateJson.contains("2027-03-29T08:00:00Z"));
            String foreignId = Long.toString(event(business, "Fremder Fiktivtermin", "2027-01-20T09:00:00Z", "2027-01-20T10:00:00Z", false, null));
            assertTrue(CalendarProviderBridge.instances(business, fp, false, Instant.parse("2027-01-01T00:00:00Z").toEpochMilli(), Instant.parse("2027-02-01T00:00:00Z").toEpochMilli(), "[]").contains("Fremder Fiktivtermin"));
            // Voller Python-Ausgangskorb gegen diesen echten Provider, zwei Rollen aus zwei Testkonten.
            python(app, "from django.contrib.auth import get_user_model\nfrom django.db import close_old_connections\nfrom django.utils import timezone\nfrom datetime import timedelta\nfrom appointments.models import *\nfrom appointments.device_sync import sync_all, AndroidCalendarBridge\nfrom appointments.device_native import DeviceController\nfrom customers.models import Customer\nu=get_user_model().objects.create_user('fiktiv-provider-owner')\nc=Customer.objects.create(owner=u,first_name='Nele',last_name='Providerfiktiv',email='nele@example.invalid')\nt=timezone.now().replace(microsecond=0)+timedelta(days=20)\na=Appointment.objects.create(owner=u,customer=c,appointment_type=AppointmentType.objects.first(),start_at=t,end_at=t+timedelta(hours=1))\nbridge=AndroidCalendarBridge()\nctl=DeviceController(bridge)\nctl.choose(u,'business','" + business + "')\nctl.choose(u,'private','" + privateCal + "')\nsync_all(bridge,u)\na.refresh_from_db()\nassert a.sync_state=='synced', a.sync_state\nb=DeviceEventBinding.objects.get(appointment=a)\nassert b.provider_id\nfirst=b.provider_id\nsync_all(bridge,u)\nb.refresh_from_db()\nassert b.provider_id==first\na.notes='Offline lokal geändert';a.version+=1;a.save()\nsync_all(bridge,u)\na.refresh_from_db();assert a.sync_state=='synced'\na.status='cancelled';a.version+=1;a.save()\nsync_all(bridge,u)\nsync_all(bridge,u)\na.refresh_from_db();assert a.sync_state=='synced'\nassert not Appointment.objects.filter(notes__contains='GEHEIM').exists()\nclose_old_connections()\n");
            // Fremde und private Termine bleiben unverändert.
            try (Cursor cursor = resolver.query(Events.CONTENT_URI, new String[]{Events.TITLE}, Events._ID + "=?", new String[]{foreignId}, null)) { assertTrue(cursor.moveToFirst()); assertEquals("Fremder Fiktivtermin", cursor.getString(0)); }
            try (Cursor cursor = resolver.query(Events.CONTENT_URI, new String[]{Events.TITLE, Events.RRULE}, Events._ID + "=?", new String[]{Long.toString(recurring)}, null)) { assertTrue(cursor.moveToFirst()); assertEquals("GEHEIM_PRIVAT_TITEL", cursor.getString(0)); assertEquals("FREQ=DAILY;COUNT=3", cursor.getString(1)); }
            // Reine native Update-/Löschtransaktion für eine korrekt zugeordnete eigene Zeile.
            String marker2 = UUID.randomUUID().toString().replace("-", "");
            JSONObject second = write(business, fp, marker2, "", "", "insert", data);
            assertEquals("deleted", write(business, fp, marker2, second.getString("id"), second.getString("revision"), "delete", data).getString("status"));
            String marker3 = UUID.randomUUID().toString().replace("-", "");
            JSONObject third = write(business, fp, marker3, "", "", "insert", data);
            long duplicate = event(business, "Fiktive Kopie", "2027-01-15T09:00:00Z", "2027-01-15T10:00:00Z", false, null);
            ContentValues copiedMarker = new ContentValues(); copiedMarker.put(Events.DESCRIPTION, "[Haarvinci-Verknüpfung: " + marker3 + "]"); change(Long.toString(duplicate), copiedMarker);
            assertEquals("duplicate", read(business, fp, marker3, third.getString("id")).getString("status"));
            assertEquals("race", write(business, fp, marker3, third.getString("id"), third.getString("revision"), "update", data).getString("status"));
            resolver.delete(Events.CONTENT_URI, Events._ID + "=?", new String[]{Long.toString(duplicate)});
            ContentValues moved = new ContentValues(); moved.put(Events.CALENDAR_ID, Long.parseLong(privateCal)); change(third.getString("id"), moved);
            ArrayList<String> movedQueries = new ArrayList<>();
            CalendarProviderBridge.audit = (uri, projection, selection, args) -> { if (uri.equals(Events.CONTENT_URI)) movedQueries.add(String.join(",", projection)); };
            assertEquals("moved", read(business, fp, marker3, third.getString("id")).getString("status"));
            CalendarProviderBridge.audit = null;
            assertEquals(Arrays.asList("_id,calendar_id"), movedQueries);

        } finally {
            CalendarProviderBridge.audit = null;
            for (Uri fixture: fixtures) resolver.delete(fixture, null, null);
        }
    }
}
