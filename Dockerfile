FROM python:3.14-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    borgbackup \
    borgmatic \
    openssh-client \
    wget \
    && rm -rf /var/lib/apt/lists/*

# create virtual environment outside /app so volume mounts don't overwrite it
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# upgrade pip
RUN pip install --no-cache-dir --upgrade pip

# copy project metadata and source code
COPY pyproject.toml README.md /app/
COPY src /app/src

# install package in editable mode
RUN pip install --no-cache-dir -e .

CMD ["bash"]
