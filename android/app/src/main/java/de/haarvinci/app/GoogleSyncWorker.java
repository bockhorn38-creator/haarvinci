package de.haarvinci.app;

import android.content.Context;
import androidx.annotation.NonNull;
import androidx.work.Constraints;
import androidx.work.ExistingPeriodicWorkPolicy;
import androidx.work.ExistingWorkPolicy;
import androidx.work.NetworkType;
import androidx.work.OneTimeWorkRequest;
import androidx.work.PeriodicWorkRequest;
import androidx.work.WorkManager;
import androidx.work.Worker;
import androidx.work.WorkerParameters;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicReference;
import org.json.JSONObject;

public final class GoogleSyncWorker extends Worker {
    public GoogleSyncWorker(@NonNull Context context, @NonNull WorkerParameters parameters) { super(context, parameters); }
    public static void schedule(Context context) {
        Constraints constraints = new Constraints.Builder().setRequiredNetworkType(NetworkType.CONNECTED).build();
        WorkManager manager = WorkManager.getInstance(context);
        manager.enqueueUniqueWork("haarvinci-google-pending", ExistingWorkPolicy.KEEP,
            new OneTimeWorkRequest.Builder(GoogleSyncWorker.class).setConstraints(constraints).build());
        manager.enqueueUniquePeriodicWork("haarvinci-google-periodic", ExistingPeriodicWorkPolicy.KEEP,
            new PeriodicWorkRequest.Builder(GoogleSyncWorker.class, 15, TimeUnit.MINUTES).setConstraints(constraints).build());
    }
    @NonNull @Override public Result doWork() {
        HaarvinciApplication app = (HaarvinciApplication) getApplicationContext();
        CountDownLatch done = new CountDownLatch(1);
        AtomicReference<Result> result = new AtomicReference<>(Result.retry());
        app.ensureBackend((info, error) -> {
            if (error != null) { done.countDown(); return; }
            app.worker.execute(() -> {
                try {
                    JSONObject report = new JSONObject(app.call("google_background", getApplicationContext()).toString());
                    result.set(report.optBoolean("retry") ? Result.retry() : Result.success());
                } catch (Exception ignored) { result.set(Result.retry()); }
                finally { done.countDown(); }
            });
        });
        try { return done.await(180, TimeUnit.SECONDS) ? result.get() : Result.retry(); }
        catch (InterruptedException error) { Thread.currentThread().interrupt(); return Result.retry(); }
    }
}
