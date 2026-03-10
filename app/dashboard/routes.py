from flask import render_template, jsonify
from flask_login import login_required
from datetime import datetime, timedelta
from sqlalchemy import func
from app.dashboard import bp
from app.models import Eleitor, Bairro, Evento, Acao, Comunicacao, db


@bp.route('/')
@login_required
def index():
    # KPIs
    total_eleitores = Eleitor.query.count()
    total_filiados = Eleitor.query.filter_by(filiacao='filiado').count()
    total_ativos = Eleitor.query.filter_by(status='ativo').count()

    # Novos este mês
    inicio_mes = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    novos_mes = Eleitor.query.filter(Eleitor.criado_em >= inicio_mes).count()

    # Próximos eventos (7 dias)
    agora = datetime.utcnow()
    proximos_eventos = Evento.query.filter(
        Evento.data_inicio >= agora,
        Evento.data_inicio <= agora + timedelta(days=7)
    ).order_by(Evento.data_inicio).limit(5).all()

    # Últimas ações
    ultimas_acoes = Acao.query.order_by(Acao.data.desc()).limit(8).all()

    # Top bairros por eleitor
    top_bairros = db.session.query(
        Bairro.nome, func.count(Eleitor.id).label('total')
    ).join(Eleitor, Eleitor.bairro_id == Bairro.id).group_by(Bairro.nome)\
     .order_by(func.count(Eleitor.id).desc()).limit(8).all()

    return render_template(
        'dashboard/index.html',
        total_eleitores=total_eleitores,
        total_filiados=total_filiados,
        total_ativos=total_ativos,
        novos_mes=novos_mes,
        proximos_eventos=proximos_eventos,
        ultimas_acoes=ultimas_acoes,
        top_bairros=top_bairros,
    )


@bp.route('/api/crescimento')
@login_required
def api_crescimento():
    """Retorna crescimento mensal de eleitores para o gráfico."""
    hoje = datetime.utcnow()
    dados = []
    for i in range(11, -1, -1):
        mes_ref = hoje - timedelta(days=30 * i)
        inicio = mes_ref.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if i == 0:
            fim = hoje
        else:
            prox = mes_ref.replace(day=28) + timedelta(days=4)
            fim = prox - timedelta(days=prox.day)
        count = Eleitor.query.filter(
            Eleitor.criado_em >= inicio,
            Eleitor.criado_em <= fim
        ).count()
        dados.append({'mes': inicio.strftime('%b/%Y'), 'total': count})
    return jsonify(dados)


@bp.route('/api/classificacao')
@login_required
def api_classificacao():
    """Retorna distribuição por classificação."""
    resultados = db.session.query(
        Eleitor.classificacao, func.count(Eleitor.id)
    ).group_by(Eleitor.classificacao).all()
    labels = {'simpatizante': 'Simpatizante', 'ativista': 'Ativista',
              'lideranca': 'Liderança', 'candidato': 'Candidato', 'cabo_eleitoral': 'Cabo Eleitoral'}
    return jsonify([{'label': labels.get(r[0], r[0]), 'total': r[1]} for r in resultados])
