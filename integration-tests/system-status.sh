#!/bin/bash

echo "Display important system information and environment variables"
echo "node -v: $(node -v)"
echo "npm -v: $(npm -v)"
echo "jahia-reporter -v: $(jahia-reporter -v)"

echo "Displaying important environment variables"
echo "MANIFEST=${MANIFEST}"
echo "JAHIA_IMAGE=${JAHIA_IMAGE}"
echo "TESTS_IMAGE=${TESTS_IMAGE}"
echo "JCUSTOMER_IMAGE=${JCUSTOMER_IMAGE}"
echo "ELASTICSEARCH_IMAGE=${ELASTICSEARCH_IMAGE}"