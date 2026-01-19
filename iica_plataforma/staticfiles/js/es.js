L.drawLocal = {
  draw: {
    toolbar: {
      actions: {
        title: 'Cancelar dibujo',
        text: 'Cancelar',
      },
      finish: {
        title: 'Finalizar dibujo',
        text: 'Finalizar',
      },
      undo: {
        title: 'Eliminar último punto',
        text: 'Eliminar último punto',
      },
      buttons: {
        polyline: 'Dibujar una línea',
        polygon: 'Dibujar un polígono',
        rectangle: 'Dibujar un rectángulo',
        circle: 'Dibujar un círculo',
        marker: 'Dibujar un marcador',
      },
    },
    handlers: {
      circle: {
        tooltip: {
          start: 'Haz clic y arrastra para dibujar un círculo.',
        },
        radius: 'Radio',
      },
      marker: {
        tooltip: {
          start: 'Haz clic en el mapa para colocar un marcador.',
        },
      },
      polygon: {
        tooltip: {
          start: 'Haz clic para comenzar a dibujar la forma.',
          cont: 'Haz clic para continuar dibujando la forma.',
          end: 'Haz clic en el primer punto para cerrar esta forma.',
        },
      },
      polyline: {
        error: '<strong>Error:</strong> las aristas no deben cruzarse.',
        tooltip: {
          start: 'Haz clic para comenzar a dibujar la línea.',
          cont: 'Haz clic para continuar dibujando la línea.',
          end: 'Haz clic en el último punto para finalizar la línea.',
        },
      },
      rectangle: {
        tooltip: {
          start: 'Haz clic y arrastra para dibujar un rectángulo.',
        },
      },
      simpleshape: {
        tooltip: {
          end: 'Suelta el mouse para finalizar el dibujo.',
        },
      },
    },
  },
  edit: {
    toolbar: {
      actions: {
        save: {
          title: 'Guardar cambios.',
          text: 'Guardar',
        },
        cancel: {
          title: 'Cancelar edición, descartar todos los cambios.',
          text: 'Cancelar',
        },
        clearAll: {
          title: 'Eliminar todas las capas.',
          text: 'Eliminar todo',
        },
      },
      buttons: {
        edit: 'Editar capas.',
        editDisabled: 'No hay capas para editar.',
        remove: 'Eliminar capas.',
        removeDisabled: 'No hay capas para eliminar.',
      },
    },
    handlers: {
      edit: {
        tooltip: {
          text: 'Arrastra los vértices o las marcas para editar la geometría.',
          subtext: 'Haz clic en cancelar para deshacer los cambios.',
        },
      },
      remove: {
        tooltip: {
          text: 'Haz clic en una figura para eliminarla.',
        },
      },
    },
  },
};