#!/bin/sh

usage=$(cat <<EOF
run-playbooks.sh [-t HUGGINGFACE_TOKEN] (optional)

Provide a Hugging Face token if you want the brick-bench
playbook to download models directly onto the host. If not
set, you will have to copy them yourself.
EOF
     )

while getopts t: optarg; do
    case "${optarg}" in
        t) token="${OPTARG}"
           ;;
        *) echo "${usage}"; exit 1
    esac
done

VENV_PATH="${HOME}/.virtualenvs/brick-bench"

if ! . "${VENV_PATH}/bin/activate"; then
    echo "Failed to source virtualenv. Is VENV_PATH set correctly?"
    exit 1
fi

printf "Setting ansible enviroment variables... "
export ANSIBLE_CONFIG="ansible/ansible.cfg"
export ANSIBLE_HOME="${VENV_PATH}"
echo "done"

ansible-galaxy install -r deps/requirements.yaml

echo "Running ansible-playbooks"

ansible-playbook ansible/kubernetes.yaml

if [ -n "${token}" ]; then
    ansible-playbook ansible/brick-bench.yaml --extra-vars "token=${token}"
else
    ansible-playbook ansible/brick-bench.yaml
fi
