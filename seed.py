"""
Script de seed para popular o banco de dados inicial.
Uso: python seed.py
"""
import os
from app import create_app, db
from app.models import User, Bairro
from cryptography.fernet import Fernet

app = create_app(os.environ.get('FLASK_ENV', 'development'))


# Bairros de Jundiaí com coordenadas aproximadas
BAIRROS_JUNDIAI = [
    ('Centro', '001', -23.1857, -46.8974),
    ('Vila Arens', '001', -23.1815, -46.8890),
    ('Anhangabaú', '002', -23.1960, -46.9020),
    ('Jardim Tarumã', '002', -23.2010, -46.8940),
    ('Bairro Colônia', '003', -23.1760, -46.8810),
    ('Campos Elíseos', '003', -23.1900, -46.9100),
    ('Jardim Novo Horizonte', '004', -23.2100, -46.9050),
    ('Vila Rio Branco', '004', -23.1950, -46.8780),
    ('Eloy Chaves', '005', -23.1700, -46.8700),
    ('Jardim Paulista', '005', -23.2050, -46.9150),
    ('Medeiros', '006', -23.1650, -46.9200),
    ('Fazenda Grande', '006', -23.2150, -46.8850),
    ('Vila Progresso', '007', -23.1850, -46.8650),
    ('Bonfiglioli', '007', -23.1780, -46.9050),
    ('Ivoturucaia', '008', -23.2200, -46.9000),
    ('Jardim Tamoio', '008', -23.1920, -46.8580),
    ('Engordadouro', '009', -23.1730, -46.8850),
    ('Jardim Caxambu', '009', -23.2000, -46.8680),
    ('Retiro', '010', -23.1680, -46.9100),
    ('Vila Nova', '010', -23.1990, -46.9220),
    ('Botujuru', '011', -23.1550, -46.8780),
    ('Malota', '011', -23.2250, -46.8780),
    ('Anhumas', '012', -23.1610, -46.8940),
    ('Traviú', '012', -23.2300, -46.9100),
]


def seed():
    with app.app_context():
        print('🌱 Iniciando seed do banco de dados...')

        # Cria bairros
        bairros_adicionados = 0
        for nome, zona, lat, lng in BAIRROS_JUNDIAI:
            if not Bairro.query.filter_by(nome=nome).first():
                b = Bairro(nome=nome, zona_eleitoral=zona, latitude=lat, longitude=lng)
                db.session.add(b)
                bairros_adicionados += 1

        db.session.commit()
        print(f'✅ {bairros_adicionados} bairros criados (de {len(BAIRROS_JUNDIAI)} total).')

        # Cria usuário admin padrão
        admin_email = 'admin@psdb-jundiai.org.br'
        if not User.query.filter_by(email=admin_email).first():
            admin = User(
                nome='Administrador PSDB',
                email=admin_email,
                perfil='gestor',
                ativo=True,
            )
            admin.set_password('psdb@2026')
            db.session.add(admin)
            db.session.commit()
            print(f'✅ Usuário admin criado: {admin_email} / senha: psdb@2026')
            print('⚠️  TROQUE A SENHA IMEDIATAMENTE após o primeiro login!')
        else:
            print('ℹ️  Usuário admin já existe, pulando.')

        print('\n🎉 Seed concluído! Acesse: http://localhost:5000')
        print(f'   Login: {admin_email}')
        print('   Senha: psdb@2026')


if __name__ == '__main__':
    seed()
