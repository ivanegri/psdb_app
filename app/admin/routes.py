from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from functools import wraps
from app.admin import bp
from app.models import User, ConfiguracaoSistema, Eleitor, Comunicacao, db
from werkzeug.security import generate_password_hash


def admin_required(f):
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if not current_user.is_admin():
            flash('Acesso restrito a administradores.', 'danger')
            return redirect(url_for('dashboard.index'))
        return f(*args, **kwargs)
    return decorated


@bp.route('/')
@admin_required
def index():
    stats = {
        'usuarios': User.query.count(),
        'eleitores': Eleitor.query.count(),
        'comunicacoes': Comunicacao.query.count(),
    }
    return render_template('admin/index.html', stats=stats)


# ── Usuários ──────────────────────────────────────────────────────────────────

@bp.route('/usuarios')
@admin_required
def usuarios():
    users = User.query.order_by(User.nome).all()
    return render_template('admin/usuarios.html', users=users)


@bp.route('/usuarios/novo', methods=['GET', 'POST'])
@admin_required
def novo_usuario():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        if User.query.filter_by(email=email).first():
            flash('E-mail já cadastrado.', 'danger')
            return redirect(url_for('admin.novo_usuario'))
        user = User(
            nome=request.form.get('nome', '').strip(),
            email=email,
            perfil=request.form.get('perfil', 'eleitor'),
            ativo=True,
        )
        user.set_password(request.form.get('senha', ''))
        db.session.add(user)
        db.session.commit()
        flash(f'Usuário {user.nome} criado!', 'success')
        return redirect(url_for('admin.usuarios'))
    return render_template('admin/usuario_form.html', user=None)


@bp.route('/usuarios/<int:id>/editar', methods=['GET', 'POST'])
@admin_required
def editar_usuario(id):
    user = User.query.get_or_404(id)
    if request.method == 'POST':
        user.nome = request.form.get('nome', '').strip()
        user.perfil = request.form.get('perfil', user.perfil)
        user.ativo = request.form.get('ativo') == 'on'
        nova_senha = request.form.get('senha', '').strip()
        if nova_senha:
            user.set_password(nova_senha)
        db.session.commit()
        flash('Usuário atualizado!', 'success')
        return redirect(url_for('admin.usuarios'))
    return render_template('admin/usuario_form.html', user=user)


@bp.route('/usuarios/<int:id>/excluir', methods=['POST'])
@admin_required
def excluir_usuario(id):
    if id == current_user.id:
        flash('Você não pode excluir seu próprio usuário.', 'danger')
        return redirect(url_for('admin.usuarios'))
    user = User.query.get_or_404(id)
    db.session.delete(user)
    db.session.commit()
    flash('Usuário removido.', 'warning')
    return redirect(url_for('admin.usuarios'))



