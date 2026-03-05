# iica_plataforma
Este es el repositorio de la plataforma de herramientas digitales para fortalecer la gestión interna, la comunicación, el trabajo colaborativo y la resolución oportuna de conflictos, de la oficina del IICA en CR.

## Requisitos previos

Para desplegar esta plataforma en tu servidor local, asegúrate de tener instalados los siguientes programas:

- makefile
- git
- Docker
- Docker Compose

## Instalación

Para comenzar, clona este repositorio utilizando el siguiente comando:

```bash
git clone https://github.com/JamesSibaja/iica_plataforma.git
```

Luego, dirígete al directorio principal del repositorio:

```bash
cd iica_plataforma
```

## Despliegue en servidor local

Para desplegar la plataforma en tu servidor local, ejecuta el siguiente comando: 

```bash
sudo make setup
```
Escribe 'n' cuando pregunte '¿Modo producción? ' y sigue las intrucciones

## Despliegue en servidor

Si deseas desplegar la plataforma en un servidor ejecuta el siguiente comando:

```bash
sudo make setup
```
Escribe 's' cuando pregunte '¿Modo producción? ' y sigue las intrucciones

## Actualizaciones

Para realizar actualizaciones ejecuta el siguiente comando:

```bash
sudo make deploy
```

## Información adicional

Este sistema ha sido probado en Ubuntu 24.04
