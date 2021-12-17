#!/bin/bash

echo "Install nodeJS on the machine"
set +e
nvm install --lts
nvm use --lts

echo "Install jahia-reporter"
npm install -g jahia-reporter
