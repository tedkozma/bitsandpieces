#!/usr/bin/env bash

#set -e

if [[ $EUID -ne 0 ]]; then
  declare -r pre_command='sudo '
else
  declare -r pre_command=''
fi

echo "[+] Unvipping, stand by ..."
unvip noemail longdrain; 
$pre_command supervisorctl stop all; 
sleep 2
$pre_command pkill -9 dotnet # because sometimes it doesn't
TG=$(readlink  -f /data/companyname/api/current)
$pre_command rm -rf ${TG} /data/companyname/api/current 
$pre_command rm -rf /tmp/latest.tar.gz /tmp/contentstack*.tar.gz

if [[ -n "$PT_myrelease" ]]; then
  RELEASENAME="contentstack-${PT_myrelease}"
else 
  RELEASENAME='latest'
fi

echo "Parameter passed: ${PT_myrelease}"
echo "Installing myrelease $RELEASENAME"

$pre_command gsutil cp gs://efoe-scrapeapi-deployment-artifacts/${RELEASENAME}.tar.gz /tmp/

$pre_command mkdir /data/companyname/api/${RELEASENAME}
$pre_command tar xzf /tmp/${RELEASENAME}.tar.gz -C /data/companyname/api/${RELEASENAME}/
$pre_command ln -s /data/companyname/api/${RELEASENAME} /data/companyname/api/current
$pre_command chown -R api:companyname  /data/companyname/api/${RELEASENAME}/

$pre_command supervisorctl start api vnc
while :; do
  ST=$(curl  -s -o /dev/null -w "%{http_code}"  http://localhost:5000/health/readiness)
  if [[ $ST -eq 200 ]]; then
    echo "[+] readiness check passed, moving on"
    break
  else
    echo "[-] readiness check not passing yet"
    sleep 1
  fi
done
revip noemail; 
$pre_command supervisorctl start check_scrape
exit 0
