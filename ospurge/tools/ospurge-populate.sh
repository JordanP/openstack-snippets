#!/usr/bin/env bash

# This script populates the project set in the environment variable
# OS_PROJECT_NAME with various resources. The purpose is to test
# ospurge.

# Be strict
set -ueo pipefail

function exit_on_failure {
    RET_CODE=$?
    ERR_MSG=$1
    if [ $RET_CODE -ne 0 ]; then
        echo $ERR_MSG
        exit 1
    fi
}

function exit_if_empty {
    STRING=${1:-}
    ERR_MSG=${2:-}
    if [ -z "$STRING" ]; then
        echo $ERR_MSG
        exit 1
    fi
}

function cleanup {
    if [[ -f zero_disk.raw ]]; then
        rm zero_disk.raw
    fi

}
# Check if needed environment variable OS_PROJECT_NAME is set and non-empty.
: "${OS_PROJECT_NAME:?Need to set OS_PROJECT_NAME non-empty}"

# Some random UUID
UUID=$(cat /proc/sys/kernel/random/uuid)
# Name of external network
EXTNET_NAME=${EXTNET_NAME:-public}
# Name of flavor used to spawn a VM
FLAVOR=${FLAVOR:-m1.nano}
# Image used for the VM
VMIMG_NAME=${VMIMG_NAME:-cirros-0.3.4-x86_64-uec}



################################
### Check resources exist
### Do that early to fail early
################################
# Retrieve external network ID
EXTNET_ID=$(neutron net-show $EXTNET_NAME | awk '/ id /{print $4}')
exit_if_empty "$EXTNET_ID" "Unable to retrieve ID of external network $EXTNET_NAME"

exit_if_empty "$(nova flavor-list | grep $FLAVOR)" "Flavor $FLAVOR is unknown to Nova"

# Look for the $VMIMG_NAME image and get its ID
IMAGE_ID=$(glance image-list | awk "/ $VMIMG_NAME /{print \$2}")
exit_if_empty "$IMAGE_ID" "Image $VMIMG_NAME could not be found"

# Create a file that will be used to populate Glance and Swift
dd if="/dev/zero" of="zero_disk.raw" bs=1M count=5
trap cleanup SIGHUP SIGINT SIGTERM EXIT



###############################
### Neutron
###############################
# Create a private network and check it exists
neutron net-create $UUID
exit_on_failure "Creation of network $UUID failed"

# Get the private network ID
NET_ID=$(neutron net-show $UUID | awk '/ id /{print $4}')
exit_if_empty "$NET_ID" "Unable to retrieve ID of network $UUID"

# Add network's subnet
neutron subnet-create --name $UUID $NET_ID 192.168.0.0/24
exit_on_failure "Unable to create subnet $UUID for network $NET_ID"

# Create an unused port
neutron port-create $NET_ID

# Retrieve the subnet ID
SUBNET_ID=$(neutron subnet-show $UUID | awk '/ id /{print $4}')
exit_if_empty "$SUBNET_ID" "Unable to retrieve ID of subnet $UUID"

# Create a router
neutron router-create $UUID
exit_on_failure "Unable to create router $UUID"

# Retrieve the router ID
ROUT_ID=$(neutron router-show $UUID | awk '/ id /{print $4}')
exit_if_empty "$ROUT_ID" "Unable to retrieve ID of router $UUID"

# Set router's gateway
neutron router-gateway-set $ROUT_ID $EXTNET_ID
exit_on_failure "Unable to set gateway to router $UUID"

# Connect router on internal network
neutron router-interface-add $ROUT_ID $SUBNET_ID
exit_on_failure "Unable to add interface on subnet $UUID to router $UUID"

# Create a floating IP and retrieve its IP Address
FIP_ADD=$(neutron floatingip-create $EXTNET_NAME | awk '/ floating_ip_address /{print $4}')
exit_if_empty "$FIP_ADD" "Unable to create or retrieve floating IP"

# Create a security group
neutron security-group-create $UUID
exit_on_failure "Unable to create security group $UUID"

# Get security group ID
SECGRP_ID=$(neutron security-group-show $UUID | awk '/ id /{print $4}')
exit_if_empty "$SECGRP_ID" "Unable to retrieve ID of security group $UUID"

# Add a rule to previously created security group
neutron security-group-rule-create --direction ingress --protocol TCP \
--port-range-min 22 --port-range-max 22 --remote-ip-prefix 0.0.0.0/0 \
$SECGRP_ID



###############################
### Cinder
###############################
# Create a volume
cinder create --display-name $UUID 1
exit_on_failure "Unable to create volume"

# Get volume ID
VOL_ID=$(cinder show $UUID | awk '/ id /{print $4}')
exit_if_empty "$VOL_ID" "Unable to retrieve ID of volume $UUID"

# Snapshot the volume (note that it has to be detached, unless using --force)
cinder snapshot-create --display-name $UUID $VOL_ID
exit_on_failure "Unable to snapshot volume $UUID"

# Backup volume
# Don't exit on failure as Cinder Backup is not available on all clouds
cinder backup-create --display-name $UUID $VOL_ID || true



###############################
### Nova
###############################
# Launch a VM
nova boot --flavor $FLAVOR --image $IMAGE_ID --nic net-id=$NET_ID $UUID
exit_on_failure "Unable to boot VM $UUID"

# Get the VM ID
VM_ID=$(nova show $UUID | awk '/ id /{print $4}')
exit_if_empty "$VM_ID" "Unable to retrieve ID of VM $UUID"



###############################
### Glance
###############################
# Upload glance image
glance image-create --name $UUID --disk-format raw \
--container-format bare --file zero_disk.raw
exit_on_failure "Unable to create Glance iamge $UUID"



###############################
### Swift
###############################
# Don't exit on failure as Swift is not available on all clouds
swift upload $UUID zero_disk.raw || true



###############################
### Link resources
###############################
# Associate floating IP
nova floating-ip-associate $VM_ID $FIP_ADD
exit_on_failure "Unable to associate floating IP $FIP_ADD to VM $VM_NAME"

# Wait for volume to be available
VOL_STATUS=$(cinder show $VOL_ID | awk '/ status /{print $4}')
while [ $VOL_STATUS != "available" ]; do
    echo "Status of volume $VOL_NAME is $VOL_STATUS. Waiting 1 sec"
    sleep 1
    VOL_STATUS=$(cinder show $VOL_ID | awk '/ status /{print $4}')
done

# Attach volume
# This must be done before instance snapshot otherwise we could run into
# ERROR (Conflict): Cannot 'attach_volume' while instance is in task_state
# image_pending_upload
nova volume-attach $VM_ID $VOL_ID
exit_on_failure "Unable to attach volume $VOL_ID to VM $VM_ID"
