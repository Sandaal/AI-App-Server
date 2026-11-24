# Your apps on top of the AI App Server image. AIAPP_IMAGE is the server image
# you build from the repository (docker build -t aiapp-server .) and push to
# your registry, e.g. myregistry.azurecr.io/aiapp-server:1.0.0.
ARG AIAPP_IMAGE=aiapp-server:latest
FROM ${AIAPP_IMAGE}
COPY --chown=10001:10001 apps/ /apps/
