FROM node:22-bookworm

# Install system dependencies
RUN apt-get update && apt-get install -y \
  git \
  curl \
  jq \
  && rm -rf /var/lib/apt/lists/*

# Install GitHub CLI
RUN curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg \
  | dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg \
  && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
  | tee /etc/apt/sources.list.d/github-cli.list > /dev/null \
  && apt-get update && apt-get install -y gh \
  && rm -rf /var/lib/apt/lists/*

# Python toolchain for this project. This is a Python codebase;
# the Node base image only carries the Sandcastle/Codex harness.
# uv manages the project's dependencies and provisions its own managed
# Python 3.14 (bookworm only ships 3.11), so `uv sync` / `uv run pytest`
# work in a clean container. Installed into /usr/local/bin for all users.
RUN curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR=/usr/local/bin sh

# Build-args for UID/GID alignment: sandcastle docker build-image
# defaults these to the host user's UID/GID so image-built files
# and bind-mounted files share an owner without runtime chown.
ARG AGENT_UID=1000
ARG AGENT_GID=1000

# Rename the base image's "node" user to "agent" and align UID/GID.
RUN groupmod -o -g $AGENT_GID node && usermod -o -u $AGENT_UID -g $AGENT_GID -d /home/agent -m -l agent node

# Install Codex CLI (run as root before USER agent)
RUN npm install -g @openai/codex

USER ${AGENT_UID}:${AGENT_GID}

WORKDIR /home/agent

# Install Claude Code CLI as the agent user so it lands in the agent's
# ~/.local/bin (installing as root would put it in /root, invisible to agent).
# Add that dir to PATH so `claude` resolves for the merge-phase agent.
ENV PATH="/home/agent/.local/bin:${PATH}"
RUN curl -fsSL https://claude.ai/install.sh | bash

# Pre-provision uv's managed CPython 3.14 into the image (matches pyproject's
# requires-python >=3.14). The per-sandbox `uv sync` hook in main.mts otherwise
# re-downloads and unpacks the interpreter on every container start. Baked here,
# it lands in the agent's ~/.local/share/uv/python and is shared across all
# sandboxes, so `uv sync` finds it ready and only needs to link the .venv.
RUN uv python install 3.14

# In worktree sandbox mode, Sandcastle bind-mounts the git worktree at /home/agent/workspace
# and overrides the working directory to /home/agent/workspace at container start.
# Structure your Dockerfile so that /home/agent/workspace can serve as the project root.
ENTRYPOINT ["sleep", "infinity"]
