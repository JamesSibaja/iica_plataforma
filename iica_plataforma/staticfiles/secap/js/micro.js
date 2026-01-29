function initializeMap(mapSlide,pos='o',measure='o',draw='o',full='o',slide='o',color='o',saved='o') {
    var i = mapSlide.path;
    var h = mapSlide.zoomI;
    var j = mapSlide.zoomM;
    var k = mapSlide.zoomMin;
    var m = parseFloat(mapSlide.maxLatLng.replace(',', '.'));
    var fe = parseFloat(mapSlide.factor.replace(',', '.'));
    var slide_url_format = "/media/slides/" + i + "/{z}/{y}/{x}.jpg";
    var drawnItems = null;
    // var slideColor = mapslide.color;
    var bounds = L.latLngBounds(
        L.latLng(-m , -m ),
        L.latLng(m , m )
    );

    var map = L.map('map', {
        center: [0, 0],
        zoom: h,
        animate: true
    });

    var layer = L.tileLayer(slide_url_format, {
        minZoom: k,
        noWrap: true,
        keepBuffer: 8,
        maxZoom: j
    }).addTo(map);

     // Función para actualizar el nivel de zoom en el contenedor
    function updateZoomLevel() {
        const zoomLevelElement = document.getElementById('zoom-level');
        zoomLevelElement.innerHTML = 'X ' + (2**(map.getZoom()-h+2));
    }

    // Llamar a la función cuando el zoom cambia
    map.on('zoomend', updateZoomLevel);

    // Inicializar el contenedor con el nivel de zoom actual
    updateZoomLevel();

    if(slide == 's'){
        var customZoomControl = L.control.zoom({
            position: 'bottomright'
        }).addTo(map);
    
        map.removeControl(map.zoomControl);
    }
    if(pos == 'l'){
        console.log("si save Uno");
        var miniMap = new L.Control.MiniMap(
            L.tileLayer(slide_url_format),
            { position: 'bottomleft',toggleDisplay: true }
        );
    } else {
        var miniMap = new L.Control.MiniMap(
            L.tileLayer(slide_url_format),
            { toggleDisplay: true }
        );
    }
    if (full == 'f'){
        L.control.fullscreen({
            position: 'topright',  // Posición del botón (topright, topleft, bottomright, bottomleft)
            title: 'Pantalla completa',  // Texto que aparecerá cuando el usuario pase el cursor sobre el botón
            titleCancel: 'Salir de pantalla completa',  // Texto para salir de pantalla completa
            forceSeparateButton: true  // Mostrar un botón separado para salir de pantalla completa
        }).addTo(map);
    }
    miniMap.addTo(map);

    miniMap._container.style.display = 'none';


    map.attributionControl.setPrefix(false);
   

    map.on('zoomend', function () {
        var currentZoom = map.getZoom();
        var minZoomToShowInMiniMap = parseInt(k, 10) + 5;

        if (currentZoom < minZoomToShowInMiniMap) {
            miniMap._container.style.display = 'none';
            console.log("No");
        } else {
            miniMap._container.style.display = 'block';
            console.log("Sí");
        }
    });

    factorDeEscala = fe;
    var customUnits = {
        micrometros: {
            factor: factorDeEscala,
            display: 'Micrómetros',
            decimals: 4
        },
        milimetros: {
            factor: factorDeEscala*0.001,
            display: 'Milímetros',
            decimals: 4
            },
        sqrmilimetros: {
            factor: factorDeEscala*0.001 * factorDeEscala*0.001,
            display: 'Milímetros cuadrados',
            decimals: 4
            }
        };
    if(measure=='m'){
        i18next.init({
            lng: 'es', // Idioma de localización
            resources: {
                es: {
                    translation: {
                        version: 'Versión', // Ejemplo de traducción
                        lastpoint:  '',
                        // ... Más traducciones aquí
                        
                    }
                }
            }
        });
        L.control.measure({
            units: customUnits,
            primaryLengthUnit: 'micrometros', // Unidad de medida principal
            secondaryLengthUnit: 'milimetros', // Unidad de medida secundaria
            primaryAreaUnit: 'sqrmilimetros', // Unidad de área principal
            secondaryAreaUnit: undefined, // Deja esto como undefined para deshabilitar el cálculo de áreas
            // Posición del control en el mapa
            activeColor: '#db4a29', // Color activo para las líneas y áreas medidas
            completedColor: '#9b2d14', // Color completado para las líneas y áreas medidas
            position: 'bottomright',
            localization: 'es', 
            className: 'custom-measure-control',
        }).addTo(map);

        

        function updateBigImage(maxScale ) {
            // Elimina el control existente si hay uno
            if (map.bigImageControl) {
                map.removeControl(map.bigImageControl);
            }
        
            // Crea un nuevo control bigImage con la escala máxima actualizada
            if(maxScale){
                map.bigImageControl = L.control.bigImage({
                    position: 'bottomright',
                    title: 'Obtener imagen',
                    printControlLabel: '📷',
                    printControlClasses: ['custom-big-image-button'],
                    minScale: 1,
                    maxScale: maxScale,
                    inputTitle: 'Escala de foto',
                    downloadTitle: 'Descargar',
                }).addTo(map);
            }
        }
        map.on('zoomend', function () {
            // Supongamos que quieres que la escala máxima aumente a medida que el zoom aumenta
            maxScale =  map.getZoom() - k;
            console.log(maxScale)
            // Actualiza la escala máxima en el control bigImage
            if(maxScale>1){
                updateBigImage((2**(maxScale-1))-1);
            }else{
                updateBigImage(0);
            }
        });
    }
 
    

    if(draw == 'd'){
        drawnItems = new L.FeatureGroup();
        map.addLayer(drawnItems);

        L.drawLocal.draw.toolbar.actions.title = 'Cancelar dibujo';
        L.drawLocal.draw.toolbar.actions.text = 'Cancelar';
        L.drawLocal.draw.toolbar.undo.title = 'Deshacer último punto dibujado';
        L.drawLocal.draw.toolbar.undo.text = 'Deshacer';
        L.drawLocal.draw.toolbar.finish.title = 'Terminar dibujo';
        L.drawLocal.draw.toolbar.finish.text = 'Terminar';

        L.drawLocal.draw.handlers.circle = {
            tooltip: {
                start: 'Haz clic y arrastra para dibujar un círculo.'
            },
            radius: 'Radio'
        };
        L.drawLocal.draw.toolbar.buttons.circle = 'Dibujar un círculo';

        L.drawLocal.draw.handlers.marker = {
            tooltip: {
                start: 'Haz clic en el mapa para colocar el marcador.'
            }
        };
        L.drawLocal.draw.toolbar.buttons.marker = 'Colocar un marcador';

        L.drawLocal.draw.handlers.polygon = {
            tooltip: {
                start: 'Haz clic para comenzar a dibujar el polígono.',
                cont: 'Haz clic para continuar dibujando el polígono.',
                end: 'Haz clic en el primer punto para cerrar este polígono.'
            },
        };
        L.drawLocal.draw.toolbar.buttons.polygon = 'Dibujar un poligono';

        L.drawLocal.draw.handlers.polyline = {
            error: '<strong>Error:</strong> Las aristas no deben cruzarse.',
            tooltip: {
                start: 'Haz clic para comenzar a dibujar la línea.',
                cont: 'Haz clic para continuar dibujando la línea.',
                end: 'Haz clic en el último punto para terminar.'
            },
        };
        L.drawLocal.draw.toolbar.buttons.polyline = 'Dibujar una linea';

        L.drawLocal.draw.handlers.rectangle = {
            tooltip: {
                start: 'Haz clic y arrastra para dibujar un rectángulo.'
            },
        };
        L.drawLocal.draw.toolbar.buttons.rectangle = 'Dibujar un rectangulo';

        L.drawLocal.draw.handlers.circlemarker = {
            tooltip: {
                start: 'Haz clic para colocar un marcador circular.'
            },
        };
        L.drawLocal.draw.toolbar.buttons.circlemarker = 'Colocar un marcador circular';


        L.drawLocal.edit.handlers.edit.tooltip.text = 'Arrastra los manejadores o los marcadores para editar las geometrías.';
        L.drawLocal.edit.handlers.remove.tooltip.text = 'Haz clic en una geometría para eliminarla.';
        L.drawLocal.edit.toolbar.actions.save.text = 'Guardar cambios';
        L.drawLocal.edit.toolbar.actions.cancel.text = 'Cancelar edición';
        L.drawLocal.edit.toolbar.actions.clearAll.text = 'Borrar todo';
        L.drawLocal.edit.toolbar.buttons.edit = 'Editar';
        L.drawLocal.edit.toolbar.buttons.remove = 'Eliminar';
        L.drawLocal.edit.toolbar.buttons.editDisabled = 'No hay entidad para editar.';
        L.drawLocal.edit.toolbar.buttons.removeDisabled = 'No hay entidad para eliminar.';
    
        var drawControl = new L.Control.Draw({
            position: 'bottomright',  // Posición en la esquina inferior derecha
            edit: {
                featureGroup: drawnItems
                
            },
            draw: {
                polygon: true,
                // polyline: true,
                polyline: {
                    metric: false, // Desactiva las medidas métricas
                    feet: false,   // Desactiva las medidas en pies
                    nautic: false, // Desactiva las medidas náuticas
                    showLength: false,  // No muestra la longitud durante el dibujo
                    hintline: {
                        displayLength: false,  // No muestra la longitud de la línea de ayuda
                    },
                    drawing: {
                        polyline: {
                            showLength: false,  // No muestra la longitud de la línea durante el dibujo
                        },
                    },
                },
                rectangle: true,
                circle: true,
                marker: true,
                circlemarker: true,
                
            }
        });
        
        map.addControl(drawControl);
        
        function setupEditing(layer) {
            if (layer instanceof L.Path) { // Verificar si la capa es una línea o polígono
                layer.options.editing = {
                    edit: true,
                    remove: true
                };

                
            }
        }

        
        map.on(L.Draw.Event.CREATED, function (e) {
            var layer = e.layer;
            console.log(layer.editing);
            drawnItems.addLayer(layer);
        });

    }
    if (saved == 'v'){
        if(mapSlide.noteGeojson!= 'None'){
            for (var i = 0; i < mapSlide.noteDraw.features.length; i++) {
                
                L.geoJSON(mapSlide.noteDraw.features[i], {
                    onEachFeature: function (feature, layer) {
                        drawnItems.addLayer(layer);
                        setupEditing(layer);
                    },
                    style: function (feature) {
                        return { color: feature.properties.color };
                    },
                    pointToLayer: function (feature, latlng) {
                        
                        if (feature.geometry.type === "Point" && feature.properties.radius) {
                            if (feature.properties.radius < 0){
                                return L.circleMarker(latlng);  
                            }else{
                                return L.circle(latlng, feature.properties.radius, { color: feature.properties.color });
                            // Crear un circle marker si la característica es un circle marker
                            }
                        } else if (feature.geometry.type === "Point") {
                            // Crear un marcador estándar si la característica es un punto
                            return L.marker(latlng);
                        }
                        return L.layerGroup();
                    }
                }).addTo(map);
                console.log(mapSlide.noteDraw.features[i]);
            }
        }

        
    }
    if (color == 'c'){
        var colorPicker = document.getElementById('colorPicker');

        colorPicker.value = "#3388ff";
        

        colorPicker.addEventListener('change', function () {
            var selectedColor = colorPicker.value;
            // Configurar el color en las opciones de dibujo
            drawControl.setDrawingOptions({
                polyline: {
                shapeOptions: {
                    color: selectedColor
                }
                },
                rectangle: {
                shapeOptions: {
                    color: selectedColor
                }
                },
                polygon: {
                shapeOptions: {
                    color: selectedColor
                }
                },
                circle: {
                shapeOptions: {
                    color: selectedColor
                }
                }
            });
        });
    }
    map.setMaxBounds(bounds);
    map.on('drag', function () {
        map.panInsideBounds(bounds, { animate: false });
    });
    return [map,drawnItems];
}