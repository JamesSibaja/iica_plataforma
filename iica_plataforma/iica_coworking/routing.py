from django.urls import path
from .consumers import KanbanConsumer

websocket_urlpatterns = [
    path("ws/kanban/", KanbanConsumer.as_asgi()),
]