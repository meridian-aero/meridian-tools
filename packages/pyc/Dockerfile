FROM python:3.11-slim

# System dependencies for numpy/scipy (BLAS/LAPACK) and compiled extensions
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
        gfortran \
        git \
        libopenblas-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install pyCycle from upstream at a pinned ref.
# Override at build time: --build-arg PYC_REF=<commit|tag|branch>
ARG PYC_REF=main
RUN pip install --no-cache-dir "om-pycycle @ git+https://github.com/mdolab/pyCycle.git@${PYC_REF}"

# Copy SDK first (changes less often -> better layer caching)
COPY packages/sdk/ packages/sdk/
RUN pip install --no-cache-dir "packages/sdk[all]"

# Copy and install the PYC package (om-pycycle dep already satisfied)
COPY packages/pyc/ packages/pyc/
RUN pip install --no-cache-dir --no-deps packages/pyc

# Create non-root user for runtime with a writable home directory
RUN useradd -r -m -s /usr/sbin/nologin pyc && \
    mkdir -p /data && chown pyc:pyc /data

ENV HANGAR_DATA_DIR=/data
ENV MPLCONFIGDIR=/tmp/matplotlib
ENV PYC_TRANSPORT=stdio

VOLUME /data
EXPOSE 8000
USER pyc

CMD ["python", "-m", "hangar.pyc.server"]
