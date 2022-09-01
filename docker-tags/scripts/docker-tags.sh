Setup() {    
    echo "$(date +'%d %B %Y - %k:%M') - Setup: Evaluating the variables coming from context"

    PARAM_VERSION_MAJOR=$(echo "${PARAM_VERSION}" | awk -F . '{print $1}' )
    PARAM_VERSION_MINOR=$(echo "${PARAM_VERSION}" | awk -F . '{print $2}' )
    PARAM_VERSION_HF=$(echo "${PARAM_VERSION}" | awk -F . '{print $3}' )
    PARAM_VERSION_CLASSIFIER=$(echo "${PARAM_VERSION}" | awk -F - '{print $2}' )

    if [ "$PARAM_VERSION_CLASSIFIER" != "" ]; then
        PARAM_VERSION_CLASSIFIER='-'$PARAM_VERSION_CLASSIFIER
    fi

    AUTH_DOMAIN="auth.docker.io"
    AUTH_SERVICE="registry.docker.io"
    AUTH_SCOPE="repository:${PARAM_ORG}/${PARAM_REPO}:pull"
    AUTH_OFFLINE_TOKEN="1"
    AUTH_CLIENT_ID="shell"

    API_DOMAIN="registry-1.docker.io"
}

GetToken() {
    echo "$(date +'%d %B %Y - %k:%M') - GetToken: Fetching Token from container registry: ${AUTH_SERVICE}"
    curl -s -X GET -u "${PARAM_USERNAME}":"${PARAM_PASSWORD}" "https://${AUTH_DOMAIN}/token?service=${AUTH_SERVICE}&scope=${AUTH_SCOPE}&offline_token=${AUTH_OFFLINE_TOKEN}&client_id=${AUTH_CLIENT_ID}
    TOKEN=$(curl -s -X GET -u "${PARAM_USERNAME}":"${PARAM_PASSWORD}" "https://${AUTH_DOMAIN}/token?service=${AUTH_SERVICE}&scope=${AUTH_SCOPE}&offline_token=${AUTH_OFFLINE_TOKEN}&client_id=${AUTH_CLIENT_ID}" | jq -r '.token')
    echo "$(date +'%d %B %Y - %k:%M') - GetToken: Fetch complete"
}

