import os
from datetime import datetime, date
from cryptography.fernet import Fernet
from flask import current_app
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db, login_manager


# ── Tabelas de associação (M2M) ───────────────────────────────────────────────

evento_participantes = db.Table(
    'evento_participantes',
    db.Column('evento_id', db.Integer, db.ForeignKey('eventos.id'), primary_key=True),
    db.Column('eleitor_id', db.Integer, db.ForeignKey('eleitores.id'), primary_key=True),
)


# ── Helpers de criptografia ───────────────────────────────────────────────────

def get_fernet():
    key = current_app.config.get('ENCRYPTION_KEY')
    if not key:
        raise RuntimeError('ENCRYPTION_KEY não configurada.')
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt_value(value: str) -> str | None:
    if not value:
        return None
    return get_fernet().encrypt(value.encode()).decode()


def decrypt_value(token: str) -> str | None:
    if not token:
        return None
    try:
        return get_fernet().decrypt(token.encode()).decode()
    except Exception:
        return None


# ── Models ────────────────────────────────────────────────────────────────────

class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    senha_hash = db.Column(db.String(256))
    perfil = db.Column(db.String(20), default='eleitor')  # gestor / lideranca / cabo_eleitoral / eleitor
    ativo = db.Column(db.Boolean, default=True)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    ultimo_login = db.Column(db.DateTime)

    def set_password(self, senha):
        self.senha_hash = generate_password_hash(senha)

    def check_password(self, senha):
        return check_password_hash(self.senha_hash, senha)

    def is_admin(self):
        return self.perfil == 'gestor'

    def is_coordenador(self):
        return self.perfil in ('gestor', 'lideranca')

    def is_eleitor(self):
        return self.perfil == 'eleitor'

    def __repr__(self):
        return f'<User {self.email}>'


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


class Bairro(db.Model):
    __tablename__ = 'bairros'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False)
    zona_eleitoral = db.Column(db.String(20))
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    descricao = db.Column(db.Text)

    eleitores = db.relationship('Eleitor', backref='bairro', lazy='dynamic')

    @property
    def total_eleitores(self):
        return self.eleitores.count()

    def __repr__(self):
        return f'<Bairro {self.nome}>'


class Eleitor(db.Model):
    __tablename__ = 'eleitores'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(150), nullable=False, index=True)

    # Dados pessoais
    _cpf_criptografado = db.Column('cpf_criptografado', db.Text)
    nascimento = db.Column(db.Date)
    telefone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    genero = db.Column(db.String(20))  # masculino / feminino / outro / prefiro_nao_informar

    # Título de eleitor (futuro cruzamento TSE/TRE)
    titulo_numero = db.Column(db.String(20))
    titulo_zona = db.Column(db.String(10))
    titulo_secao = db.Column(db.String(10))

    # Endereço e território
    bairro_id = db.Column(db.Integer, db.ForeignKey('bairros.id'), index=True)
    zona_eleitoral = db.Column(db.String(20))
    secao_eleitoral = db.Column(db.String(10))
    endereco = db.Column(db.String(255))

    # Classificação política
    classificacao = db.Column(db.String(30), default='simpatizante')
    # simpatizante / ativista / lideranca / candidato / cabo_eleitoral
    status = db.Column(db.String(20), default='ativo')
    # ativo / inativo / convertido
    filiacao = db.Column(db.String(20), default='nao_filiado')
    # filiado / nao_filiado

    # Ponto focal (liderança responsável — auto-referência)
    ponto_focal_id = db.Column(db.Integer, db.ForeignKey('eleitores.id'), nullable=True)
    ponto_focal = db.relationship('Eleitor', remote_side=[id], backref='subordinados')

    # Meta
    observacoes = db.Column(db.Text)
    foto_url = db.Column(db.String(255))
    criado_por_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    criado_por = db.relationship('User', foreign_keys=[criado_por_id])
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    atualizado_em = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relacionamentos
    acoes = db.relationship('Acao', backref='eleitor', lazy='dynamic', foreign_keys='Acao.eleitor_id')
    comunicacoes = db.relationship('Comunicacao', backref='eleitor', lazy='dynamic')

    # CPF criptografado — property transparente
    @property
    def cpf(self):
        return decrypt_value(self._cpf_criptografado)

    @cpf.setter
    def cpf(self, value):
        self._cpf_criptografado = encrypt_value(value) if value else None

    @property
    def idade(self):
        if self.nascimento:
            today = date.today()
            return today.year - self.nascimento.year - (
                (today.month, today.day) < (self.nascimento.month, self.nascimento.day)
            )
        return None

    def __repr__(self):
        return f'<Eleitor {self.nome}>'


