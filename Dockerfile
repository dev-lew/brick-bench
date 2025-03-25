# syntax=docker/dockerfile:1

FROM pytorch/pytorch:2.6.0-cuda12.6-cudnn9-runtime

ENV DEBIAN_FRONTEND=noninteractive PIP_PREFER_BINARY=1

RUN <<EOF
    apt update
    apt install -y git
    apt clean
EOF

ENV ROOT=/stable-diffusion

RUN --mount=type=cache,target=/root/.cache/pip <<EOF
    git clone https://github.com/comfyanonymous/ComfyUI.git ${ROOT}
    cd ${ROOT}
    git checkout v0.3.27
    pip install -r requirements.txt
EOF

WORKDIR ${ROOT}
ENV NVIDIA_VISIBLE_DEVICES=all PYTHONPATH="${PYTHONPATH}:${PWD}"
EXPOSE 8000
ENTRYPOINT ["/docker/entrypoint.sh"]
CMD python3 -u main.py --listen --port 8000 ${CLI_ARGS}
