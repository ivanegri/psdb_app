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
BAIRROS_JUNDIAI = []


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
