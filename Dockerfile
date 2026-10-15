FROM python:3.11-slim

# Define o diretório de trabalho dentro do container
WORKDIR /app

# Instala o curl (necessário para o healthcheck nativo do Docker)
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Copia o arquivo de dependências e instala
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia todo o código do projeto para o container
COPY . .

# Expõe a porta que o FastAPI vai utilizar
EXPOSE 8000

# Comando para iniciar a aplicação mapeando do diretório src
CMD ["uvicorn", "src.presentation.api.main:app", "--host", "0.0.0.0", "--port", "8000"]