class Evento(db.Model):
    __tablename__ = 'eventos'

    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(200), nullable=False)
    tipo = db.Column(db.String(50), default='reuniao')
    # reuniao_base / visita_domiciliar / evento_publico / treinamento / outro
    descricao = db.Column(db.Text)
    local = db.Column(db.String(255))
    data_inicio = db.Column(db.DateTime, nullable=False)
    data_fim = db.Column(db.DateTime)
    cor = db.Column(db.String(10), default='#005BB5')

    criado_por_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    criado_por = db.relationship('User', foreign_keys=[criado_por_id])
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)

    participantes = db.relationship('Eleitor', secondary=evento_participantes, backref='eventos', lazy='dynamic')

    def to_calendar_dict(self):
        return {
            'id': self.id,
            'title': self.titulo,
            'start': self.data_inicio.isoformat(),
            'end': self.data_fim.isoformat() if self.data_fim else None,
            'color': self.cor,
            'extendedProps': {
                'tipo': self.tipo,
                'local': self.local,
                'descricao': self.descricao,
            }
        }

    def __repr__(self):
        return f'<Evento {self.titulo}>'


class Acao(db.Model):
    __tablename__ = 'acoes'

    id = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.String(30), nullable=False)
    # visita / ligacao / email / whatsapp / evento / material / outro
    descricao = db.Column(db.Text)
    resultado = db.Column(db.Text)
    data = db.Column(db.DateTime, default=datetime.utcnow)

    eleitor_id = db.Column(db.Integer, db.ForeignKey('eleitores.id'), nullable=True, index=True)
    evento_id = db.Column(db.Integer, db.ForeignKey('eventos.id'), nullable=True)
    bairro_id = db.Column(db.Integer, db.ForeignKey('bairros.id'), nullable=True)
    responsavel_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    evento = db.relationship('Evento', foreign_keys=[evento_id])
    responsavel = db.relationship('User', foreign_keys=[responsavel_id])

    def __repr__(self):
        return f'<Acao {self.tipo} - {self.data}>'


class Comunicacao(db.Model):
    __tablename__ = 'comunicacoes'

    id = db.Column(db.Integer, primary_key=True)
    canal = db.Column(db.String(20), nullable=False)  # email / whatsapp
    assunto = db.Column(db.String(200))
    corpo = db.Column(db.Text, nullable=False)
    enviado_em = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='pendente')  # pendente / enviado / erro
    erro_msg = db.Column(db.Text)

    eleitor_id = db.Column(db.Integer, db.ForeignKey('eleitores.id'), nullable=False)
    enviado_por_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    enviado_por = db.relationship('User', foreign_keys=[enviado_por_id])

    def __repr__(self):
        return f'<Comunicacao {self.canal} - {self.status}>'


class MensagemCandidato(db.Model):
    __tablename__ = 'mensagens_candidatos'

    id = db.Column(db.Integer, primary_key=True)
    eleitor_id = db.Column(db.Integer, db.ForeignKey('eleitores.id'), nullable=False)
    # The recipient (could be NULL if sent to the general system, or specific ID)
    candidato_id = db.Column(db.Integer, db.ForeignKey('eleitores.id'), nullable=True)
    
    assunto = db.Column(db.String(150), nullable=False)
    mensagem = db.Column(db.Text, nullable=False)
    lida = db.Column(db.Boolean, default=False)
    criada_em = db.Column(db.DateTime, default=datetime.utcnow)

    remetente = db.relationship('Eleitor', foreign_keys=[eleitor_id], backref='mensagens_enviadas')
    destinatario = db.relationship('Eleitor', foreign_keys=[candidato_id], backref='mensagens_recebidas')

    def __repr__(self):
        return f'<MensagemCandidato {self.id} de {self.eleitor_id}>'



class ConfiguracaoSistema(db.Model):
    __tablename__ = 'configuracoes'

    id = db.Column(db.Integer, primary_key=True)
    chave = db.Column(db.String(60), unique=True, nullable=False)
    valor = db.Column(db.Text)
    descricao = db.Column(db.String(255))
    atualizado_em = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @classmethod
    def get(cls, chave, default=None):
        row = cls.query.filter_by(chave=chave).first()
        return row.valor if row else default

    @classmethod
    def set(cls, chave, valor, descricao=None):
        row = cls.query.filter_by(chave=chave).first()
        if row:
            row.valor = valor
        else:
            row = cls(chave=chave, valor=valor, descricao=descricao)
            db.session.add(row)
        db.session.commit()
