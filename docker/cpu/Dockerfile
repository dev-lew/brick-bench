# syntax=docker/dockerfile:1

FROM pytorch/pytorch:2.6.0-cuda12.6-cudnn9-runtime

RUN <<EOF
    apt update
    apt install -y git
    apt clean
EOF

ENV PIP_PREFER_BINARY=1 ROOT=/stable-diffusion

RUN --mount=type=cache,target=/root/.cache/pip <<EOF
    git clone https://github.com/comfyanonymous/ComfyUI.git ${ROOT}
    cd ${ROOT}
    git checkout v0.3.27
    pip install -r requirements.txt
EOF

WORKDIR ${ROOT}

ENV PYTHONPATH="${PYTHONPATH}:${PWD}"

EXPOSE 8000

ENTRYPOINT ["python3", "-u", "main.py", "--listen", "--port", "8000", "--cpu"]
