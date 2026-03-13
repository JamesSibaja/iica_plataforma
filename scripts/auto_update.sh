#!/bin/bash

cd /home/usuario/iica_plataforma || exit

git fetch origin

LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/main)

if [ "$LOCAL" != "$REMOTE" ]; then

    echo "Actualizando servidor $(date)"

    git pull origin main

    make deploy

fi