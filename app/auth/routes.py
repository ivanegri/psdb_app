from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from datetime import datetime
from app import db
from app.auth import bp
from app.models import User


@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        senha = request.form.get('senha', '')
        user = User.query.filter_by(email=email, ativo=True).first()
        if user and user.check_password(senha):
            login_user(user, remember=request.form.get('lembrar') == 'on')
            user.ultimo_login = datetime.utcnow()
            db.session.commit()
            next_page = request.args.get('next')
            flash(f'Bem-vindo, {user.nome}!', 'success')
            return redirect(next_page or url_for('dashboard.index'))
        flash('E-mail ou senha incorretos.', 'danger')
    return render_template('auth/login.html')


@bp.route('/primeiro-acesso', methods=['GET', 'POST'])
def primeiro_acesso():
    if current_user.is_authenticated:
        return redirect(url_for('portal.index') if current_user.is_eleitor() else url_for('dashboard.index'))
    
    if request.method == 'POST':
        cpf_input = request.form.get('cpf', '').strip()
        cpf_input = ''.join(filter(str.isdigit, cpf_input))
        email_input = request.form.get('email', '').strip().lower()
        senha_input = request.form.get('senha', '')

        if not cpf_input or not email_input or not senha_input:
            flash('Por favor, preencha todos os campos.', 'danger')
            return redirect(url_for('auth.primeiro_acesso'))

        if User.query.filter_by(email=email_input).first():
            flash('Este e-mail reservado já está em uso por outro usuário. Vá para o Login ou recupere a conta.', 'danger')
            return redirect(url_for('auth.primeiro_acesso'))

        # Fetch eleitores from Models
        from app.models import Eleitor
        
        eleitores = Eleitor.query.filter(Eleitor._cpf_criptografado.is_not(None)).all()
        eleitor_encontrado = None
        for e in eleitores:
            if e.cpf == cpf_input:
                eleitor_encontrado = e
                break
        
        if not eleitor_encontrado:
            flash('Seu CPF não foi encontrado nas listas de eleitores de nossa base. Por favor contate a liderança que preencheu sua ficha.', 'warning')
            return redirect(url_for('auth.primeiro_acesso'))
            
        # Register new User
        eleitor_encontrado.email = email_input
        new_user = User(nome=eleitor_encontrado.nome, email=email_input, perfil='eleitor')
        new_user.set_password(senha_input)
        db.session.add(new_user)
        db.session.commit()
        
        flash('Cadastro online ativado! Você já pode entrar com seu E-Mail e Senha.', 'success')
        return redirect(url_for('auth.login'))
        
    return render_template('auth/primeiro_acesso.html')


@bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Sessão encerrada com sucesso.', 'info')
    return redirect(url_for('auth.login'))


@bp.route('/perfil', methods=['GET', 'POST'])
@login_required
def perfil():
    if request.method == 'POST':
        current_user.nome = request.form.get('nome', current_user.nome).strip()
        nova_senha = request.form.get('nova_senha', '').strip()
        if nova_senha:
            if len(nova_senha) < 6:
                flash('A senha deve ter pelo menos 6 caracteres.', 'warning')
                return redirect(url_for('auth.perfil'))
            current_user.set_password(nova_senha)
        db.session.commit()
        flash('Perfil atualizado com sucesso!', 'success')
        return redirect(url_for('auth.perfil'))
    return render_template('auth/perfil.html')
