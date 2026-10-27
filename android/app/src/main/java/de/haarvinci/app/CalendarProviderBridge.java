package de.haarvinci.app;

import android.Manifest;
import android.accounts.Account;
import android.content.ContentProviderOperation;
import android.content.ContentProviderResult;
import android.content.ContentResolver;
import android.content.ContentUris;
import android.content.ContentValues;
import android.content.Context;
import android.content.OperationApplicationException;
import android.content.pm.PackageManager;
import android.database.Cursor;
import android.net.Uri;
import android.provider.CalendarContract;
import android.provider.CalendarContract.Calendars;
import android.provider.CalendarContract.Events;
import android.provider.CalendarContract.Instances;
import org.json.JSONArray;
import org.json.JSONObject;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.time.Instant;
import java.time.ZoneId;
import java.time.ZoneOffset;
import java.util.ArrayList;
import java.util.HashSet;

/** Ausschließlich normale CalendarContract-Aufrufe, keine Sync-Adapter-Imitation. */
public final class CalendarProviderBridge {
    private static Context app;
    static void initialize(Context context) { app = context.getApplicationContext(); }
    interface QueryAudit { void query(Uri uri, String[] projection, String selection, String[] args); }
    static QueryAudit audit; // Nur Instrumentierung im selben Prozess; kein exportierter App-/JS-Einstieg.
    private static final String[] CAL = {Calendars._ID, Calendars.ACCOUNT_NAME, Calendars.ACCOUNT_TYPE, Calendars.NAME, Calendars.OWNER_ACCOUNT, Calendars.CALENDAR_DISPLAY_NAME, Calendars.CALENDAR_ACCESS_LEVEL, Calendars.SYNC_EVENTS};
    private static final String[] EVENT = {Events._ID, Events.CALENDAR_ID, Events.TITLE, Events.DESCRIPTION, Events.DTSTART, Events.DTEND, Events.EVENT_TIMEZONE, Events.ALL_DAY, Events.STATUS, Events.DELETED, Events.RRULE, Events.RDATE, Events.EXRULE, Events.EXDATE, Events.ORIGINAL_ID, Events.CUSTOM_APP_PACKAGE, Events.CUSTOM_APP_URI};
    private static ContentResolver resolver() { if (app == null) throw new IllegalStateException(); return app.getContentResolver(); }
    private static Cursor query(Uri uri, String[] projection, String selection, String[] args) {
        if (audit != null) audit.query(uri, projection.clone(), selection, args == null ? null : args.clone());
        Cursor cursor = resolver().query(uri, projection, selection, args, null);
        if (cursor == null) throw new IllegalStateException("Kalender nicht erreichbar");
        return cursor;
    }
    public static String permissions() {
        return "{\"read\":" + has(Manifest.permission.READ_CALENDAR) + ",\"write\":" + has(Manifest.permission.WRITE_CALENDAR) + "}";
    }
    private static boolean has(String permission) { return app != null && app.checkSelfPermission(permission) == PackageManager.PERMISSION_GRANTED; }
    private static void requireRead() { if (!has(Manifest.permission.READ_CALENDAR)) throw new SecurityException(); }
    private static void requireWrite() { requireRead(); if (!has(Manifest.permission.WRITE_CALENDAR)) throw new SecurityException(); }
    private static String hash(String value) throws Exception {
        byte[] bytes = MessageDigest.getInstance("SHA-256").digest(value.getBytes(StandardCharsets.UTF_8));
        StringBuilder out = new StringBuilder(); for (byte b: bytes) out.append(String.format(java.util.Locale.ROOT, "%02x", b & 255)); return out.toString();
    }
    private static JSONObject row(Cursor cursor, String[] projection) throws Exception {
        JSONObject result = new JSONObject();
        for (int i=0; i<projection.length; i++) result.put(projection[i], cursor.isNull(i) ? JSONObject.NULL : cursor.getString(i));
        return result;
    }
    private static String fingerprint(JSONObject calendar) throws Exception {
        JSONArray fields = new JSONArray();
        for (String name: new String[]{Calendars.ACCOUNT_NAME, Calendars.ACCOUNT_TYPE, Calendars.NAME, Calendars.OWNER_ACCOUNT}) fields.put(calendar.opt(name));
        return hash(fields.toString());
    }
    public static String calendars(String role) throws Exception {
        requireRead(); if (!role.equals("business") && !role.equals("private")) throw new IllegalArgumentException();
        JSONArray result = new JSONArray();
        try (Cursor cursor = query(Calendars.CONTENT_URI, CAL, Calendars.SYNC_EVENTS + "=1 AND " + Calendars.CALENDAR_ACCESS_LEVEL + ">=?", new String[]{role.equals("business") ? "500" : "100"})) {
            while (cursor.moveToNext()) {
                JSONObject item = row(cursor, CAL);
                result.put(new JSONObject().put("id", item.getString(Calendars._ID)).put("fingerprint", fingerprint(item))
                    .put("label", item.optString(Calendars.CALENDAR_DISPLAY_NAME, "Kalender") + " · " + item.optString(Calendars.ACCOUNT_NAME, "") + ("com.google".equals(item.optString(Calendars.ACCOUNT_TYPE)) ? " · Google" : " · Gerätekalender")));
            }
        }
        return result.toString();
    }
    private static JSONObject calendar(String id, String expected, boolean write) throws Exception {
        requireRead();
        try (Cursor cursor = query(Calendars.CONTENT_URI, CAL, Calendars._ID + "=?", new String[]{id})) {
            if (cursor.getCount() != 1 || !cursor.moveToFirst()) throw new IllegalArgumentException("calendar");
            JSONObject row = row(cursor, CAL);
            if (!fingerprint(row).equals(expected) || (write && row.getInt(Calendars.CALENDAR_ACCESS_LEVEL) < Calendars.CAL_ACCESS_CONTRIBUTOR)) throw new IllegalArgumentException("calendar");
            return row;
        }
    }
    public static String syncSettings(String id, String expected) {
        try {
            JSONObject calendar = calendar(id, expected, false);
            if (!"com.google".equals(calendar.getString(Calendars.ACCOUNT_TYPE))) return "local";
            if (calendar.getInt(Calendars.SYNC_EVENTS) == 0 || !ContentResolver.getMasterSyncAutomatically() || !ContentResolver.getSyncAutomatically(new Account(calendar.getString(Calendars.ACCOUNT_NAME), calendar.getString(Calendars.ACCOUNT_TYPE)), CalendarContract.AUTHORITY)) return "disabled";
            return "enabled";
        } catch (Exception error) { return "unknown"; }
    }
    private static String uri(String marker) { return "haarvinci://calendar-binding/" + marker; }
    private static String tag(String marker) { return "[Haarvinci-Verknüpfung: " + marker + "]"; }
    private static String description(String notes, String marker) { return notes + "\n\n" + tag(marker); }
    private static String notes(String description, String marker) {
        return description.replace(tag(marker), "").replaceAll("\\s+$", "");
    }
    private static String text(JSONObject object, String name) { return object.isNull(name) ? "" : object.optString(name, ""); }
    private static boolean owns(JSONObject event, String marker) {
        return (app.getPackageName().equals(text(event, Events.CUSTOM_APP_PACKAGE)) && uri(marker).equals(text(event, Events.CUSTOM_APP_URI))) || text(event, Events.DESCRIPTION).contains(tag(marker));
    }
    private static String revision(JSONObject event) throws Exception {
        JSONArray fields = new JSONArray(); for (String name: EVENT) fields.put(event.opt(name)); return hash(fields.toString());
    }
    private static JSONObject locate(String id, String expected, String marker, String knownId) throws Exception {
        calendar(id, expected, false);
        // Globale Suche liest ausschließlich Zuordnungs-Metadaten, niemals private Inhalte.
        try (Cursor cursor = query(Events.CONTENT_URI, new String[]{Events._ID, Events.CALENDAR_ID}, Events.CUSTOM_APP_URI + "=?", new String[]{uri(marker)})) {
            while (cursor.moveToNext()) if (!id.equals(cursor.getString(1))) return new JSONObject().put("status", "moved");
        }
        ArrayList<JSONObject> live = new ArrayList<>(), deleted = new ArrayList<>();
        try (Cursor cursor = query(Events.CONTENT_URI, EVENT, Events.CALENDAR_ID + "=? AND (" + Events.CUSTOM_APP_URI + "=? OR " + Events.DESCRIPTION + " LIKE ?)", new String[]{id, uri(marker), "%" + tag(marker) + "%"})) {
            while (cursor.moveToNext()) {
                JSONObject event = row(cursor, EVENT);
                if (!owns(event, marker)) continue;
                if (event.optInt(Events.DELETED) == 1 || event.optInt(Events.STATUS) == Events.STATUS_CANCELED) deleted.add(event); else live.add(event);
            }
        }
        if (live.size() > 1 || (live.isEmpty() && deleted.size() > 1)) return new JSONObject().put("status", "duplicate");
        if (!live.isEmpty()) return live.get(0);
        if (!deleted.isEmpty()) return deleted.get(0);
        if (!knownId.isEmpty()) {
            try (Cursor cursor = query(Events.CONTENT_URI, new String[]{Events._ID, Events.CALENDAR_ID}, Events._ID + "=?", new String[]{knownId})) {
                if (cursor.moveToFirst()) return new JSONObject().put("status", id.equals(cursor.getString(1)) ? "identity" : "moved");
            }
        }
        return new JSONObject().put("status", "missing");
    }
    private static JSONObject publicEvent(JSONObject event, String marker) throws Exception {
        if (event.has("status")) return event;
        if (!text(event, Events.RRULE).isEmpty() || !text(event, Events.RDATE).isEmpty() || !event.isNull(Events.ORIGINAL_ID)) return new JSONObject().put("status", "recurring");
        JSONObject out = new JSONObject().put("status", "found").put("id", event.getString(Events._ID)).put("revision", revision(event));
        boolean cancelled = event.optInt(Events.DELETED) == 1 || event.optInt(Events.STATUS) == Events.STATUS_CANCELED;
        out.put("event", new JSONObject().put("start", Instant.ofEpochMilli(event.optLong(Events.DTSTART)).toString())
            .put("end", Instant.ofEpochMilli(event.optLong(Events.DTEND)).toString()).put("title", text(event, Events.TITLE))
            .put("notes", notes(text(event, Events.DESCRIPTION), marker)).put("cancelled", cancelled)
            .put("all_day", event.optInt(Events.ALL_DAY) == 1));
        out.put("marker_present", text(event, Events.DESCRIPTION).contains(tag(marker)));
        return out;
    }
    public static String read(String id, String expected, String marker, String knownId) {
        try { return publicEvent(locate(id, expected, marker, knownId), marker).toString(); }
        catch (SecurityException error) { return "{\"status\":\"permission\"}"; }
        catch (Exception error) { return "{\"status\":\"calendar\"}"; }
    }
    private static ContentValues values(JSONObject data, String id, String marker) throws Exception {
        ContentValues values = new ContentValues();
        values.put(Events.CALENDAR_ID, Long.parseLong(id));
        values.put(Events.TITLE, data.getString("title"));
        values.put(Events.DESCRIPTION, description(data.getString("notes"), marker));
        values.put(Events.DTSTART, Instant.parse(data.getString("start")).toEpochMilli());
        values.put(Events.DTEND, Instant.parse(data.getString("end")).toEpochMilli());
        values.put(Events.EVENT_TIMEZONE, "Europe/Berlin"); values.put(Events.ALL_DAY, 0);
        values.put(Events.CUSTOM_APP_PACKAGE, app.getPackageName()); values.put(Events.CUSTOM_APP_URI, uri(marker));
        return values;
    }
    private static ContentValues expectedValues(JSONObject object, String[] columns) throws Exception {
        ContentValues values = new ContentValues();
        for (String name: columns) { if (object.isNull(name)) values.putNull(name); else values.put(name, object.getString(name)); }
        return values;
    }
    public static String write(String id, String expected, String marker, String knownId, String expectedRevision, String action, String payload) {
        try {
            requireWrite(); JSONObject cal = calendar(id, expected, true);
            JSONObject existing = locate(id, expected, marker, knownId);
            ArrayList<ContentProviderOperation> ops = new ArrayList<>();
            ops.add(ContentProviderOperation.newAssertQuery(Calendars.CONTENT_URI).withSelection(Calendars._ID + "=?", new String[]{id})
                .withValues(expectedValues(cal, CAL)).withExpectedCount(1).build());
            if (action.equals("insert")) {
                if (!"missing".equals(existing.optString("status"))) return publicEvent(existing, marker).toString();
                ops.add(ContentProviderOperation.newAssertQuery(Events.CONTENT_URI).withSelection(Events.CALENDAR_ID + "=? AND (" + Events.CUSTOM_APP_URI + "=? OR " + Events.DESCRIPTION + " LIKE ?)", new String[]{id, uri(marker), "%" + tag(marker) + "%"}).withValue(Events._ID, -1).withExpectedCount(0).build());
                ops.add(ContentProviderOperation.newInsert(Events.CONTENT_URI).withValues(values(new JSONObject(payload), id, marker)).build());
            } else {
                if (existing.has("status") || !publicEvent(existing, marker).optString("status").equals("found") || !revision(existing).equals(expectedRevision)) return "{\"status\":\"race\"}";
                String selection = Events._ID + "=? AND " + Events.CALENDAR_ID + "=?";
                String[] args = {existing.getString(Events._ID), id};
                ops.add(ContentProviderOperation.newAssertQuery(Events.CONTENT_URI).withSelection(selection, args).withValues(expectedValues(existing, EVENT)).withExpectedCount(1).build());
                if (action.equals("delete")) ops.add(ContentProviderOperation.newDelete(Events.CONTENT_URI).withSelection(selection, args).withExpectedCount(1).build());
                else if (action.equals("update")) ops.add(ContentProviderOperation.newUpdate(Events.CONTENT_URI).withSelection(selection, args).withValues(values(new JSONObject(payload), id, marker)).withExpectedCount(1).build());
                else throw new IllegalArgumentException();
            }
            ContentProviderResult[] results = resolver().applyBatch(CalendarContract.AUTHORITY, ops);
            if (action.equals("delete")) return "{\"status\":\"deleted\"}";
            String rowId = action.equals("insert") ? Long.toString(ContentUris.parseId(results[results.length - 1].uri)) : existing.getString(Events._ID);
            return publicEvent(locate(id, expected, marker, rowId), marker).toString();
        } catch (SecurityException error) { return "{\"status\":\"permission\",\"definite\":true}"; }
        catch (OperationApplicationException error) { return "{\"status\":\"race\",\"definite\":true}"; }
        catch (Exception error) { return "{\"status\":\"unavailable\"}"; }
    }
    private static long boundary(long millis, boolean allDay) {
        return allDay ? Instant.ofEpochMilli(millis).atZone(ZoneOffset.UTC).toLocalDate().atStartOfDay(ZoneId.of("Europe/Berlin")).toInstant().toEpochMilli() : millis;
    }
    public static String instances(String id, String expected, boolean privateRole, long start, long end, String skipJson) throws Exception {
        calendar(id, expected, false);
        JSONArray skipped = new JSONArray(skipJson); HashSet<String> skip = new HashSet<>();
        for (int i=0; i<skipped.length(); i++) skip.add(skipped.getString(i));
        Uri.Builder builder = Instances.CONTENT_URI.buildUpon(); ContentUris.appendId(builder, start); ContentUris.appendId(builder, end);
        String[] projection = privateRole ? new String[]{Instances.BEGIN, Instances.END, Instances.ALL_DAY} : new String[]{Instances.BEGIN, Instances.END, Instances.ALL_DAY, Instances.EVENT_ID, Instances.TITLE};
        JSONArray rows = new JSONArray();
        try (Cursor cursor = query(builder.build(), projection, Instances.CALENDAR_ID + "=? AND " + Events.DELETED + "=0 AND (" + Instances.STATUS + " IS NULL OR " + Instances.STATUS + "!=2) AND (" + Instances.AVAILABILITY + " IS NULL OR " + Instances.AVAILABILITY + "!=1)", new String[]{id})) {
            while (cursor.moveToNext()) {
                boolean allDay = cursor.getInt(2) == 1;
                if (!privateRole && skip.contains(cursor.getString(3))) continue;
                JSONObject row = new JSONObject().put("start", Instant.ofEpochMilli(boundary(cursor.getLong(0), allDay)).toString()).put("end", Instant.ofEpochMilli(boundary(cursor.getLong(1), allDay)).toString());
                if (!privateRole) row.put("id", cursor.getString(3) + ":" + cursor.getLong(0)).put("title", cursor.getString(4) == null ? "Geschäftlich belegt" : cursor.getString(4));
                rows.put(row);
            }
        }
        return rows.toString();
    }
}
