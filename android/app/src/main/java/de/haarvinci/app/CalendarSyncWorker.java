package de.haarvinci.app;

import android.content.Context;
import androidx.annotation.NonNull;
import androidx.work.Constraints;
import androidx.work.ExistingPeriodicWorkPolicy;
import androidx.work.ExistingWorkPolicy;
import androidx.work.OneTimeWorkRequest;
import androidx.work.PeriodicWorkRequest;
import androidx.work.WorkManager;
import androidx.work.Worker;
import androidx.work.WorkerParameters;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicReference;
import org.json.JSONObject;

public final class CalendarSyncWorker extends Worker {
    public CalendarSyncWorker(@NonNull Context context, @NonNull WorkerParameters parameters) { super(context, parameters); }
    public static void schedule(Context context) {
        Constraints constraints = new Constraints.Builder().build();
        WorkManager manager = WorkManager.getInstance(context);
        manager.enqueueUniqueWork("haarvinci-device-pending", ExistingWorkPolicy.APPEND_OR_REPLACE,
            new OneTimeWorkRequest.Builder(CalendarSyncWorker.class).setConstraints(constraints).build());
        manager.enqueueUniquePeriodicWork("haarvinci-device-periodic", ExistingPeriodicWorkPolicy.KEEP,
            new PeriodicWorkRequest.Builder(CalendarSyncWorker.class, 15, TimeUnit.MINUTES).setConstraints(constraints).build());
    }
    @NonNull @Override public Result doWork() {
        HaarvinciApplication app = (HaarvinciApplication) getApplicationContext();
        CountDownLatch done = new CountDownLatch(1);
        AtomicReference<Result> result = new AtomicReference<>(Result.retry());
        app.ensureBackend((info, error) -> {
            if (error != null) { done.countDown(); return; }
            app.worker.execute(() -> {
                try {
                    JSONObject report = new JSONObject(app.call("device_background").toString());
                    if (report.has("enabled") && !report.optBoolean("enabled")) WorkManager.getInstance(app).cancelUniqueWork("haarvinci-device-periodic");
                    result.set(report.optBoolean("retry") ? Result.retry() : Result.success());
                } catch (Exception ignored) { result.set(Result.retry()); }
                finally { done.countDown(); }
            });
        });
        try { return done.await(180, TimeUnit.SECONDS) ? result.get() : Result.retry(); }
        catch (InterruptedException error) { Thread.currentThread().interrupt(); return Result.retry(); }
    }
}
