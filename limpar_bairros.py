from app import create_app, db
from app.models import Bairro, Eleitor, Evento

app = create_app()

with app.app_context():
    print("Iniciando limpeza da base de bairros...")
    
    # Desvincular relacionamento de eleitores
    eleitores = Eleitor.query.filter(Eleitor.bairro_id.is_not(None)).all()
    for eleitor in eleitores:
        eleitor.bairro_id = None
    if eleitores:
        print(f"{len(eleitores)} eleitores desvinculados dos bairros antigos.")

    # Desvincular relacionamento de eventos
    eventos = Evento.query.filter(Evento.bairro_id.is_not(None)).all()
    for evento in eventos:
        evento.bairro_id = None
    if eventos:
        print(f"{len(eventos)} eventos desvinculados dos bairros antigos.")

    # Excluir a tabela de bairros
    db.session.commit()
    deletados = Bairro.query.delete()
    db.session.commit()

    print(f"Sucesso! {deletados} bairros falsos antigos foram deletados da base.")
    print("A tabela de Territórios está livre para receber seus novos polígonos.")
