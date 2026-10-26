import os
import threading


def start_backend(data_dir, secret, token):
    os.environ["DJANGO_SETTINGS_MODULE"] = "config.desktop_settings"
    os.environ["HAARVINCI_DATA_DIR"] = str(data_dir)
    os.environ["HAARVINCI_DESKTOP_SECRET"] = secret
    os.environ["HAARVINCI_DESKTOP_TOKEN"] = token
    import django

    django.setup()
    from django.core.management import call_command
    from django.core.wsgi import get_wsgi_application
    from django.db import connections
    from waitress import create_server

    call_command("migrate", interactive=False, verbosity=0)
    connections.close_all()
    server = create_server(
        get_wsgi_application(),
        host="127.0.0.1",
        port=0,
        threads=4,
        ident="Haarvinci",
        clear_untrusted_proxy_headers=True,
    )
    thread = threading.Thread(target=server.run, name="haarvinci-backend", daemon=True)
    thread.start()
    return server, thread, f"http://127.0.0.1:{server.effective_port}"


def stop_backend(server, thread):
    server.task_dispatcher.shutdown(timeout=10)
    server.close()
    thread.join(timeout=10)
