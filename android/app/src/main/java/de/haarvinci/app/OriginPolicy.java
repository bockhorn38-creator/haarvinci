package de.haarvinci.app;

import java.net.URI;

/** Verhindert Navigation und Weitergabe privater Cookies an andere Ziele. */
public final class OriginPolicy {
    private OriginPolicy() {}
    public static boolean isInternal(String origin, String target) {
        try {
            URI expected = new URI(origin);
            URI actual = new URI(target);
            return "http".equals(expected.getScheme())
                && "127.0.0.1".equals(expected.getHost())
                && expected.getRawUserInfo() == null
                && "http".equals(actual.getScheme())
                && "127.0.0.1".equals(actual.getHost())
                && actual.getRawUserInfo() == null
                && expected.getPort() > 0 && expected.getPort() == actual.getPort();
        } catch (Exception ignored) {
            return false;
        }
    }
}
