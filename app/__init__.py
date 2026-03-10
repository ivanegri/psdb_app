from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_mail import Mail
from flask_migrate import Migrate
from config import config

db = SQLAlchemy()
login_manager = LoginManager()
mail = Mail()
migrate = Migrate()


def create_app(config_name='default'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # Inicializa extensões
    db.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)
    migrate.init_app(app, db)

    # Configuração do login
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Por favor, faça login para acessar esta página.'
    login_manager.login_message_category = 'warning'

    @app.context_processor
    def inject_conf():
        return dict()

    # Importa modelos para que o Alembic os detecte
    from app import models  # noqa: F401

    # Registra Blueprints
    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    from app.dashboard import bp as dashboard_bp
    app.register_blueprint(dashboard_bp)

    from app.eleitores import bp as eleitores_bp
    app.register_blueprint(eleitores_bp, url_prefix='/eleitores')

    from app.territorio import bp as territorio_bp
    app.register_blueprint(territorio_bp, url_prefix='/territorio')

    from app.comunicacao import bp as comunicacao_bp
    app.register_blueprint(comunicacao_bp, url_prefix='/comunicacao')

    from app.agenda import bp as agenda_bp
    app.register_blueprint(agenda_bp, url_prefix='/agenda')

    from app.acoes import bp as acoes_bp
    app.register_blueprint(acoes_bp, url_prefix='/acoes')

    from app.admin import bp as admin_bp
    app.register_blueprint(admin_bp, url_prefix='/admin')

    from app.portal import bp as portal_bp
    app.register_blueprint(portal_bp, url_prefix='/portal')

    @app.before_request
    def check_restricoes_eleitor():
        from flask_login import current_user
        from flask import request, redirect, url_for, flash
        if current_user.is_authenticated and current_user.is_eleitor():
            allowed = ['agenda.index', 'agenda.api_eventos', 'agenda.detalhe', 'agenda.confirmar_presenca', 'auth.logout', 'auth.perfil', 'static']
            if request.endpoint and request.endpoint not in allowed and not request.endpoint.startswith('portal.'):
                # Redirect to the new portal
                flash('Acesso restrito. Você foi redirecionado para o seu Portal do Eleitor.', 'warning')
                return redirect(url_for('portal.index'))

    return app
