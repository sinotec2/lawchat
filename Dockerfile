FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    software-properties-common \
    git \
    bash \
    vim \
    && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/sinotec2/lawchat.git .

RUN pip3 install -r requirements.txt
EXPOSE 8501

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

ENTRYPOINT ["/usr/local/bin/streamlit/streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
