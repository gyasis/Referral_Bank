FROM python:3.8-slim-buster as builder

# Install git
RUN apt-get update && apt-get install -y git

# Clone the repository
ARG GIT_REPO
RUN git clone $GIT_REPO /app

# Use another stage to install Python dependencies and set up the app
FROM python:3.8-slim-buster

WORKDIR /app

COPY --from=builder /app /app

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 5005
