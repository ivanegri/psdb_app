from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from datetime import datetime
from app import db
from app.portal import bp
from app.models import Eleitor, Bairro, Evento, MensagemCandidato, db

@bp.before_request
@login_required
def check_eleitor_only():
    # Garantir que só eleitores acessem o portal
    if not current_user.is_eleitor():
        flash('Este portal é exclusivo para eleitores.', 'warning')
        return redirect(url_for('dashboard.index'))

@bp.route('/painel')
def index():
    eleitor = Eleitor.query.filter_by(email=current_user.email).first()
    
    # Eventos próximos (5 mais recentes da data atual em diante)
    proximos_eventos = Evento.query.filter(Evento.data_inicio >= datetime.utcnow()).order_by(Evento.data_inicio).limit(5).all()
    
    return render_template('portal/index.html', eleitor=eleitor, eventos=proximos_eventos)

@bp.route('/meus-dados', methods=['GET', 'POST'])
def meus_dados():
    eleitor = Eleitor.query.filter_by(email=current_user.email).first()
    bairros = Bairro.query.order_by(Bairro.nome).all()

    if request.method == 'POST':
        # Permite atualizar fone, endereco, bairro
        if eleitor:
            eleitor.telefone = request.form.get('telefone', '').strip()
            eleitor.endereco = request.form.get('endereco', '').strip()
            
            bairro_id = request.form.get('bairro_id')
            if bairro_id and bairro_id.isdigit():
                eleitor.bairro_id = int(bairro_id)
            else:
                eleitor.bairro_id = None
            
            eleitor.atualizado_em = datetime.utcnow()
            db.session.commit()
            
            flash('Seus dados foram atualizados com sucesso.', 'success')
            return redirect(url_for('portal.index'))
            
    return render_template('portal/meus_dados.html', eleitor=eleitor, bairros=bairros)

@bp.route('/mensagem', methods=['GET', 'POST'])
def mensagem():
    eleitor = Eleitor.query.filter_by(email=current_user.email).first()
    
    # Pegar eleitores que estão como "candidato"
    candidatos = Eleitor.query.filter_by(classificacao='candidato').order_by(Eleitor.nome).all()

    if request.method == 'POST':
        if not eleitor:
            flash('Seu usuário não está devidamente vinculado. Contacte o suporte.', 'danger')
            return redirect(url_for('portal.index'))

        assunto = request.form.get('assunto', '').strip()
        corpo = request.form.get('mensagem', '').strip()
        candidato_id = request.form.get('candidato_id')

        # candidato_id opcional (pode ser "Geral")
        cid = int(candidato_id) if candidato_id and candidato_id.isdigit() else None

        nova_msg = MensagemCandidato(
            eleitor_id=eleitor.id,
            candidato_id=cid,
            assunto=assunto,
            mensagem=corpo
        )
        db.session.add(nova_msg)
        db.session.commit()
        
        flash('Sua mensagem foi enviada ao candidato/equipe com sucesso! Eles receberão seu contato.', 'success')
        return redirect(url_for('portal.index'))

    return render_template('portal/mensagem.html', candidatos=candidatos)
