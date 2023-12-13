from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine
import mysql.connector
import subprocess

app = Flask(__name__)

db_config = {
    "host": "localhost",
    "user": "root",
    "password": "",
    "database": "detencao_db",
}

app.config[
    "SQLALCHEMY_DATABASE_URI"
] = f"mysql+mysqlconnector://{db_config['user']}:{db_config['password']}@{db_config['host']}/{db_config['database']}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)


class LogEmail(db.Model):
    __tablename__ = "logemail"
    log_id = db.Column(db.Integer, primary_key=True)
    pessoa_id = db.Column(db.Integer, nullable=True)
    assunto = db.Column(db.String(255), nullable=True)
    corpo = db.Column(db.Text, nullable=True)


class Pessoa(db.Model):
    __tablename__ = "pessoa"
    pessoa_id = db.Column(db.Integer, primary_key=True)
    entrada_tempo = db.Column(db.DateTime, nullable=True)
    saida_tempo = db.Column(db.DateTime, nullable=True)


class Usuario(db.Model):
    __tablename__ = "usuario"
    usuario_id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(30), nullable=True)
    telefone = db.Column(db.String(15), nullable=True)
    senha = db.Column(db.String(255), nullable=False)


# Rota para iniciar o sistema de detecção
@app.route("/iniciar_detecao", methods=["POST"])
def iniciar_detecao():
    try:
        # Lógica para iniciar o sistema de detecção
        # Exemplo usando subprocess para executar um script externo
        subprocess.run(["python", "counter.py"])

        return jsonify({"mensagem": "Sistema de detecção iniciado com sucesso."})

    except Exception as e:
        return jsonify({"erro": str(e)})


# Rota para parar o sistema de detecção
@app.route("/parar_detecao", methods=["POST"])
def parar_detecao():
    try:
        # Lógica para parar o sistema de detecção
        # Exemplo usando subprocess para enviar um sinal de interrupção (Ctrl+C)
        subprocess.run(["pkill", "-f", "counter.py"])

        return jsonify({"mensagem": "Sistema de detecção parado com sucesso."})

    except Exception as e:
        return jsonify({"erro": str(e)})


# Rota para criar um novo log de e-mail
@app.route("/logemail", methods=["POST"])
def criar_log_email():
    try:
        data_input = request.json

        novo_log = LogEmail(
            pessoa_id=data_input.get("pessoa_id"),
            assunto=data_input.get("assunto"),
            corpo=data_input.get("corpo"),
        )

        db.session.add(novo_log)
        db.session.commit()

        return jsonify(
            {"log_id": novo_log.log_id, "mensagem": "Log de e-mail criado com sucesso."}
        )

    except Exception as e:
        return jsonify({"erro": str(e)})


# Rota para obter todos os logs de e-mail
@app.route("/logemails", methods=["GET"])
def obter_todos_logs_email():
    try:
        logs = LogEmail.query.all()
        logs_serializados = [
            {
                "log_id": log.log_id,
                "pessoa_id": log.pessoa_id,
                "assunto": log.assunto,
                "corpo": log.corpo,
            }
            for log in logs
        ]

        return jsonify({"logs_email": logs_serializados})

    except Exception as e:
        return jsonify({"erro": str(e)})


# Rota para criar uma nova pessoa
@app.route("/pessoa", methods=["POST"])
def criar_pessoa():
    try:
        data_input = request.json

        nova_pessoa = Pessoa(
            entrada_tempo=data_input.get("entrada_tempo"),
            saida_tempo=data_input.get("saida_tempo"),
        )

        db.session.add(nova_pessoa)
        db.session.commit()

        return jsonify(
            {
                "pessoa_id": nova_pessoa.pessoa_id,
                "mensagem": "Pessoa criada com sucesso.",
            }
        )

    except Exception as e:
        return jsonify({"erro": str(e)})


# Rota para obter todas as pessoas
@app.route("/pessoas", methods=["GET"])
def obter_todas_pessoas():
    try:
        pessoas = Pessoa.query.all()
        pessoas_serializadas = [
            {
                "pessoa_id": pessoa.pessoa_id,
                "entrada_tempo": str(pessoa.entrada_tempo),
                "saida_tempo": str(pessoa.saida_tempo),
            }
            for pessoa in pessoas
        ]

        return jsonify({"pessoas": pessoas_serializadas})

    except Exception as e:
        return jsonify({"erro": str(e)})


# Rota para criar um novo usuário
@app.route("/usuario", methods=["POST"])
def criar_usuario():
    try:
        data_input = request.json

        novo_usuario = Usuario(
            username=data_input.get("username"),
            email=data_input.get("email"),
            telefone=data_input.get("telefone"),
            senha=data_input.get("senha"),
        )

        db.session.add(novo_usuario)
        db.session.commit()

        return jsonify(
            {
                "usuario_id": novo_usuario.usuario_id,
                "mensagem": "Usuário criado com sucesso.",
            }
        )

    except Exception as e:
        return jsonify({"erro": str(e)})


# Rota para obter todos os usuários
@app.route("/usuarios", methods=["GET"])
def obter_todos_usuarios():
    try:
        usuarios = Usuario.query.all()
        usuarios_serializados = [
            {
                "usuario_id": usuario.usuario_id,
                "username": usuario.username,
                "email": usuario.email,
                "telefone": usuario.telefone,
            }
            for usuario in usuarios
        ]

        return jsonify({"usuarios": usuarios_serializados})

    except Exception as e:
        return jsonify({"erro": str(e)})


if __name__ == "__main__":
    db.create_all()
    app.run(debug=True, host="0.0.0.0", port=5001)
