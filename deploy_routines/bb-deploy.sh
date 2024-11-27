#!/usr/bin/env bash

# Ted Kozma
# script to be used as part of bolt task, deploying botbypasser services in DC
# The PT_myrelease variable is passed from the bolt task as a parameter.
# 2024

set -e

if [[ $EUID -ne 0 ]]; then
  declare -r pre_command='sudo '
else
  declare -r pre_command=''
fi
echo "[+] Disabling puppet agent"
$pre_command /opt/puppetlabs/bin/puppet agent --disable "deployment"

# for those services behind loadbalancer – unvip
if [[ $APPNAME = 'fingerprintapi' ]] || [[ $APPNAME = 'generator' ]]; then
  echo "[+] Appname is $APPNAME. Unvipping from loadbalancer"
  /usr/local/bin/unvip noemail longdrain
fi
echo "[+] Stopping the service"
$pre_command supervisorctl stop all;
sleep 1

APPNAME=$(echo $(hostname)|sed  's/^bb-//; s/[0-9]*$//')

TG=$(readlink -f /data/companyname/${APPNAME}/current)

if test -d "$TG"; then
  # speed up generating the node_modules by saving the folder from the previous build
  $pre_command mv ${TG}/node_modules /data/companyname/${APPNAME}/
  $pre_command rm -rf ${TG} /data/companyname/${APPNAME}/current
fi
# compute the latest version in case the PT_release var is not defined
latest_version=$($pre_command /usr/bin/gsutil ls  gs://botbypasser-deployment-artifacts | grep -v latest |tail -n1|/usr/bin/perl -lne 'print $1 if m/botbypasser-([^\/]+)\.tar\.gz/')

if [[ -n "$PT_myrelease" ]]; then
  RELEASENAME="botbypasser-${PT_myrelease}"
else
  RELEASENAME='botbypasser-latest'
fi

echo "[+] Parameter passed: ${PT_myrelease}"
echo "[+] Downloading gs://botbypasser-deployment-artifacts/${RELEASENAME}.tar.gz"
$pre_command /usr/bin/gsutil cp gs://botbypasser-deployment-artifacts/${RELEASENAME}.tar.gz /tmp/
echo "[+] Installing myrelease $RELEASENAME"
$pre_command mkdir /data/companyname/${APPNAME}/${RELEASENAME}
$pre_command tar xzf /tmp/${RELEASENAME}.tar.gz -C /data/companyname/${APPNAME}/${RELEASENAME}/
$pre_command test -d /data/companyname/${APPNAME}/node_modules && $pre_command mv /data/companyname/${APPNAME}/node_modules /data/companyname/${APPNAME}/${RELEASENAME}/
echo "[+] Symlinking /data/companyname/${APPNAME}/current to /data/companyname/${APPNAME}/${RELEASENAME}"
$pre_command ln -s /data/companyname/${APPNAME}/${RELEASENAME} /data/companyname/${APPNAME}/current
echo "[+] Chowing the new code in /data/companyname/${APPNAME}/${RELEASENAME}"
$pre_command chown -R bb:companyname /data/companyname/${APPNAME}/${RELEASENAME}/
echo "[+] Building modules in /data/companyname/${APPNAME}/${RELEASENAME}"
sudo -u bb -- bash -c "cd /data/companyname/${APPNAME}/current && /usr/bin/npm install --production"
echo "[+] Running gulp in /data/companyname/${APPNAME}/current"
sudo -u bb -- bash -c "cd /data/companyname/${APPNAME}/current && /usr/bin/gulp"
echo
echo "[+] Starting the service"
$pre_command supervisorctl start $APPNAME

if [[ $APPNAME = 'fingerprintapi' ]] || [[ $APPNAME = 'generator' ]]; then
  echo "[+] Appname is $APPNAME. Reenabling in loadbalancer"
  sleep 2
  /usr/local/bin/revip noemail
fi
echo "[+] Reenabling the puppet agent"
$pre_command /opt/puppetlabs/bin/puppet agent --enable
echo "[+] Done with the `hostname -f`"
exit 0
