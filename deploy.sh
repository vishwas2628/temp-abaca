#!/bin/bash

gitLastCommit=$(git log -1 HEAD --pretty=format:%s)
gitRevision=$(git rev-parse --short HEAD 2> /dev/null | sed "s/\(.*\)/@\1/")
buildDescription=$gitLastCommit$gitRevision

ENVIRONMENT=$1
# Theses where the initial environemnts setup by pixelmatters
AVAILABLE_ENVIRONMENTS=("production" "staging" "development")

if [[ ! " ${AVAILABLE_ENVIRONMENTS[@]} " =~ " ${ENVIRONMENT} " ]]; then
  echo "Invalid environment"
  exit
fi

# Decide DIVIO environment based on the environment
if [[ $ENVIRONMENT == "production" ]]; then
  DIVIO_ENVIRONMENT="5dder6dmmjaojm6yykrrjkbi3u"
  TARGET_BRANCH="master"
  REPO="viral-577"
elif [[ $ENVIRONMENT == "staging" ]]; then
  DIVIO_ENVIRONMENT="ryi7qrrfa5abvlwa4og6cjonzq"
  TARGET_BRANCH="staging"
  REPO="viral-577"
elif [[ $ENVIRONMENT == "development" ]]; then
  DIVIO_ENVIRONMENT="wcclxsteovegdduedgy6ytp4vi"
  TARGET_BRANCH="develop"
  REPO="viral-577"
fi


# Init and setup a new repository
echo "Creating a new empty repository"
git init
git branch -m main
git remote add origin git@git.divio.com:"${REPO}".git

# Configure local repro name and SSH known hosts
git config user.email "akash.kumar@vilcap.com"
git config user.name "Akash Kumar Verma"

# Commit all changes
echo "Commiting all changes"
git add .
git commit -am "VIRAL API build from: $buildDescription"

# Push changes to DIVIO
git push origin main:$TARGET_BRANCH --force --prune

# Remove temporary reposition
echo "Cleaning up..."
rm -rf .git/


curl --location --request POST 'https://api.divio.com/apps/v3/deployments/' \
--header 'Content-Type: application/json' \
--header "Authorization: Token $DIVIO_TOKEN" \
--header 'Accept: */*' \
--header 'Host: api.divio.com' \
--header 'Connection: keep-alive' \
--data-raw "{\"environment\": \"$DIVIO_ENVIRONMENT\"}"


echo "Done 👌"
