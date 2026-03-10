#!/bin/sh
set -e

echo "🔧 Ajustando permissões..."
# Garante que psdbuser pode escrever nas pastas que o Alembic precisa
# (necessário porque o volume .:/app sobrescreve o chown do Dockerfile)
chown -R psdbuser:psdb /app/migrations 2>/dev/null || true
chown -R psdbuser:psdb /app/migrations/versions 2>/dev/null || true

echo "🗄️  Inicializando banco de dados..."

# Se a pasta migrations não existir ou estiver vazia, inicializa
if [ ! -f /app/migrations/env.py ]; then
    echo "  → Criando pasta migrations (primeiro uso)..."
    su -s /bin/sh psdbuser -c "flask --app run.py db init"
fi

# Gera nova migration se houver alterações nos modelos (ignora se não houver mudanças)
echo "  → Verificando alterações nos modelos..."
su -s /bin/sh psdbuser -c "flask --app run.py db migrate -m 'auto' 2>&1 || true"

# Aplica todas as migrations pendentes
echo "  → Aplicando migrations no banco..."
su -s /bin/sh psdbuser -c "flask --app run.py db upgrade"

echo "🌱 Rodando seed..."
su -s /bin/sh psdbuser -c "python seed.py"

echo "🚀 Iniciando Gunicorn..."
exec su -s /bin/sh psdbuser -c \
    "gunicorn --bind 0.0.0.0:5000 --workers 4 --timeout 120 'run:app'"
