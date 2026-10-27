package de.haarvinci.app;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.Intent;
import android.graphics.Color;
import android.graphics.Insets;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.provider.DocumentsContract;
import android.view.Menu;
import android.view.MenuItem;
import android.view.View;
import android.view.WindowInsets;
import android.webkit.CookieManager;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.LinearLayout;
import android.widget.ProgressBar;
import android.widget.TextView;
import android.widget.Toast;
import android.widget.Toolbar;
import org.json.JSONObject;
import java.io.ByteArrayInputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;

public final class MainActivity extends Activity {
    private static final int SAVE = 21, OPEN = 22;
    private static final int BACKUP = 1, RESTORE = 2;
    private HaarvinciApplication application;
    private volatile HaarvinciApplication.RuntimeInfo runtime;
    private WebView web;
    private LinearLayout content;
    private TextView status;
    private ProgressBar progress;
    private File pendingExport;
    private boolean authenticated;
    private boolean firstRun;
    private final Handler timer = new Handler(Looper.getMainLooper());
    volatile Uri lastExport;
    private final Runnable hourlyBackup = new Runnable() {
        @Override public void run() {
            application.automaticBackup();
            timer.postDelayed(this, 60L * 60 * 1000);
        }
    };

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        application = (HaarvinciApplication) getApplication();
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setBackgroundColor(Color.rgb(248, 246, 242));
        if (Build.VERSION.SDK_INT >= 30) {
            root.setOnApplyWindowInsetsListener((view, insets) -> {
                Insets bars = insets.getInsets(WindowInsets.Type.systemBars() | WindowInsets.Type.ime());
                root.setPadding(bars.left, bars.top, bars.right, bars.bottom);
                return insets;
            });
        } else root.setFitsSystemWindows(true);
        Toolbar toolbar = new Toolbar(this);
        toolbar.setTitle("Haarvinci");
        toolbar.setTitleTextColor(Color.rgb(91, 40, 62));
        toolbar.setBackgroundColor(Color.rgb(251, 249, 245));
        root.addView(toolbar, new LinearLayout.LayoutParams(-1, dp(56)));
        setActionBar(toolbar);
        content = new LinearLayout(this);
        content.setOrientation(LinearLayout.VERTICAL);
        root.addView(content, new LinearLayout.LayoutParams(-1, 0, 1));
        progress = new ProgressBar(this);
        LinearLayout.LayoutParams spinner = new LinearLayout.LayoutParams(dp(44), dp(44));
        spinner.gravity = android.view.Gravity.CENTER_HORIZONTAL;
        spinner.topMargin = dp(70);
        content.addView(progress, spinner);
        status = new TextView(this);
        status.setText("Dein Kundenbuch wird vorbereitet …");
        status.setTextSize(16);
        status.setTextColor(Color.rgb(91, 40, 62));
        status.setGravity(android.view.Gravity.CENTER);
        status.setPadding(dp(24), dp(24), dp(24), dp(24));
        content.addView(status);
        setContentView(root);
        if (Build.VERSION.SDK_INT >= 33) getOnBackInvokedDispatcher().registerOnBackInvokedCallback(android.window.OnBackInvokedDispatcher.PRIORITY_DEFAULT, this::navigateBack);
        application.ensureBackend(this::backendReady);
    }

    private int dp(int value) { return Math.round(value * getResources().getDisplayMetrics().density); }

    private void backendReady(HaarvinciApplication.RuntimeInfo info, Exception error) {
        if (isFinishing() || isDestroyed()) return;
        if (error != null) {
            progress.setVisibility(View.GONE);
            status.setText("Haarvinci konnte noch nicht geöffnet werden. Bitte starte die App erneut. Deine vorhandenen Daten bleiben erhalten.");
            android.util.Log.e("Haarvinci", "Start fehlgeschlagen (" + error.getClass().getSimpleName() + ").");
            return;
        }
        runtime = info;
        if (web == null) {
            web = new WebView(this);
            WebSettings settings = web.getSettings();
            settings.setJavaScriptEnabled(true);
            settings.setDomStorageEnabled(false);
            settings.setAllowFileAccess(false);
            settings.setAllowContentAccess(false);
            settings.setJavaScriptCanOpenWindowsAutomatically(false);
            settings.setSupportMultipleWindows(false);
            settings.setCacheMode(WebSettings.LOAD_NO_CACHE);
            settings.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);
            WebView.setWebContentsDebuggingEnabled(BuildConfig.DEBUG);
            CookieManager.getInstance().setAcceptThirdPartyCookies(web, false);
            web.setWebViewClient(new AppClient());
            web.setDownloadListener((url, agent, disposition, mime, length) -> exportCustomer(url));
            content.removeAllViews();
            content.addView(web, new LinearLayout.LayoutParams(-1, -1));
        }
        attachCookiesAndOpen();
    }

    private void attachCookiesAndOpen() {
        CookieManager cookies = CookieManager.getInstance();
        cookies.setAcceptCookie(true);
        Runnable open = () -> cookies.setCookie(runtime.origin,
            "haarvinci_android_gate=" + runtime.token + "; Path=/; HttpOnly; SameSite=Strict", accepted -> {
                if (!accepted) { showError("Der geschützte Appzugang konnte nicht eingerichtet werden."); return; }
                application.cookiesPrepared = true;
                web.loadUrl(runtime.origin + "/");
            });
        if (application.cookiesPrepared) open.run();
        else cookies.removeAllCookies(ignored -> open.run());
    }

    private final class AppClient extends WebViewClient {
        @Override public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
            String url = request.getUrl().toString();
            if (OriginPolicy.isInternal(runtime.origin, url)) return false;
            if (request.hasGesture() && request.isForMainFrame() && OriginPolicy.isInternal(runtime.origin, view.getUrl())) {
                if ("haarvinci".equals(request.getUrl().getScheme())) {
                    if ("backup".equals(request.getUrl().getHost()) && authenticated) createBackup();
                    if ("restore".equals(request.getUrl().getHost()) && (authenticated || firstRun)) chooseRestore();
                } else if ("tel".equals(request.getUrl().getScheme()) || "mailto".equals(request.getUrl().getScheme())) {
                    try { startActivity(new Intent("tel".equals(request.getUrl().getScheme()) ? Intent.ACTION_DIAL : Intent.ACTION_SENDTO, request.getUrl())); }
                    catch (android.content.ActivityNotFoundException ignored) { Toast.makeText(MainActivity.this, "Keine passende App gefunden.", Toast.LENGTH_SHORT).show(); }
                }
            }
            return true;
        }

        @Override public WebResourceResponse shouldInterceptRequest(WebView view, WebResourceRequest request) {
            if (OriginPolicy.isInternal(runtime.origin, request.getUrl().toString())) return null;
            return new WebResourceResponse("text/plain", "UTF-8", 403, "Forbidden", java.util.Collections.emptyMap(), new ByteArrayInputStream("Dieser Link ist hier nicht verfügbar.".getBytes(StandardCharsets.UTF_8)));
        }

        @Override public void onPageFinished(WebView view, String url) {
            firstRun = OriginPolicy.isInternal(runtime.origin, url) && "/einrichten/".equals(Uri.parse(url).getPath());
            view.evaluateJavascript("document.body && document.body.dataset.authenticated === 'true'", value -> {
                boolean wasAuthenticated = authenticated;
                authenticated = "true".equals(value) && OriginPolicy.isInternal(runtime.origin, url);
                if (wasAuthenticated && !authenticated) web.clearHistory();
                invalidateOptionsMenu();
            });
        }
    }

    @Override public boolean onCreateOptionsMenu(Menu menu) {
        menu.add(0, BACKUP, 0, "Datensicherung erstellen");
        menu.add(0, RESTORE, 1, "Sicherung wiederherstellen");
        menu.add(0, 3, 2, "Über Haarvinci");
        return true;
    }
    @Override public boolean onPrepareOptionsMenu(Menu menu) {
        menu.findItem(BACKUP).setEnabled(authenticated);
        menu.findItem(RESTORE).setEnabled(authenticated || firstRun);
        return super.onPrepareOptionsMenu(menu);
    }
    @Override public boolean onOptionsItemSelected(MenuItem item) {
        if (item.getItemId() == BACKUP && authenticated) { createBackup(); return true; }
        if (item.getItemId() == RESTORE && (authenticated || firstRun)) { chooseRestore(); return true; }
        if (item.getItemId() == 3) {
            new AlertDialog.Builder(this).setTitle("Haarvinci " + BuildConfig.VERSION_NAME).setMessage("Dein Kundenbuch auf Android.\n\nDie Daten werden lokal auf diesem Gerät gespeichert. Bitte verwende in dieser ersten Testversion ausschließlich fiktive Kundinnen.\n\nEine automatische Synchronisierung mit der Windows-Version ist noch nicht eingerichtet.").setPositiveButton("Schließen", null).show();
            return true;
        }
        return super.onOptionsItemSelected(item);
    }

    private void createBackup() {
        application.worker.execute(() -> {
            try {
                File file = File.createTempFile("haarvinci-", ".haarvinci", getCacheDir());
                application.call("export_backup", file.getAbsolutePath());
                runOnUiThread(() -> saveDocument(file, "Haarvinci-Sicherung.haarvinci", "application/octet-stream"));
            } catch (Exception error) { runOnUiThread(() -> showError("Die Sicherung konnte nicht vorbereitet werden. Deine Kundenakten bleiben erhalten.")); }
        });
    }

    private void exportCustomer(String url) {
        if (!authenticated || !OriginPolicy.isInternal(runtime.origin, url)) return;
        String cookies = CookieManager.getInstance().getCookie(url);
        application.worker.execute(() -> {
            HttpURLConnection connection = null;
            try {
                connection = (HttpURLConnection) new URL(url).openConnection();
                connection.setInstanceFollowRedirects(false);
                connection.setConnectTimeout(15000);
                connection.setReadTimeout(15000);
                connection.setRequestProperty("Cookie", cookies == null ? "" : cookies);
                if (connection.getResponseCode() != 200 || !connection.getContentType().startsWith("application/json")) throw new java.io.IOException("Export nicht verfügbar");
                File file = File.createTempFile("haarvinci-kundin-", ".json", getCacheDir());
                try (InputStream input = connection.getInputStream(); OutputStream output = new FileOutputStream(file)) { copy(input, output); }
                runOnUiThread(() -> saveDocument(file, "Haarvinci-Kundenakte.json", "application/json"));
            } catch (Exception error) { runOnUiThread(() -> showError("Die Kundenakte konnte nicht exportiert werden. Bitte melde dich gegebenenfalls erneut an.")); }
            finally { if (connection != null) connection.disconnect(); }
        });
    }

    private void saveDocument(File file, String title, String mime) {
        if (isFinishing() || isDestroyed()) { file.delete(); return; }
        pendingExport = file;
        Intent intent = new Intent(Intent.ACTION_CREATE_DOCUMENT).addCategory(Intent.CATEGORY_OPENABLE).setType(mime).putExtra(Intent.EXTRA_TITLE, title);
        intent.putExtra(DocumentsContract.EXTRA_INITIAL_URI, Uri.parse("content://com.android.externalstorage.documents/document/primary:Download"));
        startActivityForResult(intent, SAVE);
    }

    private void chooseRestore() {
        Intent intent = new Intent(Intent.ACTION_OPEN_DOCUMENT).addCategory(Intent.CATEGORY_OPENABLE).setType("*/*");
        intent.putExtra(DocumentsContract.EXTRA_INITIAL_URI, Uri.parse("content://com.android.externalstorage.documents/document/primary:Download"));
        startActivityForResult(intent, OPEN);
    }

    @Override public void onActivityResult(int request, int result, Intent data) {
        super.onActivityResult(request, result, data);
        if (request == SAVE) {
            File file = pendingExport;
            pendingExport = null;
            if (file == null) return;
            if (result != RESULT_OK || data == null || data.getData() == null) { file.delete(); return; }
            Uri uri = data.getData();
            application.worker.execute(() -> {
                try (InputStream input = new FileInputStream(file); OutputStream output = getContentResolver().openOutputStream(uri, "wt")) {
                    if (output == null) throw new java.io.IOException("Speicherort nicht verfügbar");
                    copy(input, output);
                    lastExport = uri;
                    runOnUiThread(() -> Toast.makeText(this, "Datei gespeichert.", Toast.LENGTH_LONG).show());
                } catch (Exception error) { runOnUiThread(() -> showError("Die Datei konnte nicht gespeichert werden. Bitte wähle einen anderen Speicherort.")); }
                finally { file.delete(); }
            });
        } else if (request == OPEN && result == RESULT_OK && data != null && data.getData() != null) {
            Uri uri = data.getData();
            application.worker.execute(() -> inspectRestore(uri));
        }
    }

    private void inspectRestore(Uri uri) {
        File archive = null;
        try {
            archive = File.createTempFile("haarvinci-restore-", ".haarvinci", getCacheDir());
            try (InputStream input = getContentResolver().openInputStream(uri); OutputStream output = new FileOutputStream(archive)) {
                if (input == null) throw new java.io.IOException("Sicherung nicht lesbar");
                copy(input, output);
            }
            JSONObject info = new JSONObject(application.call("inspect_backup", archive.getAbsolutePath()).toString());
            int count = info.getInt("customers");
            File checked = archive;
            runOnUiThread(() -> new AlertDialog.Builder(this).setTitle("Sicherung wiederherstellen?")
                .setMessage("Diese geprüfte Sicherung enthält " + count + " Kundenakten. Der aktuelle Stand wird zusätzlich gesichert. Anschließend öffnet Haarvinci den gewählten Datenstand.")
                .setNegativeButton("Abbrechen", (dialog, which) -> checked.delete())
                .setPositiveButton("Wiederherstellen", (dialog, which) -> application.restore(checked, (infoResult, error) -> {
                    if (error != null) showError("Die Sicherung konnte nicht wiederhergestellt werden. Bitte starte die App erneut.");
                    else { runtime = infoResult; authenticated = false; web.clearCache(true); web.clearHistory(); attachCookiesAndOpen(); }
                })).setOnCancelListener(dialog -> checked.delete()).show());
        } catch (Exception error) {
            if (archive != null) archive.delete();
            runOnUiThread(() -> showError("Diese Datei ist keine gültige Haarvinci-Sicherung oder konnte nicht gelesen werden."));
        }
    }

    private static void copy(InputStream input, OutputStream output) throws java.io.IOException {
        byte[] buffer = new byte[32768];
        long total = 0;
        int count;
        while ((count = input.read(buffer)) != -1) {
            total += count;
            if (total > 1024L * 1024 * 1024) throw new java.io.IOException("Datei zu groß");
            output.write(buffer, 0, count);
        }
        output.flush();
    }
    private void showError(String message) {
        if (!isFinishing() && !isDestroyed()) new AlertDialog.Builder(this).setTitle("Haarvinci").setMessage(message).setPositiveButton("Schließen", null).show();
    }
    private void navigateBack() {
        String path = web == null || web.getUrl() == null ? "/" : Uri.parse(web.getUrl()).getPath();
        if (web != null && web.canGoBack() && !"/".equals(path) && !"/anmelden/".equals(path) && !"/einrichten/".equals(path)) web.goBack();
        else finish();
    }
    @Override public void onBackPressed() { navigateBack(); }
    @Override protected void onStart() {
        super.onStart();
        application.automaticBackup();
        timer.postDelayed(hourlyBackup, 60L * 60 * 1000);
    }
    @Override protected void onStop() {
        timer.removeCallbacks(hourlyBackup);
        application.automaticBackup();
        super.onStop();
    }
    @Override protected void onDestroy() {
        if (web != null) { web.stopLoading(); web.destroy(); }
        super.onDestroy();
    }
    WebView appView() { return web; }
    String appOrigin() { return runtime == null ? "" : runtime.origin; }
}
