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


@bp.route('/importar', methods=['GET', 'POST'])
@login_required
def importar():
    if not current_user.is_coordenador():
        flash('Sem permissão.', 'danger')
        return redirect(url_for('territorio.index'))
        
    if request.method == 'POST':
        if 'arquivo' not in request.files:
            flash('Nenhum arquivo selecionado.', 'danger')
            return redirect(request.url)
            
        file = request.files['arquivo']
        if not file or not file.filename.endswith('.geojson'):
            flash('Apenas arquivos .geojson são suportados.', 'danger')
            return redirect(request.url)
            
        import json
        try:
            data = json.load(file)
            bairros_criados = 0
            
            for feature in data.get('features', []):
                props = feature.get('properties', {})
                # Tenta localizar o nome do bairro baseado nas tags comuns do IBGE/Prefeitura Jundiai
                nome = props.get('name') or props.get('NM_BAIRRO') or props.get('NOME') or props.get('nome') or props.get('bairro')
                if not nome:
                    continue
                    
                # Se o bairro já existir, ignoramos para não duplicar
                if Bairro.query.filter_by(nome=nome).first():
                    continue
                    
                geom = feature.get('geometry', {})
                typ = geom.get('type', '')
                coords = geom.get('coordinates', [])
                
                if not coords:
                    continue
                    
                # Calcula o Centro/Centróide do Polígono
                lng, lat = 0.0, 0.0
                try:
                    pts = []
                    if typ == 'Polygon':
                        pts = coords[0]
                    elif typ == 'MultiPolygon':
                        pts = coords[0][0]
                    elif typ == 'Point':
                        lng, lat = coords[0], coords[1]
                        
                    if pts:
                        lngs = [p[0] for p in pts]
                        lats = [p[1] for p in pts]
                        lng = sum(lngs) / len(lngs)
                        lat = sum(lats) / len(lats)
                except Exception:
                    continue
                    
                if lat != 0.0 and lng != 0.0:
                    b = Bairro(nome=nome, latitude=lat, longitude=lng)
                    db.session.add(b)
                    bairros_criados += 1
                    
            db.session.commit()
            flash(f'✅ Importação concluída! {bairros_criados} novos bairros adicionados.', 'success')
            return redirect(url_for('territorio.index'))
            
        except Exception as e:
            flash(f'Erro ao ler arquivo GeoJSON: {str(e)}', 'danger')
            return redirect(request.url)

    return render_template('territorio/importar.html')


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