GetVersions() {
    echo "$(date +'%d %B %Y - %k:%M') - GetVersions: Fetching container versions from container registry: ${AUTH_SERVICE}"
    VERSIONS=$(curl -s -H "Authorization: Bearer ${TOKEN}" https://${API_DOMAIN}/v2/"${PARAM_ORG}"/"${PARAM_REPO}"/tags/list | jq -r '.tags[]' | grep -E "^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$PARAM_VERSION_CLASSIFIER$")
    echo "$(date +'%d %B %Y - %k:%M') - GetVersions: Fetch complete"
}

DockerTags() {
    REGISTRY_VERSIONS=$(echo "$VERSIONS" | awk -vORS=, '{ print $1 }' | sed 's/,$/\n/')   
    echo "$(date +'%d %B %Y - %k:%M') - The following tags exists in ${PARAM_ORG}/${PARAM_REPO}: ${REGISTRY_VERSIONS}"

    if ! (echo "$VERSIONS" | grep "$PARAM_VERSION"); then   
        echo "$(date +'%d %B %Y - %k:%M') - Version ${PARAM_VERSION} does not exist in the repository"
        echo "$(date +'%d %B %Y - %k:%M') - The orb is meant at tagging existing images"
        echo "$(date +'%d %B %Y - %k:%M') - The orb will TERMINATE"
        exit 1
    fi

    if ! (echo "$VERSIONS" | grep "$PARAM_VERSION"); then
        echo "$PARAM_VERSION" not found yet, adding it
        VERSIONS=$(echo -e "${VERSIONS}\n${PARAM_VERSION}")
    fi

    VERSIONS=$(echo "$VERSIONS" | sort --version-sort)

    LATEST=$(echo "$VERSIONS" | tail -1)
    MATCHING1=$(echo "$VERSIONS" | grep -E "^${PARAM_VERSION_MAJOR}\." | tail -1)
    MATCHING2=$(echo "$VERSIONS" | grep -E "^${PARAM_VERSION_MAJOR}\.${PARAM_VERSION_MINOR}\." | tail -1)
    MATCHING3=$(echo "$VERSIONS" | grep -E "^${PARAM_VERSION_MAJOR}\.${PARAM_VERSION_MINOR}\.${PARAM_VERSION_HF}\." | tail -1)

    if [[ $PARAM_DRYRUN -eq 0 ]]; then
        echo "$(date +'%d %B %Y - %k:%M') - Pulling docker image prior to tagging"
        docker pull "${PARAM_ORG}"/"${PARAM_REPO}":"${PARAM_VERSION}"
    fi

    if [ "$LATEST" == "$PARAM_VERSION" ]; then
        echo "$(date +'%d %B %Y - %k:%M') - Tag: latest${PARAM_VERSION_CLASSIFIER} should be an alias of ${LATEST}, tag update is required"
        if [[ $PARAM_DRYRUN -eq 0 ]]; then
            echo "$(date +'%d %B %Y - %k:%M') - RUNNING): docker tag ${PARAM_ORG}/${PARAM_REPO}:${PARAM_VERSION} ${PARAM_ORG}/${PARAM_REPO}:latest${PARAM_VERSION_CLASSIFIER}"
            docker tag "${PARAM_ORG}"/"${PARAM_REPO}":"${PARAM_VERSION}" "${PARAM_ORG}"/"${PARAM_REPO}":latest"${PARAM_VERSION_CLASSIFIER}"
            echo "$(date +'%d %B %Y - %k:%M') - RUNNING: docker push ${PARAM_ORG}/${PARAM_REPO}:latest${PARAM_VERSION_CLASSIFIER}"        
            docker push "${PARAM_ORG}"/"${PARAM_REPO}":latest"${PARAM_VERSION_CLASSIFIER}"
        else
            echo "$(date +'%d %B %Y - %k:%M') - DRY-RUN (command not executed): docker tag ${PARAM_ORG}/${PARAM_REPO}:${PARAM_VERSION} ${PARAM_ORG}/${PARAM_REPO}:latest${PARAM_VERSION_CLASSIFIER}"
            echo "$(date +'%d %B %Y - %k:%M') - DRY-RUN (command not executed): docker push ${PARAM_ORG}/${PARAM_REPO}:latest${PARAM_VERSION_CLASSIFIER}"
        fi
    else
        echo "$(date +'%d %B %Y - %k:%M') - Tag: latest is an alias of ${LATEST}, unchanged"
    fi

    if [ "$MATCHING1" == "$PARAM_VERSION" ]; then
        echo "$(date +'%d %B %Y - %k:%M') - Tag: ${PARAM_VERSION_MAJOR}${PARAM_VERSION_CLASSIFIER} should be an alias of ${MATCHING1}, tag update is required"
        if [[ $PARAM_DRYRUN -eq 0 ]]; then
            echo "$(date +'%d %B %Y - %k:%M') - RUNNING): docker tag ${PARAM_ORG}/${PARAM_REPO}:${PARAM_VERSION} ${PARAM_ORG}/${PARAM_REPO}:${PARAM_VERSION_MAJOR}${PARAM_VERSION_CLASSIFIER}"
            docker tag "${PARAM_ORG}"/"${PARAM_REPO}":"${PARAM_VERSION}" "${PARAM_ORG}"/"${PARAM_REPO}":"${PARAM_VERSION_MAJOR}""${PARAM_VERSION_CLASSIFIER}"
            echo "$(date +'%d %B %Y - %k:%M') - RUNNING: docker push ${PARAM_ORG}/${PARAM_REPO}:${PARAM_VERSION_MAJOR}${PARAM_VERSION_CLASSIFIER}"        
            docker push "${PARAM_ORG}"/"${PARAM_REPO}":"${PARAM_VERSION_MAJOR}""${PARAM_VERSION_CLASSIFIER}"
        else
            echo "$(date +'%d %B %Y - %k:%M') - DRY-RUN (command not executed): docker tag ${PARAM_ORG}/${PARAM_REPO}:${PARAM_VERSION} ${PARAM_ORG}/${PARAM_REPO}:${PARAM_VERSION_MAJOR}${PARAM_VERSION_CLASSIFIER}"
            echo "$(date +'%d %B %Y - %k:%M') - DRY-RUN (command not executed): docker push ${PARAM_ORG}/${PARAM_REPO}:${PARAM_VERSION_MAJOR}${PARAM_VERSION_CLASSIFIER}"
        fi      
    else
        echo "$(date +'%d %B %Y - %k:%M') - Tag: ${PARAM_VERSION_MAJOR}${PARAM_VERSION_CLASSIFIER} is an alias of ${MATCHING1}, unchanged"
    fi

    if [ "$MATCHING2" == "$PARAM_VERSION" ]; then
        echo "$(date +'%d %B %Y - %k:%M') - Tag: ${PARAM_VERSION_MAJOR}.${PARAM_VERSION_MINOR}${PARAM_VERSION_CLASSIFIER} should be  an alias of ${MATCHING2}, tag update is required"
        if [[ $PARAM_DRYRUN -eq 0 ]]; then
            echo "$(date +'%d %B %Y - %k:%M') - RUNNING): docker tag ${PARAM_ORG}/${PARAM_REPO}:${PARAM_VERSION} ${PARAM_ORG}/${PARAM_REPO}:${PARAM_VERSION_MAJOR}.${PARAM_VERSION_MINOR}${PARAM_VERSION_CLASSIFIER}"
            docker tag "${PARAM_ORG}"/"${PARAM_REPO}":"${PARAM_VERSION}" "${PARAM_ORG}"/"${PARAM_REPO}":"${PARAM_VERSION_MAJOR}"."${PARAM_VERSION_MINOR}""${PARAM_VERSION_CLASSIFIER}"
            echo "$(date +'%d %B %Y - %k:%M') - RUNNING: docker push ${PARAM_ORG}/${PARAM_REPO}:${PARAM_VERSION_MAJOR}.${PARAM_VERSION_MINOR}${PARAM_VERSION_CLASSIFIER}"        
            docker push "${PARAM_ORG}"/"${PARAM_REPO}":"${PARAM_VERSION_MAJOR}"."${PARAM_VERSION_MINOR}""${PARAM_VERSION_CLASSIFIER}"
        else
            echo "$(date +'%d %B %Y - %k:%M') - DRY-RUN (command not executed): docker tag ${PARAM_ORG}/${PARAM_REPO}:${PARAM_VERSION} ${PARAM_ORG}/${PARAM_REPO}:${PARAM_VERSION_MAJOR}.${PARAM_VERSION_MINOR}${PARAM_VERSION_CLASSIFIER}"
            echo "$(date +'%d %B %Y - %k:%M') - DRY-RUN (command not executed): docker push ${PARAM_ORG}/${PARAM_REPO}:${PARAM_VERSION_MAJOR}.${PARAM_VERSION_MINOR}${PARAM_VERSION_CLASSIFIER}"
        fi          
    else
        echo "$(date +'%d %B %Y - %k:%M') - Tag: ${PARAM_VERSION_MAJOR}.${PARAM_VERSION_MINOR}${PARAM_VERSION_CLASSIFIER} is an alias of ${MATCHING2}, unchanged"
    fi

    if [ "$MATCHING3" == "$PARAM_VERSION" ]; then
        echo "$(date +'%d %B %Y - %k:%M') - Tag: ${PARAM_VERSION_MAJOR}.${PARAM_VERSION_MINOR}.${PARAM_VERSION_HF}${PARAM_VERSION_CLASSIFIER} should be  an alias of ${MATCHING3}, tag update is required"
        if [[ $PARAM_DRYRUN -eq 0 ]]; then
            echo "$(date +'%d %B %Y - %k:%M') - RUNNING): docker tag ${PARAM_ORG}/${PARAM_REPO}:${PARAM_VERSION} ${PARAM_ORG}/${PARAM_REPO}:${PARAM_VERSION_MAJOR}.${PARAM_VERSION_MINOR}.${PARAM_VERSION_HF}${PARAM_VERSION_CLASSIFIER}"
            docker tag "${PARAM_ORG}"/"${PARAM_REPO}":"${PARAM_VERSION}" "${PARAM_ORG}"/"${PARAM_REPO}":"${PARAM_VERSION_MAJOR}"."${PARAM_VERSION_MINOR}"."${PARAM_VERSION_HF}""${PARAM_VERSION_CLASSIFIER}"
            echo "$(date +'%d %B %Y - %k:%M') - RUNNING: docker push ${PARAM_ORG}/${PARAM_REPO}:${PARAM_VERSION_MAJOR}.${PARAM_VERSION_MINOR}.${PARAM_VERSION_HF}${PARAM_VERSION_CLASSIFIER}"        
            docker push "${PARAM_ORG}"/"${PARAM_REPO}":"${PARAM_VERSION_MAJOR}"."${PARAM_VERSION_MINOR}"."${PARAM_VERSION_HF}""${PARAM_VERSION_CLASSIFIER}"
        else
            echo "$(date +'%d %B %Y - %k:%M') - DRY-RUN (command not executed): docker tag ${PARAM_ORG}/${PARAM_REPO}:${PARAM_VERSION} ${PARAM_ORG}/${PARAM_REPO}:${PARAM_VERSION_MAJOR}.${PARAM_VERSION_MINOR}.${PARAM_VERSION_HF}${PARAM_VERSION_CLASSIFIER}"
            echo "$(date +'%d %B %Y - %k:%M') - DRY-RUN (command not executed): docker push ${PARAM_ORG}/${PARAM_REPO}:${PARAM_VERSION_MAJOR}.${PARAM_VERSION_MINOR}.${PARAM_VERSION_HF}${PARAM_VERSION_CLASSIFIER}"
        fi           
    else
        echo "$(date +'%d %B %Y - %k:%M') - Tag: ${PARAM_VERSION_MAJOR}.${PARAM_VERSION_MINOR}.${PARAM_VERSION_HF}${PARAM_VERSION_CLASSIFIER} is an alias of ${MATCHING3}, unchanged"
    fi    
}

Main() {
    echo "$(date +'%d %B %Y - %k:%M') - Received tagging request for: ${PARAM_ORG}/${PARAM_REPO}:${PARAM_VERSION}"
    Setup
    GetToken
    GetVersions
    DockerTags    
}

Main
