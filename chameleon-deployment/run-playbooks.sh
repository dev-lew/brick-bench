#!/bin/sh

usage=$(cat <<EOF
run-playbooks.sh [-g] [-t HUGGINGFACE_TOKEN] (optional)

-g: Enable support for GPU inference (disabled by default).

-t: Provide a Hugging Face token if you want the brick-bench
playbook to download models directly onto the host. If not
set, you will have to copy them yourself.
EOF
     )

while getopts gt: optarg; do
    case "${optarg}" in
        g) use_gpu=true
           ;;
        t) token="${OPTARG}"
           ;;
        *) echo "${usage}"; exit 1
    esac
done

VENV_PATH=".venv"

if ! . "${VENV_PATH}/bin/activate"; then
    echo "Failed to source virtualenv. Is VENV_PATH set correctly?"
    exit 1
fi

printf "Setting ansible enviroment variables... "
export ANSIBLE_CONFIG="ansible/ansible.cfg"
export ANSIBLE_HOME="${VENV_PATH}"
echo "done"

ansible-galaxy install -r ansible/deps/requirements.yaml

echo "Running ansible-playbooks"

ansible-playbook ansible/kubernetes.yaml

extra_vars=""
skip_tags=""

if [ "${use_gpu}" = true ]; then
    extra_vars="${extra_vars} image_gen_manifest=image-gen-gpu.yaml"
else
    extra_vars="${extra_vars} image_gen_manifest=image-gen-cpu.yaml"
    skip_tags="${skip_tags}gpu,"
fi

if [ -n "${token}" ]; then
    extra_vars="${extra_vars} token=${token}"
fi

ansible-playbook ansible/brick-bench.yaml --extra-vars "${extra_vars}" --skip-tags="${skip_tags}"
