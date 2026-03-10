import requests as http_requests
from datetime import datetime
from flask import render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from flask_mail import Message
from app.comunicacao import bp
from app.models import Eleitor, Comunicacao, Bairro, db
from app import mail


def _send_whatsapp(telefone: str, mensagem: str) -> dict:
    """Envia mensagem via Evolution API."""
    base_url = current_app.config['EVOLUTION_API_URL'].rstrip('/')
    instance = current_app.config['EVOLUTION_INSTANCE']
    api_key = current_app.config['EVOLUTION_API_KEY']

    numero = ''.join(filter(str.isdigit, telefone))
    if not numero.startswith('55'):
        numero = '55' + numero
        
    url = f"{base_url}/message/sendText/{instance}"
    payload = {
        "number": numero,
        "options": {"delay": 1200, "presence": "composing"},
        "text": mensagem
    }
    resp = http_requests.post(url, json=payload, headers={'apikey': api_key}, timeout=15)
    return resp.json()


@bp.route('/')
@login_required
def index():
    page = request.args.get('page', 1, type=int)
    canal = request.args.get('canal', '')
    query = Comunicacao.query
    if canal:
        query = query.filter_by(canal=canal)
    comunicacoes = query.order_by(Comunicacao.enviado_em.desc()).paginate(page=page, per_page=30, error_out=False)
    return render_template('comunicacao/index.html', comunicacoes=comunicacoes, canal=canal)


@bp.route('/nova', methods=['GET', 'POST'])
@login_required
def nova():
    bairros = Bairro.query.order_by(Bairro.nome).all()
    if request.method == 'POST':
        canal = request.form.get('canal')
        assunto = request.form.get('assunto', '').strip()
        mensagem = request.form.get('mensagem', '').strip()
        destino = request.form.get('destino')  # individual / bairro / todos / filiados
        eleitor_id = request.form.get('eleitor_id', type=int)
        bairro_id = request.form.get('bairro_id', type=int)

        # Monta lista de destinatários
        if destino == 'individual' and eleitor_id:
            destinatarios = [Eleitor.query.get(eleitor_id)]
        elif destino == 'bairro' and bairro_id:
            destinatarios = Eleitor.query.filter_by(bairro_id=bairro_id, status='ativo').all()
        elif destino == 'filiados':
            destinatarios = Eleitor.query.filter_by(filiacao='filiado', status='ativo').all()
        else:  # todos
            destinatarios = Eleitor.query.filter_by(status='ativo').all()

        enviados = 0
        erros = 0
        for eleitor in [d for d in destinatarios if d]:
            com = Comunicacao(
                canal=canal,
                assunto=assunto,
                corpo=mensagem,
                eleitor_id=eleitor.id,
                enviado_por_id=current_user.id,
                status='pendente',
            )
            try:
                if canal == 'email':
                    if not eleitor.email:
                        com.status = 'erro'
                        com.erro_msg = 'Eleitor sem e-mail cadastrado.'
                    else:
                        msg = Message(
                            subject=assunto or 'Mensagem do PSDB Jundiaí',
                            recipients=[eleitor.email],
                            body=mensagem,
                        )
                        mail.send(msg)
                        com.status = 'enviado'
                        enviados += 1
                elif canal == 'whatsapp':
                    if not eleitor.telefone:
                        com.status = 'erro'
                        com.erro_msg = 'Eleitor sem telefone cadastrado.'
                    else:
                        result = _send_whatsapp(eleitor.telefone, mensagem)
                        if result.get('key') or result.get('status') == 'success':
                            com.status = 'enviado'
                            enviados += 1
                        else:
                            com.status = 'erro'
                            com.erro_msg = str(result)
                            erros += 1
            except Exception as e:
                com.status = 'erro'
                com.erro_msg = str(e)
                erros += 1
            db.session.add(com)

        db.session.commit()
        flash(f'✅ {enviados} mensagens enviadas. ❌ {erros} erros.', 'info')
        return redirect(url_for('comunicacao.index'))

    eleitores = Eleitor.query.order_by(Eleitor.nome).all()
    return render_template('comunicacao/nova.html', eleitores=eleitores, bairros=bairros)


@bp.route('/buscar-eleitor')
@login_required
def buscar_eleitor():
    """Endpoint AJAX para busca de eleitor no formulário de comunicação."""
    q = request.args.get('q', '')
    eleitores = Eleitor.query.filter(Eleitor.nome.ilike(f'%{q}%')).limit(10).all()
    return jsonify([{'id': e.id, 'nome': e.nome, 'telefone': e.telefone or '', 'email': e.email or ''} for e in eleitores])
