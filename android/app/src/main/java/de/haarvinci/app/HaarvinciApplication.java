package de.haarvinci.app;

import android.app.Application;
import android.os.Handler;
import android.os.Looper;
import com.chaquo.python.PyObject;
import com.chaquo.python.Python;
import com.chaquo.python.android.AndroidPlatform;
import org.json.JSONObject;
import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public final class HaarvinciApplication extends Application {
    public interface Callback { void complete(RuntimeInfo info, Exception error); }
    public static final class RuntimeInfo {
        final String origin;
        final String token;
        RuntimeInfo(String json) throws Exception {
            JSONObject value = new JSONObject(json);
            origin = value.getString("origin");
            token = value.getString("token");
        }
    }
    final ExecutorService worker = Executors.newSingleThreadExecutor();
    final Handler main = new Handler(Looper.getMainLooper());
    private RuntimeInfo info;
    private PyObject runtime;
    boolean cookiesPrepared = false;
    // Geteilter Text bleibt ausschließlich im Prozess-RAM bis zur Anmeldung.
    String pendingImport;
    long pendingImportAt;

    @Override public void onCreate() {
        super.onCreate();
        CalendarProviderBridge.initialize(this);
        androidx.work.WorkManager.getInstance(this).cancelUniqueWork("haarvinci-google-pending");
        androidx.work.WorkManager.getInstance(this).cancelUniqueWork("haarvinci-google-periodic");
    }
    private android.database.ContentObserver calendarObserver;
    private final Runnable calendarChanged = () -> CalendarSyncWorker.schedule(this);
    void observeCalendars() {
        if (calendarObserver != null || checkSelfPermission(android.Manifest.permission.READ_CALENDAR) != android.content.pm.PackageManager.PERMISSION_GRANTED) return;
        calendarObserver = new android.database.ContentObserver(main) {
            @Override public void onChange(boolean selfChange) { main.removeCallbacks(calendarChanged); main.postDelayed(calendarChanged, 1500); }
        };
        try { getContentResolver().registerContentObserver(android.provider.CalendarContract.CONTENT_URI, true, calendarObserver); }
        catch (SecurityException revoked) { calendarObserver = null; }
    }

    public void ensureBackend(Callback callback) {
        worker.execute(() -> {
            Exception failure = null;
            try {
                if (info == null) {
                    File resourceDir = new File(getFilesDir(), "haarvinci/resources/" + BuildConfig.VERSION_CODE + "-" + getPackageManager().getPackageInfo(getPackageName(), 0).lastUpdateTime);
                    File marker = new File(resourceDir, ".complete");
                    if (!marker.exists()) {
                        copyAssets("haarvinci", resourceDir);
                        new File(resourceDir, "staticfiles").mkdirs();
                        if (!marker.createNewFile()) throw new java.io.IOException("Ressourcen konnten nicht vorbereitet werden.");
                    }
                    if (!Python.isStarted()) Python.start(new AndroidPlatform(this));
                    runtime = Python.getInstance().getModule("android_backend.runtime");
                    info = new RuntimeInfo(runtime.callAttr("start", new File(getFilesDir(), "haarvinci/data").getAbsolutePath(), resourceDir.getAbsolutePath()).toString());
                }
            } catch (Exception error) { failure = error; }
            RuntimeInfo result = info;
            Exception error = failure;
            main.post(() -> callback.complete(result, error));
        });
    }

    private void copyAssets(String source, File destination) throws java.io.IOException {
        String[] children = getAssets().list(source);
        if (children != null && children.length > 0) {
            if (!destination.exists() && !destination.mkdirs()) throw new java.io.IOException("Ordner konnte nicht angelegt werden.");
            for (String child : children) copyAssets(source + "/" + child, new File(destination, child));
        } else {
            try (InputStream input = getAssets().open(source); FileOutputStream output = new FileOutputStream(destination)) {
                byte[] buffer = new byte[32768];
                int count;
                while ((count = input.read(buffer)) != -1) output.write(buffer, 0, count);
                output.getFD().sync();
            }
        }
    }

    PyObject call(String method, Object... arguments) {
        if (runtime == null) throw new IllegalStateException("Haarvinci wird noch vorbereitet.");
        return runtime.callAttr(method, arguments);
    }

    void automaticBackup() {
        worker.execute(() -> {
            try { if (runtime != null) runtime.callAttr("automatic_backup"); }
            catch (Exception error) {
                android.util.Log.e("Haarvinci", "Automatische Sicherung fehlgeschlagen (" + error.getClass().getSimpleName() + ").");
            }
        });
    }

    void restore(File archive, Callback callback) {
        worker.execute(() -> {
            try {
                info = new RuntimeInfo(call("restore", archive.getAbsolutePath()).toString());
                cookiesPrepared = false;
                main.post(() -> callback.complete(info, null));
            } catch (Exception error) { main.post(() -> callback.complete(null, error)); }
            finally { archive.delete(); }
        });
    }
}
