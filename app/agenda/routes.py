from datetime import datetime
from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app.agenda import bp
from app.models import Evento, Eleitor, db


TIPOS_EVENTO = [
    ('reuniao_base', '🏠 Reunião de Base'),
    ('visita_domiciliar', '🚪 Visita Domiciliar'),
    ('evento_publico', '🎤 Evento Público'),
    ('treinamento', '📚 Treinamento'),
    ('outro', '📌 Outro'),
]


@bp.route('/')
@login_required
def index():
    return render_template('agenda/index.html', tipos=TIPOS_EVENTO)


@bp.route('/api/eventos')
@login_required
def api_eventos():
    """Retorna todos os eventos no formato FullCalendar."""
    eventos = Evento.query.all()
    return jsonify([e.to_calendar_dict() for e in eventos])


@bp.route('/novo', methods=['GET', 'POST'])
@login_required
def novo():
    if current_user.is_eleitor():
        flash('Acesso negado. Apenas líderes e administradores podem criar eventos.', 'danger')
        return redirect(url_for('agenda.index'))

    if request.method == 'POST':
        data_inicio_str = request.form.get('data_inicio', '')
        data_fim_str = request.form.get('data_fim', '')
        try:
            data_inicio = datetime.fromisoformat(data_inicio_str)
            data_fim = datetime.fromisoformat(data_fim_str) if data_fim_str else None
        except ValueError:
            flash('Data inválida.', 'danger')
            return redirect(url_for('agenda.novo'))

        evento = Evento(
            titulo=request.form.get('titulo', '').strip(),
            tipo=request.form.get('tipo', 'outro'),
            descricao=request.form.get('descricao', '').strip() or None,
            local=request.form.get('local', '').strip() or None,
            data_inicio=data_inicio,
            data_fim=data_fim,
            cor=request.form.get('cor', '#005BB5'),
            criado_por_id=current_user.id,
        )
        db.session.add(evento)
        db.session.flush()

        # Participantes
        participante_ids = request.form.getlist('participantes')
        for pid in participante_ids:
            eleitor = Eleitor.query.get(int(pid))
            if eleitor:
                evento.participantes.append(eleitor)

        db.session.commit()
        flash(f'Evento "{evento.titulo}" criado com sucesso!', 'success')
        return redirect(url_for('agenda.index'))

    eleitores = Eleitor.query.order_by(Eleitor.nome).all()
    return render_template('agenda/form.html', evento=None, tipos=TIPOS_EVENTO, eleitores=eleitores)


@bp.route('/<int:id>')
@login_required
def detalhe(id):
    evento = Evento.query.get_or_404(id)
    eleitor_confirmou = False
    
    if current_user.is_eleitor():
        eleitor_vinculado = Eleitor.query.filter_by(email=current_user.email).first()
        if eleitor_vinculado and eleitor_vinculado in evento.participantes:
            eleitor_confirmou = True
            
    return render_template('agenda/detalhe.html', evento=evento, tipos=TIPOS_EVENTO, eleitor_confirmou=eleitor_confirmou)


@bp.route('/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def editar(id):
    if current_user.is_eleitor():
        flash('Acesso negado. Apenas líderes e administradores podem editar eventos.', 'danger')
        return redirect(url_for('agenda.detalhe', id=id))

    evento = Evento.query.get_or_404(id)
    if request.method == 'POST':
        data_inicio_str = request.form.get('data_inicio', '')
        data_fim_str = request.form.get('data_fim', '')
        try:
            evento.data_inicio = datetime.fromisoformat(data_inicio_str)
            evento.data_fim = datetime.fromisoformat(data_fim_str) if data_fim_str else None
        except ValueError:
            flash('Data inválida.', 'danger')
            return redirect(url_for('agenda.editar', id=id))

        evento.titulo = request.form.get('titulo', '').strip()
        evento.tipo = request.form.get('tipo', 'outro')
        evento.descricao = request.form.get('descricao', '').strip() or None
        evento.local = request.form.get('local', '').strip() or None
        evento.cor = request.form.get('cor', '#005BB5')

        # Atualiza participantes
        evento.participantes[:] = []
        for pid in request.form.getlist('participantes'):
            eleitor = Eleitor.query.get(int(pid))
            if eleitor:
                evento.participantes.append(eleitor)

        db.session.commit()
        flash('Evento atualizado!', 'success')
        return redirect(url_for('agenda.detalhe', id=evento.id))

    eleitores = Eleitor.query.order_by(Eleitor.nome).all()
    return render_template('agenda/form.html', evento=evento, tipos=TIPOS_EVENTO, eleitores=eleitores)


@bp.route('/<int:id>/excluir', methods=['POST'])
@login_required
def excluir(id):
    if current_user.is_eleitor():
        flash('Acesso negado.', 'danger')
        return redirect(url_for('agenda.index'))

    evento = Evento.query.get_or_404(id)
    db.session.delete(evento)
    db.session.commit()
    flash('Evento removido.', 'warning')
    return redirect(url_for('agenda.index'))


@bp.route('/<int:id>/confirmar', methods=['POST'])
@login_required
def confirmar_presenca(id):
    evento = Evento.query.get_or_404(id)
    
    # Try locking the 'User' to a registered 'Eleitor' using the user's email
    eleitor_vinculado = Eleitor.query.filter_by(email=current_user.email).first()
    
    if not eleitor_vinculado:
        flash('Não foi possível confirmar presença pois seu e-mail de usuário não está vinculado a um cadastro de eleitor.', 'warning')
        return redirect(url_for('agenda.detalhe', id=evento.id))

    if eleitor_vinculado in evento.participantes:
        evento.participantes.remove(eleitor_vinculado)
        flash('Você cancelou sua presença neste evento.', 'info')
    else:
        evento.participantes.append(eleitor_vinculado)
        flash('Presença confirmada no evento com sucesso!', 'success')
        
    db.session.commit()
    return redirect(url_for('agenda.detalhe', id=evento.id))
