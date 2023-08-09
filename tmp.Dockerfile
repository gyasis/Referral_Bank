# Use a multi-stage build to pull the repository and then set up the environment
FROM python:3.8-slim-buster as builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install git and necessary build tools
RUN apt-get update && apt-get install -y git build-essential apt-utils gcc libpq-dev python3-dev

# Clone the repository
ARG GIT_REPO
RUN git clone $GIT_REPO /src

# Use another stage to install Python dependencies and set up the app
FROM python:3.8-slim-buster

WORKDIR /src

# Copy content from the builder stage
COPY --from=builder /src /src

# Install necessary build tools for C extensions
RUN apt-get update && apt-get install -y build-essential gcc libpq-dev python3-dev

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 5005
