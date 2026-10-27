package de.haarvinci.app;

import android.content.Context;
import android.security.keystore.KeyGenParameterSpec;
import android.security.keystore.KeyProperties;
import android.util.Base64;
import java.nio.charset.StandardCharsets;
import java.security.KeyStore;
import javax.crypto.Cipher;
import javax.crypto.KeyGenerator;
import javax.crypto.SecretKey;
import javax.crypto.spec.GCMParameterSpec;

/** Tokens bleiben AES-GCM-verschlüsselt außerhalb der Django-Datenbank/Sicherungen. */
public final class GoogleVault {
    private static final String ALIAS = "haarvinci.google.oauth.aes.v1";
    private static synchronized SecretKey key() throws Exception {
        KeyStore store = KeyStore.getInstance("AndroidKeyStore");
        store.load(null);
        if (store.containsAlias(ALIAS)) return (SecretKey) store.getKey(ALIAS, null);
        KeyGenerator generator = KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, "AndroidKeyStore");
        generator.init(new KeyGenParameterSpec.Builder(ALIAS, KeyProperties.PURPOSE_ENCRYPT | KeyProperties.PURPOSE_DECRYPT)
            .setBlockModes(KeyProperties.BLOCK_MODE_GCM).setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE).setKeySize(256).build());
        return generator.generateKey();
    }
    public static String load(Context context, String label) throws Exception {
        String stored = context.getSharedPreferences("google-vault", Context.MODE_PRIVATE).getString(label, "");
        if (stored.isEmpty()) return "";
        byte[] envelope = Base64.decode(stored, Base64.NO_WRAP);
        if (envelope.length < 29) throw new java.security.GeneralSecurityException("Ungültiger Tokenumschlag");
        Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
        cipher.init(Cipher.DECRYPT_MODE, key(), new GCMParameterSpec(128, java.util.Arrays.copyOfRange(envelope, 0, 12)));
        cipher.updateAAD(label.getBytes(StandardCharsets.UTF_8));
        return new String(cipher.doFinal(envelope, 12, envelope.length - 12), StandardCharsets.UTF_8);
    }
    public static void save(Context context, String label, String value) throws Exception {
        Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
        cipher.init(Cipher.ENCRYPT_MODE, key());
        cipher.updateAAD(label.getBytes(StandardCharsets.UTF_8));
        byte[] encrypted = cipher.doFinal(value.getBytes(StandardCharsets.UTF_8));
        byte[] envelope = new byte[12 + encrypted.length];
        System.arraycopy(cipher.getIV(), 0, envelope, 0, 12);
        System.arraycopy(encrypted, 0, envelope, 12, encrypted.length);
        if (!context.getSharedPreferences("google-vault", Context.MODE_PRIVATE).edit().putString(label, Base64.encodeToString(envelope, Base64.NO_WRAP)).commit()) throw new java.io.IOException("Token konnte nicht gespeichert werden");
    }
    public static void remove(Context context, String label) {
        if (!context.getSharedPreferences("google-vault", Context.MODE_PRIVATE).edit().remove(label).commit()) throw new IllegalStateException("Token konnte nicht entfernt werden");
    }
}
