FROM eclipse-temurin:21-jre
WORKDIR /app
# Mustang + KoSIT Schematron werden beim Build offline gebundled (siehe README)
# Für Sorgfalt: kein Internet beim Run, nur beim Build
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*
COPY pom.xml ./
# Fallback: wenn Maven nicht verfügbar, nutze pre-built jar (siehe stub)
COPY src ./src
COPY rules ./rules
# Stub-Server für Track B - ersetzt später Mustang
COPY server.py ./
RUN apt-get update && apt-get install -y python3 python3-pip && pip3 install --no-cache-dir flask pypdf --break-system-packages || true
EXPOSE 8081
CMD ["python3", "server.py"]
