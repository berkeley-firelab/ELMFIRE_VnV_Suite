# ------------------------------------------------------------------------------
# ELMFIRE VnV Suite image with an *embedded* ELMFIRE build at a chosen git ref.
# - You can still mount your local elmfire repo and rebuild inside the container.
# - Multiple ELMFIRE versions can live side-by-side under /opt/elmfire/<ref>.
# ------------------------------------------------------------------------------

# We start from the base that already contains compilers, MPI, GDAL, Python, etc.
FROM clauten/elmfire:latest AS builder

# ---- Build args to fetch & build a *specific* ELMFIRE version -----------------
# Override at build time:
#   docker build --build-arg GIT_REF=v2025.0717 ...
ARG GIT_URL=https://github.com/berkeley-firelab/elmfire.git
ARG GIT_REF=main

# Optional: install git for the builder stage (base image may have it already)
RUN apt-get update -y && apt-get install -y --no-install-recommends \
    git ca-certificates \
 && rm -rf /var/lib/apt/lists/*

# Fresh checkout at a precise ref (shallow clone keeps the image small)
RUN rm -rf /src/elmfire && \
    git clone --depth=1 --branch ${GIT_REF} ${GIT_URL} /src/elmfire

# Build ELMFIRE
WORKDIR /src/elmfire/build/linux
RUN ./make_gnu.sh

# Layout for installation (versioned)
# - bin/ : compiled executables
# - src/ : source for reference (optional but handy for debugging)
RUN mkdir -p /opt/elmfire/${GIT_REF} && \
    cp -r /src/elmfire/build/linux/bin /opt/elmfire/${GIT_REF}/ && \
    cp -r /src/elmfire /opt/elmfire/${GIT_REF}/src

# ------------------------------------------------------------------------------
# Final image
# ------------------------------------------------------------------------------
FROM clauten/elmfire:latest

# Add (optional) TeX install for report compilation by toggling build arg
ARG INSTALL_TEX=no
RUN if [ "$INSTALL_TEX" = "yes" ]; then \
      apt-get update -y && apt-get install -y --no-install-recommends \
        texlive-latex-recommended texlive-latex-extra \
        texlive-fonts-recommended latexmk ghostscript && \
      rm -rf /var/lib/apt/lists/* ; \
    fi

# Copy the baked ELMFIRE version from builder stage
ARG GIT_REF=main
COPY --from=builder /opt/elmfire/${GIT_REF} /opt/elmfire/${GIT_REF}

# Symlink "current" to this baked version (you can switch later)
RUN ln -s /opt/elmfire/${GIT_REF} /opt/elmfire/current

# --- Workspace: bring the VnV Suite into the image (you can still mount over it)
WORKDIR /workspace/ELMFIRE_VnV_Suite
COPY requirements.txt .
RUN python3 -m pip install --upgrade pip && \
    python3 -m pip install --no-cache-dir -r requirements.txt

COPY . /workspace/ELMFIRE_VnV_Suite

# --- Helper scripts to switch ELMFIRE versions at runtime
# COPY scripts/switch-elmfire.sh /usr/local/bin/switch-elmfire.sh
# COPY scripts/elmfire-version /usr/local/bin/elmfire-version
# RUN chmod +x /usr/local/bin/switch-elmfire.sh /usr/local/bin/elmfire-version

# --- Default envs
ENV ELMFIRE_HOME=/opt/elmfire/current \
    ELMFIRE_BIN=/opt/elmfire/current/bin/elmfire \
    ELMFIRE_INSTALL_DIR=/opt/elmfire/current/bin \
    ELMFIRE_SCRATCH_BASE=/scratch/elmfire \
    PATH=$PATH:/opt/elmfire/current/bin

# Print helpful info when the container starts
COPY scripts/docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh
ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["/bin/bash"]
