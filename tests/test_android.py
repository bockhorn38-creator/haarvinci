import importlib.util
from pathlib import Path

from django.http import HttpResponse
from django.test import RequestFactory, TestCase, override_settings

path = (
    Path(__file__).resolve().parent.parent
    / "android/app/src/main/python/android_backend/middleware.py"
)
spec = importlib.util.spec_from_file_location("android_gate_test", path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


@override_settings(DESKTOP_TOKEN="a-private-android-test-instance-token")
class AndroidGateTests(TestCase):
    def test_only_the_private_android_cookie_grants_access(self):
        gate = module.AndroidGateMiddleware(lambda request: HttpResponse("bereit"))
        for cookie, expected in [
            ("", 403),
            ("haarvinci_android_gate=wrong", 403),
            ("sessionid=a-private-android-test-instance-token", 403),
            ("haarvinci_android_gate=a-private-android-test-instance-token", 200),
        ]:
            with self.subTest(cookie=cookie):
                request = RequestFactory().get("/bereit/", HTTP_COOKIE=cookie)
                self.assertEqual(gate(request).status_code, expected)

    @override_settings(
        ANDROID_MODE=True, DESKTOP_MODE=True, AXES_ENABLED=False, SECURE_SSL_REDIRECT=False
    )
    def test_android_account_offers_native_backup_instead_of_desktop_instructions(self):
        from django.contrib.auth import get_user_model

        user = get_user_model().objects.create_user(username="android-account-test")
        self.client.force_login(user)
        response = self.client.get("/konto/")
        self.assertContains(response, "haarvinci://backup")
        self.assertContains(response, "haarvinci://restore")
        self.assertNotContains(response, "Programmmenü")
        self.assertNotContains(response, 'rel="manifest"')
