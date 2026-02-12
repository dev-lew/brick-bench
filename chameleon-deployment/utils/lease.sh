#!/bin/sh

usage=$(
    cat <<EOF
lease.sh <lease-name> [-g] (optional)

-g
    Reserve a node with gpu. Defaults to 2 cpu nodes.
EOF
)

lease_name=$1

if [ -z "${lease_name}" ]; then
    echo "You must provide a lease name"
    echo "${usage}"
    exit 1
fi

while getopts g: optarg; do
    case "${optarg}" in
    g)
        use_gpu=true
        ;;
    *)
        echo "${usage}"
        exit 1
        ;;
    esac
done

END_DATE="$(date --date '+7 days' '+%F %H:%M')"

if [ "${use_gpu}" = true ]; then
    uv run openstack reservation lease create \
        --reservation min=1,max=1,resource_type=physical:host,resource_properties='["=", "$node_type", "compute_cascadelake_r"]' \
        --end-date "${END_DATE}" "${lease_name}-cpu"

    uv run openstack reservation lease create \
        --reservation min=1,max=1,resource_type=physical:host,resource_properties='["=", "$node_type", "gpu_rtx_6000"]' \
        --end-date "${END_DATE}" "${lease_name}-gpu"
else
    uv run openstack reservation lease create \
        --reservation min=2,max=2,resource_type=physical:host,resource_properties='["=", "$node_type", "compute_cascadelake_r"]' \
        --end-date "${END_DATE}" "${lease_name}-cpu"
fi
