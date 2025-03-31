#!/bin/sh

usage=$(cat <<EOF
quick-ssh.sh <hostname> <keyfile>

Where hostname is one of: controller, worker.
Keyfile is the path to the ssh private
key for the instances.
EOF
     )

if [ -z "${1}" ]; then
    echo "${0}: You must provide a hostname."
    echo "${usage}"
    exit 1
fi

if [ -z "${2}" ]; then
    echo "${0}: You must provide a keyfile."
    echo "${usage}"
    exit 1
fi

if [ "${1}" != "controller" ] && [ "${1}" != "worker" ]; then
    echo "${0}: hostname is not one of: controller, worker."
    echo "${usage}"
    exit 1
fi

HOSTFILE="../ansible/inventory/hosts"

if [ "${1}" = "controller" ]; then
    hostname=$(sed -n "/^\[controller\]/{n; p}" "${HOSTFILE}")
else
    hostname=$(sed -n "/^\[worker\]/{n; p}" "${HOSTFILE}")
fi

ssh -o StrictHostKeyChecking=no -i "${2}" "cc@${hostname}"

