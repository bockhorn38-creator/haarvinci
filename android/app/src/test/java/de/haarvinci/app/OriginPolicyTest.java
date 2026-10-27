package de.haarvinci.app;

import org.junit.Test;
import static org.junit.Assert.*;

public class OriginPolicyTest {
    private static final String ORIGIN = "http://127.0.0.1:43127";
    @Test public void acceptsOnlyTheCurrentLocalService() {
        assertTrue(OriginPolicy.isInternal(ORIGIN, ORIGIN + "/kundinnen/?q=Mila"));
        for (String value : new String[]{"http://127.0.0.1:43128/", "http://localhost:43127/", "https://example.com", "http://127.0.0.1:43127@example.com/", "http://user:pass@127.0.0.1:43127/", "file:///data/user/0/private", "content://private", "javascript:alert(1)", "http://[::1]:43127/"}) {
            assertFalse(value, OriginPolicy.isInternal(ORIGIN, value));
        }
        assertFalse(OriginPolicy.isInternal("http://evil:43127", ORIGIN));
    }
}
