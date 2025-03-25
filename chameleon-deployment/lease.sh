#!/bin/sh

lease_name=$1

if [ -z "${lease_name}" ]; then
    echo "You must provide a lease name"
    exit 1
fi

END_DATE="$(date --date '+7 days' '+%F %H:%M')"

openstack reservation lease create \
          --reservation min=1,max=1,resource_type=physical:host,resource_properties='["=", "$node_type", "compute_cascadelake_r"]' \
	  --end-date "${END_DATE}" "${lease_name}-cpu"

openstack reservation lease create \
          --reservation min=1,max=1,resource_type=physical:host,resource_properties='["=", "$node_type", "gpu_rtx_6000"]' \
	  --end-date "${END_DATE}" "${lease_name}-gpu"
