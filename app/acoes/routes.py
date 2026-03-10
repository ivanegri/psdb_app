from datetime import datetime
from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.acoes import bp
from app.models import Acao, Eleitor, Evento, Bairro, db


TIPOS_ACAO = [
    ('visita', '🚪 Visita'),
    ('ligacao', '📞 Ligação'),
    ('email', '📧 E-mail'),
    ('whatsapp', '💬 WhatsApp'),
    ('evento', '📅 Evento'),
    ('material', '📄 Distribuição de Material'),
    ('outro', '📌 Outro'),
]


@bp.route('/')
@login_required
def index():
    page = request.args.get('page', 1, type=int)
    tipo = request.args.get('tipo', '')
    query = Acao.query
    if tipo:
        query = query.filter_by(tipo=tipo)
    acoes = query.order_by(Acao.data.desc()).paginate(page=page, per_page=30, error_out=False)
    return render_template('acoes/index.html', acoes=acoes, tipos=TIPOS_ACAO, filtro_tipo=tipo)


@bp.route('/nova', methods=['GET', 'POST'])
@login_required
def nova():
    if request.method == 'POST':
        acao = Acao(
            tipo=request.form.get('tipo', 'outro'),
            descricao=request.form.get('descricao', '').strip() or None,
            resultado=request.form.get('resultado', '').strip() or None,
            data=datetime.utcnow(),
            eleitor_id=request.form.get('eleitor_id', type=int) or None,
            evento_id=request.form.get('evento_id', type=int) or None,
            bairro_id=request.form.get('bairro_id', type=int) or None,
            responsavel_id=current_user.id,
        )
        db.session.add(acao)
        db.session.commit()
        flash('Ação registrada com sucesso!', 'success')
        return redirect(url_for('acoes.index'))

    eleitores = Eleitor.query.order_by(Eleitor.nome).all()
    eventos = Evento.query.order_by(Evento.data_inicio.desc()).limit(20).all()
    bairros = Bairro.query.order_by(Bairro.nome).all()
    return render_template('acoes/form.html', tipos=TIPOS_ACAO,
                           eleitores=eleitores, eventos=eventos, bairros=bairros)


@bp.route('/<int:id>/excluir', methods=['POST'])
@login_required
def excluir(id):
    if not current_user.is_coordenador():
        flash('Sem permissão.', 'danger')
        return redirect(url_for('acoes.index'))
    acao = Acao.query.get_or_404(id)
    db.session.delete(acao)
    db.session.commit()
    flash('Ação removida.', 'warning')
    return redirect(url_for('acoes.index'))
