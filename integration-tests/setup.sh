#!/bin/bash

echo "Install jahia-reporter"
npm install -g jahia-reporter

echo "Exporting important environment variables"
echo "export MANIFEST=${{ inputs.tests_manifest }}" >> $BASH_ENV
