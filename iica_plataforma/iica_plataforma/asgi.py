import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'iica_plataforma.settings')
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
# from django.conf.urls.static import static

from channels.auth import AuthMiddlewareStack
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
# from projects import routing

# application = ProtocolTypeRouter({
#     'http': get_asgi_application(),
#     'websocket': URLRouter(
#         # path('ws/projects/', consumers.ChatConsumer.as_asgi()),
#         routing.websocket_urlpatterns,
#     ),
# })
