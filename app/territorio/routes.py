from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app.territorio import bp
from app.models import Bairro, Eleitor, db
from sqlalchemy import func


@bp.route('/')
@login_required
def index():
    bairros = db.session.query(
        Bairro,
        func.count(Eleitor.id).label('total_eleitores')
    ).outerjoin(Eleitor, Eleitor.bairro_id == Bairro.id)\
     .group_by(Bairro.id)\
     .order_by(func.count(Eleitor.id).desc()).all()
    return render_template('territorio/index.html', bairros=bairros)


@bp.route('/mapa')
@login_required
def mapa():
    bairros = Bairro.query.filter(Bairro.latitude.isnot(None)).all()
    return render_template('territorio/mapa.html', bairros=bairros)


@bp.route('/api/eleitores-geo')
@login_required
def api_eleitores_geo():
    """Retorna eleitores com localização para o mapa."""
    eleitores = Eleitor.query.join(Bairro).filter(
        Bairro.latitude.isnot(None)
    ).all()
    features = []
    for e in eleitores:
        features.append({
            'type': 'Feature',
            'geometry': {'type': 'Point', 'coordinates': [e.bairro.longitude, e.bairro.latitude]},
            'properties': {
                'nome': e.nome, 'bairro': e.bairro.nome,
                'classificacao': e.classificacao, 'status': e.status,
                'id': e.id,
            }
        })
    return jsonify({'type': 'FeatureCollection', 'features': features})


@bp.route('/api/bairros')
@login_required
def api_bairros():
    bairros = db.session.query(
        Bairro.id, Bairro.nome, Bairro.latitude, Bairro.longitude,
        func.count(Eleitor.id).label('total')
    ).outerjoin(Eleitor, Eleitor.bairro_id == Bairro.id)\
     .group_by(Bairro.id).all()
    return jsonify([{
        'id': b.id, 'nome': b.nome, 'lat': b.latitude, 'lng': b.longitude, 'total': b.total
    } for b in bairros])


@bp.route('/novo', methods=['GET', 'POST'])
@login_required
def novo():
    if not current_user.is_coordenador():
        flash('Sem permissão.', 'danger')
        return redirect(url_for('territorio.index'))
    if request.method == 'POST':
        bairro = Bairro(
            nome=request.form.get('nome', '').strip(),
            zona_eleitoral=request.form.get('zona_eleitoral', '').strip() or None,
            latitude=request.form.get('latitude', type=float),
            longitude=request.form.get('longitude', type=float),
            descricao=request.form.get('descricao', '').strip() or None,
        )
        db.session.add(bairro)
        db.session.commit()
        flash(f'Bairro "{bairro.nome}" cadastrado!', 'success')
        return redirect(url_for('territorio.index'))
    return render_template('territorio/form.html', bairro=None)


@bp.route('/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def editar(id):
    if not current_user.is_coordenador():
        flash('Sem permissão.', 'danger')
        return redirect(url_for('territorio.index'))
    bairro = Bairro.query.get_or_404(id)
    if request.method == 'POST':
        bairro.nome = request.form.get('nome', '').strip()
        bairro.zona_eleitoral = request.form.get('zona_eleitoral', '').strip() or None
        bairro.latitude = request.form.get('latitude', type=float)
        bairro.longitude = request.form.get('longitude', type=float)
        bairro.descricao = request.form.get('descricao', '').strip() or None
        db.session.commit()
        flash('Bairro atualizado!', 'success')
        return redirect(url_for('territorio.index'))
    return render_template('territorio/form.html', bairro=bairro)
