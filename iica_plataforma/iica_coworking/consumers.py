import json

from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async

from .models import Tarea


class KanbanConsumer(AsyncWebsocketConsumer):

    async def connect(self):

        print("WS CONNECT")

        self.room_group_name = "kanban_global"

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()


    async def disconnect(self, close_code):

        print("WS DISCONNECT")

        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )


    async def receive(self, text_data):

        print("WS RECEIVE:", text_data)

        data = json.loads(text_data)

        tarea_id = data["tarea_id"]
        estado = data["estado"]

        await self.actualizar_tarea(tarea_id, estado)

        await self.channel_layer.group_send(

            self.room_group_name,

            {
                "type": "kanban_update",
                "tarea_id": tarea_id,
                "estado": estado
            }

        )


    async def kanban_update(self, event):

        await self.send(text_data=json.dumps({

            "tarea_id": event["tarea_id"],
            "estado": event["estado"]

        }))


    async def actualizar_tarea(self, tarea_id, estado):

        print("ACTUALIZANDO:", tarea_id, estado)

        await sync_to_async(
            Tarea.objects.filter(id=tarea_id).update
        )(estado=estado)