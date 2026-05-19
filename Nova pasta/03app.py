from flask import Flask, request, render_template_string, redirect, url_for, flash
import sqlite3
from datetime import datetime
import urllib.parse
import json
import re

app = Flask(__name__)
app.secret_key = 'ezetec_super_secret_key_2025'
DB_NAME = 'ezetec_clientes.db'

# --- INICIALIZAÇÃO E EVOLUÇÃO DO BANCO DE DADOS ---
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS ordens_servico (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT,
            telefone TEXT,
            aparelho TEXT,
            marca TEXT,
            modelo TEXT,
            defeito_relatado TEXT,
            estado_entrada TEXT,
            observacao TEXT,
            defeito_encontrado TEXT,
            valor_conserto REAL DEFAULT 0.0,
            valor_pecas REAL DEFAULT 0.0,
            tecnico_responsavel TEXT,
            status_retirada TEXT,
            data_entrada DATE,
            data_saida DATE
        )
    ''')
    
    colunas_novas = {
        'valor_pecas': 'REAL DEFAULT 0.0',
        'tecnico_responsavel': 'TEXT',
        'data_saida': 'DATE'
    }
    for coluna, tipo in colunas_novas.items():
        try:
            c.execute(f'ALTER TABLE ordens_servico ADD COLUMN {coluna} {tipo}')
        except sqlite3.OperationalError:
            pass 
            
    conn.commit()
    conn.close()

init_db()

# --- TEMPLATE INTERFACE PREMIUM (UI/UX) ---
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Ezetec Pro - Sistema de Gestão de Assistência</title>
    <style>
        :root {
            --primary: #1a73e8; --primary-hover: #1557b0;
            --bg-main: #f8f9fa; --card-bg: #ffffff;
            --text-dark: #202124; --text-muted: #5f6368;
            --border-color: #dadce0;
            --status-loja: #e8f0fe; --status-loja-txt: #1a73e8;
            --status-entregue: #e6f4ea; --status-entregue-txt: #137333;
            --status-abandonado: #fce8e6; --status-abandonado-txt: #c5221f;
            --status-retirado: #fff3cd; --status-retirado-txt: #856404;
            --status-vendido: #f3e5f5; --status-vendido-txt: #8e24aa;
        }

        body { font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: var(--bg-main); color: var(--text-dark); margin: 0; padding: 25px; }
        header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 25px; border-bottom: 1px solid var(--border-color); padding-bottom: 15px; }
        header h1 { margin: 0; font-size: 24px; color: var(--primary); display: flex; align-items: center; gap: 10px; }
        
        .dashboard { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 25px; }
        .card-stat { background: var(--card-bg); padding: 15px 20px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); border-left: 4px solid var(--primary); }
        .card-stat.alert { border-left-color: #f4b400; }
        .card-stat.success { border-left-color: #0f9d58; transition: background 0.2s; }
        .card-stat.success:hover { background: #f1fbe9; }
        .card-stat .label { font-size: 12px; color: var(--text-muted); text-transform: uppercase; font-weight: bold; }
        .card-stat .value { font-size: 22px; font-weight: bold; margin-top: 5px; }

        .main-layout { display: flex; gap: 25px; align-items: flex-start; }
        .left-panel { flex: 1; background: var(--card-bg); padding: 25px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); position: sticky; top: 25px; border: 1px solid var(--border-color); }
        .right-panel { flex: 2; background: var(--card-bg); padding: 25px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); border: 1px solid var(--border-color); }
        
        .form-group { display: flex; flex-direction: column; margin-bottom: 14px; position: relative; }
        .form-group label { font-size: 13px; font-weight: 600; color: var(--text-dark); margin-bottom: 5px; }
        input, select, textarea { padding: 10px 12px; border: 1px solid var(--border-color); border-radius: 6px; font-size: 14px; box-sizing: border-box; background: #fff; color: var(--text-dark); }
        input:focus, select:focus, textarea:focus { border-color: var(--primary); outline: none; box-shadow: 0 0 0 2px rgba(26,115,232,0.2); }
        
        textarea.fixed-size { height: 80px; resize: none; }
        .grid-form { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
        .full-width { grid-column: 1 / -1; }
        
        .input-privacy-container { display: flex; align-items: center; position: relative; }
        .input-privacy-container input { padding-right: 40px; }
        .btn-toggle-input { position: absolute; right: 10px; background: none; border: none; cursor: pointer; font-size: 16px; color: var(--text-muted); padding: 5px; }
        
        button.btn-primary { width: 100%; padding: 12px; background-color: var(--primary); color: white; border: none; border-radius: 6px; font-weight: bold; font-size: 14px; cursor: pointer; transition: background 0.2s; }
        button.btn-primary:hover { background-color: var(--primary-hover); }
        
        .toolbar { display: flex; justify-content: space-between; align-items: center; gap: 15px; margin-bottom: 15px; flex-wrap: wrap; }
        .search-box { flex: 1; min-width: 250px; }
        .search-box input { border: 2px solid var(--primary); border-radius: 6px; padding: 10px; font-size: 14px; width: 100%; }
        
        .status-filters { display: flex; gap: 5px; }
        .filter-btn { padding: 6px 12px; border: 1px solid var(--border-color); background: #fff; border-radius: 20px; font-size: 12px; font-weight: bold; cursor: pointer; }
        .filter-btn.active { background: var(--primary); color: white; border-color: var(--primary); }

        .table-container { overflow-x: auto; max-height: 550px; border: 1px solid var(--border-color); border-radius: 6px; }
        table { width: 100%; border-collapse: collapse; font-size: 13px; }
        th, td { padding: 12px; border-bottom: 1px solid var(--border-color); text-align: left; }
        th { background-color: #f1f3f4; color: var(--text-dark); font-weight: 600; position: sticky; top: 0; z-index: 10; }
        tr:hover { background-color: #f8f9fa; }
        
        .alerta-laranja { background-color: #fff3e0 !important; }
        
        .badge { padding: 5px 10px; border-radius: 4px; font-size: 11px; font-weight: bold; display: inline-block; text-transform: uppercase; }
        .status-loja { background: var(--status-loja); color: var(--status-loja-txt); }
        .status-entregue { background: var(--status-entregue); color: var(--status-entregue-txt); }
        .status-abandonado { background: var(--status-abandonado); color: var(--status-abandonado-txt); }
        .status-retirado { background: var(--status-retirado); color: var(--status-retirado-txt); }
        .status-vendido { background: var(--status-vendido); color: var(--status-vendido-txt); }
        
        .acoes { display: flex; gap: 5px; }
        .acoes a, .acoes button { text-decoration: none; padding: 6px 10px; border-radius: 4px; font-size: 12px; border: none; color: white; cursor: pointer; font-weight: 600; text-align: center; }
        .btn-zap { background: #25d366; }
        .btn-edit { background: #f4b400; color: #202124; }
        .btn-print { background: #5f6368; }

        .modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.4); z-index: 100; backdrop-filter: blur(2px); }
        .modal-content { background: white; margin: 2% auto; padding: 25px; width: 90%; max-width: 650px; border-radius: 8px; box-shadow: 0 4px 24px rgba(0,0,0,0.15); max-height: 90vh; overflow-y: auto; }
        
        .flash-messages { margin-bottom: 15px; }
        .flash-msg { padding: 10px 15px; border-radius: 6px; margin-bottom: 8px; font-weight: bold; }
        .flash-success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
        .flash-error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
        
        @media(max-width: 1024px) {
            .main-layout { flex-direction: column; }
            .left-panel { position: static; width: 100%; }
        }
    </style>
</head>
<body>

    <header>
        <h1>⚡ Ezetec Pro <span style="font-size:14px; color:var(--text-muted); font-weight:normal;">| Enterprise Service Management</span></h1>
        <div style="display: flex; align-items: center; gap: 10px;">
            <button class="btn-primary" style="width: auto; padding: 8px 20px; background: #0f9d58;" onclick="document.getElementById('modalImport').style.display='block'">📥 Importar JSON</button>
            <div style="font-size: 14px; font-weight: 600; color: var(--text-muted);">Balcão Operacional</div>
        </div>
    </header>

    <!-- FLASH MESSAGES -->
    {% with messages = get_flashed_messages(with_categories=true) %}
      {% if messages %}
        <div class="flash-messages">
          {% for category, message in messages %}
            <div class="flash-msg flash-{{ category }}">{{ message }}</div>
          {% endfor %}
        </div>
      {% endif %}
    {% endwith %}

    <!-- DASHBOARD DE MÉTRICAS -->
    <div class="dashboard">
        <div class="card-stat">
            <div class="label">Aparelhos na Loja</div>
            <div class="value">{{ stats.na_loja }}</div>
        </div>
        
        <div class="card-stat success" onclick="toggleFaturamento(this)" style="cursor: pointer;" title="Clique para exibir/ocultar valor">
            <div class="label">Faturamento Geral 🔒</div>
            <div class="value" id="txt-faturamento" data-real="R$ {{ "%.2f"|format(stats.faturamento) }}">R$ ••••</div>
        </div>
        
        <div class="card-stat">
            <div class="label">Entregues / Retirados</div>
            <div class="value">{{ stats.entregues }}</div>
        </div>
        <div class="card-stat alert">
            <div class="label">Avisos (+90 dias)</div>
            <div class="value">{{ stats.alertas }}</div>
        </div>
    </div>

    <div class="main-layout">
        <!-- FORMULÁRIO DE ENTRADA -->
        <div class="left-panel">
            <h3>Entrada de Equipamento</h3>
            <form action="/add" method="POST" class="grid-form">
                <div class="form-group full-width">
                    <label>Nome do Cliente</label>
                    <input type="text" name="nome" placeholder="Nome Completo" required>
                </div>
                <div class="form-group full-width">
                    <label>WhatsApp (Com DDD)</label>
                    <input type="text" name="telefone" placeholder="Ex: 11999999999" required>
                </div>
                <div class="form-group">
                    <label>Equipamento</label>
                    <input type="text" name="aparelho" placeholder="Ex: Notebook, Televisor" required>
                </div>
                <div class="form-group">
                    <label>Marca</label>
                    <input type="text" name="marca" placeholder="Ex: Samsung, Dell">
                </div>
                <div class="form-group full-width">
                    <label>Modelo / Versão</label>
                    <input type="text" name="modelo" placeholder="Ex: Inspiron 15 3000">
                </div>
                
                <div class="form-group full-width">
                    <label>Defeito Declarado</label>
                    <textarea name="defeito_relatado" class="fixed-size" placeholder="Relato detalhado do cliente..." required></textarea>
                </div>
                
                <div class="form-group full-width">
                    <label>Status Inicial</label>
                    <select name="status_retirada">
                        <option value="Na Loja">Na Loja</option>
                        <option value="Entregue">Entregue</option>
                        <option value="Abandonado">Abandonado</option>
                        <option value="Retirado">Retirado</option>
                        <option value="Vendido para a loja">Vendido para a loja</option>
                    </select>
                </div>
                
                <div class="form-group full-width">
                    <label>Estado de Entrada / Avarias</label>
                    <input type="text" name="estado_entrada" placeholder="Riscos, partes quebradas, sem parafusos...">
                </div>
                <div class="form-group full-width">
                    <label>Observações Internas</label>
                    <input type="text" name="observacao" placeholder="Informações exclusivas da bancada">
                </div>
                <button type="submit" class="btn-primary">EMITIR ORDEM DE SERVIÇO</button>
            </form>
        </div>

        <!-- LISTA FILTRÁVEL -->
        <div class="right-panel">
            <div class="toolbar">
                <div class="search-box">
                    <input type="text" id="buscaInput" onkeyup="filtrarTabela()" placeholder="🔍 Pesquisa rápida inteligente...">
                </div>
                <div class="status-filters">
                    <button class="filter-btn active" onclick="filtrarStatus('TODOS')">Todos</button>
                    <button class="filter-btn" onclick="filtrarStatus('Na Loja')">Na Loja</button>
                    <button class="filter-btn" onclick="filtrarStatus('Entregue')">Entregue</button>
                    <button class="filter-btn" onclick="filtrarStatus('Vendido')">Vendidos</button>
                </div>
            </div>

            <div class="table-container">
                <table>
                    <thead>
                        <tr>
                            <th>OS</th>
                            <th>Cliente</th>
                            <th>Equipamento</th>
                            <th>Entrada</th>
                            <th>Status</th>
                            <th>Ações</th>
                        </tr>
                    </thead>
                    <tbody id="tabelaCorpo">
                        {% for os in ordens %}
                        <tr class="{% if os.alerta_laranja %}alerta-laranja{% endif %}" data-status-row="{{ os.status_retirada }}">
                            <td><strong>#{{ os.id }}</strong></td>
                            <td><strong>{{ os.nome }}</strong><br><small>{{ os.telefone }}</small></td>
                            <td><span>{{ os.aparelho }}</span><br><small>{{ os.marca }} {{ os.modelo }}</small></td>
                            <td>{{ os.data_entrada_fmt }}</td>
                            <td>
                                <span class="badge {% if os.status_retirada == 'Na Loja' %}status-loja{% elif os.status_retirada == 'Entregue' %}status-entregue{% elif os.status_retirada == 'Abandonado' %}status-abandonado{% elif os.status_retirada == 'Retirado' %}status-retirado{% else %}status-vendido{% endif %}">
                                    {{ os.status_retirada }}
                                </span>
                            </td>
                            <td class="acoes">
                                <a href="{{ os.zap_link }}" target="_blank" class="btn-zap">Zap</a>
                                <button type="button" class="btn-edit" 
                                    data-id="{{ os.id }}" data-nome="{{ os.nome }}" data-telefone="{{ os.telefone }}"
                                    data-aparelho="{{ os.aparelho }}" data-marca="{{ os.marca }}" data-modelo="{{ os.modelo }}"
                                    data-defeito_relatado="{{ os.defeito_relatado }}" data-estado_entrada="{{ os.estado_entrada }}"
                                    data-observacao="{{ os.observacao }}" data-defeito_encontrado="{{ os.defeito_encontrado }}"
                                    data-valor="{{ os.valor_conserto }}" data-pecas="{{ os.valor_pecas }}"
                                    data-tecnico="{{ os.tecnico_responsavel }}" data-status="{{ os.status_retirada }}"
                                    data-saida="{{ os.data_saida }}" onclick="abrirModalEdicao(this)">Editar</button>
                                <a href="/print/{{ os.id }}" target="_blank" class="btn-print">Doc</a>
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
    </div>

    <!-- MODAL GERENCIAL DE EDIÇÃO -->
    <div id="modalEdicao" class="modal">
        <div class="modal-content">
            <h3 style="border-bottom: 2px solid #f4b400; padding-bottom: 8px; margin-top:0;">Prontuário e Atualização da OS</h3>
            <form action="/update" method="POST" class="grid-form">
                <input type="hidden" name="old_id" id="mod_old_id">
                
                <div class="form-group">
                    <label style="color: var(--primary);">Número da OS</label>
                    <input type="number" name="id" id="mod_id" required>
                </div>
                <div class="form-group">
                    <label>Status Atual do Fluxo</label>
                    <select name="status_retirada" id="mod_status">
                        <option value="Na Loja">Na Loja</option>
                        <option value="Entregue">Entregue</option>
                        <option value="Abandonado">Abandonado</option>
                        <option value="Retirado">Retirado</option>
                        <option value="Vendido para a loja">Vendido para a loja</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>Cliente</label>
                    <input type="text" name="nome" id="mod_nome" required>
                </div>
                <div class="form-group">
                    <label>Telefone Contato</label>
                    <input type="text" name="telefone" id="mod_telefone" required>
                </div>
                <div class="form-group">
                    <label>Aparelho</label>
                    <input type="text" name="aparelho" id="mod_aparelho" required>
                </div>
                <div class="form-group">
                    <label>Marca</label>
                    <input type="text" name="marca" id="mod_marca">
                </div>
                <div class="form-group">
                    <label>Modelo</label>
                    <input type="text" name="modelo" id="mod_modelo">
                </div>
                <div class="form-group">
                    <label>Data de Fechamento/Saída</label>
                    <input type="date" name="data_saida" id="mod_saida">
                </div>
                
                <div class="form-group full-width">
                    <label>Defeito Declarado</label>
                    <input type="text" name="defeito_relatado" id="mod_defeito_relatado" required>
                </div>
                <div class="form-group">
                    <label>Condições de Entrada</label>
                    <input type="text" name="estado_entrada" id="mod_estado_entrada">
                </div>
                <div class="form-group">
                    <label>Observações Técnicas</label>
                    <input type="text" name="observacao" id="mod_observacao">
                </div>

                <div class="form-group full-width" style="border-top: 2px dashed var(--border-color); padding-top: 15px; margin-top: 10px;">
                    <label style="color: #c5221f;">Laudo Técnico / Solução Aplicada</label>
                    <input type="text" name="defeito_encontrado" id="mod_defeito_encontrado" placeholder="O que foi reparado no equipamento?">
                </div>
                <div class="form-group">
                    <label>Técnico Responsável</label>
                    <input type="text" name="tecnico_responsavel" id="mod_tecnico" placeholder="Iniciais ou nome do técnico">
                </div>
                <div class="form-group">
                    <label>Custo das Peças (R$)</label>
                    <input type="number" step="0.01" name="valor_pecas" id="mod_pecas" placeholder="0.00">
                </div>
                
                <div class="form-group full-width">
                    <label style="font-weight: bold; color: #137333;">Valor Total Cobrado do Cliente (R$)</label>
                    <div class="input-privacy-container">
                        <input type="password" name="valor_conserto" id="mod_valor" placeholder="0.00">
                        <button type="button" class="btn-toggle-input" onclick="toggleInputValor()" title="Exibir/Ocultar valor">👁️</button>
                    </div>
                </div>
                
                <button type="submit" class="btn-primary" style="background: #f4b400; color: black; margin-top:15px;">SALVAR ALTERAÇÕES OPERACIONAIS</button>
                <button type="button" class="btn-primary" style="background: var(--text-muted);" onclick="fecharModalEdicao()">FECHAR JANELA</button>
            </form>
        </div>
    </div>

    <!-- MODAL DE IMPORTAÇÃO JSON -->
    <div id="modalImport" class="modal">
        <div class="modal-content">
            <h3 style="margin-top:0; color: #0f9d58;">📥 Importar Ordens via Arquivo JSON</h3>
            <form action="/import" method="POST" enctype="multipart/form-data">
                <div class="form-group">
                    <label>Selecione o arquivo JSON (.json)</label>
                    <input type="file" name="json_file" accept=".json" required>
                </div>
                <div style="display: flex; gap: 10px; justify-content: flex-end; margin-top: 20px;">
                    <button type="button" class="btn-primary" style="width: auto; background: #5f6368;" onclick="document.getElementById('modalImport').style.display='none'">Cancelar</button>
                    <button type="submit" class="btn-primary" style="width: auto; background: #0f9d58;">Importar Agora</button>
                </div>
            </form>
        </div>
    </div>

    <script>
        function toggleFaturamento(card) {
            let txtEl = document.getElementById('txt-faturamento');
            let realVal = txtEl.getAttribute('data-real');
            if (txtEl.innerText.includes('••••')) {
                txtEl.innerText = realVal;
            } else {
                txtEl.innerText = 'R$ ••••';
            }
        }

        function toggleInputValor() {
            let input = document.getElementById('mod_valor');
            if (input.type === 'password') {
                input.type = 'number';
                input.step = '0.01';
            } else {
                input.type = 'password';
            }
        }

        function filtrarTabela() {
            let input = document.getElementById("buscaInput").value.toLowerCase();
            let linhas = document.querySelectorAll("#tabelaCorpo tr");
            linhas.forEach(linha => {
                linha.style.display = linha.innerText.toLowerCase().includes(input) ? "" : "none";
            });
        }

        function filtrarStatus(status) {
            let botoes = document.querySelectorAll(".filter-btn");
            botoes.forEach(btn => btn.classList.remove("active"));
            event.target.classList.add("active");

            let linhas = document.querySelectorAll("#tabelaCorpo tr");
            linhas.forEach(linha => {
                let statusLinha = linha.getAttribute("data-status-row");
                if(status === 'TODOS' || statusLinha.includes(status)) {
                    linha.style.display = "";
                } else {
                    linha.style.display = "none";
                }
            });
        }

        function abrirModalEdicao(btn) {
            const id = btn.getAttribute('data-id');
            document.getElementById('mod_old_id').value = id;
            document.getElementById('mod_id').value = id;
            document.getElementById('mod_nome').value = btn.getAttribute('data-nome');
            document.getElementById('mod_telefone').value = btn.getAttribute('data-telefone');
            document.getElementById('mod_aparelho').value = btn.getAttribute('data-aparelho');
            document.getElementById('mod_marca').value = btn.getAttribute('data-marca');
            document.getElementById('mod_modelo').value = btn.getAttribute('data-modelo');
            document.getElementById('mod_defeito_relatado').value = btn.getAttribute('data-defeito_relatado');
            document.getElementById('mod_estado_entrada').value = btn.getAttribute('data-estado_entrada');
            document.getElementById('mod_observacao').value = btn.getAttribute('data-observacao');
            
            let defEnc = btn.getAttribute('data-defeito_encontrado');
            document.getElementById('mod_defeito_encontrado').value = (defEnc !== 'None' && defEnc !== 'null') ? defEnc : '';
            
            let tec = btn.getAttribute('data-tecnico');
            document.getElementById('mod_tecnico').value = (tec !== 'None' && tec !== 'null') ? tec : '';
            
            let pçs = btn.getAttribute('data-pecas');
            document.getElementById('mod_pecas').value = (pçs !== 'None' && pçs !== '0.0') ? pçs : '';

            let vlr = btn.getAttribute('data-valor');
            document.getElementById('mod_valor').value = (vlr !== 'None' && vlr !== '0.0') ? vlr : '';
            
            document.getElementById('mod_valor').type = 'password';
            document.getElementById('mod_status').value = btn.getAttribute('data-status');
            
            let saida = btn.getAttribute('data-saida');
            document.getElementById('mod_saida').value = (saida !== 'None' && saida !== 'null') ? saida : '';
            
            document.getElementById('modalEdicao').style.display = 'block';
        }

        function fecharModalEdicao() {
            document.getElementById('modalEdicao').style.display = 'none';
        }
    </script>
</body>
</html>
'''

PRINT_TEMPLATE = '''
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>Recibo OS - Ezetec</title>
    <style>
        body { font-family: 'Courier New', Courier, monospace; width: 100%; max-width: 58mm; padding: 2px; font-size: 11px; margin: 0; color: #000; }
        .center { text-align: center; }
        .bold { font-weight: bold; }
        .line { border-bottom: 1px dashed black; margin: 5px 0; }
        .aviso { font-size: 9px; border: 1px solid black; padding: 4px; margin-top: 8px; text-align: justify; }
        @media print { body { margin: 0; } }
    </style>
</head>
<body onload="window.print()">
    <div class="center">
        <h2 style="margin:0; font-size: 16px;">EZETEC</h2>
        <small>Especialistas em Eletrônica</small>
    </div>
    <div class="line"></div>
    <div><span class="bold">ORDEM DE SERVIÇO:</span> #{{ os.id }}</div>
    <div><span class="bold">ENTRADA:</span> {{ os.data_entrada }}</div>
    {% if os.data_saida %}
    <div><span class="bold">SÁIDA:</span> {{ os.data_saida }}</div>
    {% endif %}
    <div class="line"></div>
    <div><span class="bold">CLIENTE:</span> {{ os.nome }}</div>
    <div><span class="bold">CONTATO:</span> {{ os.telefone }}</div>
    <div class="line"></div>
    <div><span class="bold">APARELHO:</span> {{ os.aparelho }}</div>
    <div><span class="bold">M/M:</span> {{ os.marca }} {{ os.modelo }}</div>
    <div><span class="bold">ESTADO:</span> {{ os.estado_entrada }}</div>
    <div><span class="bold">DEFEITO:</span> {{ os.defeito_relatado }}</div>
    <div class="line"></div>
    <div><span class="bold">SOLUÇÃO:</span> {{ os.defeito_encontrado or 'EM ANÁLISE' }}</div>
    {% if os.tecnico_responsavel %}
    <div><span class="bold">TEC. RESP:</span> {{ os.tecnico_responsavel }}</div>
    {% endif %}
    <div><span class="bold">VALOR TOTAL:</span> R$ {{ "%.2f"|format(os.valor_conserto) if os.valor_conserto else '0.00' }}</div>
    <div class="line"></div>
    <div class="aviso">
        TERMOS: Equipamentos não retirados em até 90 dias após o aviso de conclusão estarão sujeitos a descarte ou venda para cobrir despesas de insumos e armazenamento conforme diretrizes comerciais da loja.
    </div>
    <div class="center" style="margin-top:25px;">
        ___________________________<br>Assinatura Cliente
    </div>
</body>
</html>
'''

# --- CONTROLADORES DO SISTEMA (ROTAS) ---

@app.route('/')
def index():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM ordens_servico ORDER BY id DESC')
    rows = c.fetchall()
    
    ordens = []
    hoje = datetime.now().date()
    stats = {'na_loja': 0, 'faturamento': 0.0, 'entregues': 0, 'alertas': 0}
    
    for row in rows:
        os_dict = dict(row)
        
        # TRATAMENTO AVANÇADO E SEGURO DO NÚMERO DO WHATSAPP
        fone_cru = ''.join(filter(str.isdigit, str(os_dict['telefone'])))
        if fone_cru.startswith('55') and len(fone_cru) >= 12:
            fone_final = fone_cru
        else:
            fone_final = '55' + fone_cru
            
        texto_msg = f"Olá {os_dict['nome']}, aqui é da Ezetec. Passando para trazer uma atualização sobre a sua Ordem de Serviço de número #{os_dict['id']} ({os_dict['aparelho']})."
        texto_codificado = urllib.parse.quote(texto_msg)
        os_dict['zap_link'] = f"https://api.whatsapp.com/send?phone={fone_final}&text={texto_codificado}"
        
        data_entrada = datetime.strptime(os_dict['data_entrada'], '%Y-%m-%d').date()
        os_dict['data_entrada_fmt'] = data_entrada.strftime('%d/%m/%Y')
        
        if os_dict.get('data_saida'):
            try:
                os_dict['data_saida_fmt'] = datetime.strptime(os_dict['data_saida'], '%Y-%m-%d').strftime('%d/%m/%Y')
            except:
                os_dict['data_saida_fmt'] = os_dict['data_saida']
        
        if os_dict['status_retirada'] == 'Na Loja':
            stats['na_loja'] += 1
        elif os_dict['status_retirada'] in ['Entregue', 'Retirado']:
            stats['entregues'] += 1
            stats['faturamento'] += (os_dict['valor_conserto'] or 0.0)
            
        dias_na_loja = (hoje - data_entrada).days
        os_dict['alerta_laranja'] = dias_na_loja >= 90 and os_dict['status_retirada'] in ['Na Loja', 'Abandonado']
        
        if os_dict['alerta_laranja']:
            stats['alertas'] += 1
            
        ordens.append(os_dict)
        
    conn.close()
    return render_template_string(HTML_TEMPLATE, ordens=ordens, stats=stats)

@app.route('/add', methods=['POST'])
def add_os():
    data = request.form
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        INSERT INTO ordens_servico (nome, telefone, aparelho, marca, modelo, defeito_relatado, estado_entrada, observacao, status_retirada, data_entrada)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        data.get('nome'), data.get('telefone'), data.get('aparelho'), data.get('marca'), data.get('modelo'),
        data.get('defeito_relatado'), data.get('estado_entrada', ''), data.get('observacao', ''),
        data.get('status_retirada', 'Na Loja'), datetime.now().strftime('%Y-%m-%d')
    ))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/update', methods=['POST'])
def update_os():
    data = request.form
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    try:
        c.execute('''
            UPDATE ordens_servico 
            SET id = ?, nome = ?, telefone = ?, aparelho = ?, marca = ?, modelo = ?, 
                defeito_relatado = ?, estado_entrada = ?, observacao = ?, 
                defeito_encontrado = ?, valor_conserto = ?, valor_pecas = ?, 
                tecnico_responsavel = ?, status_retirada = ?, data_saida = ?
            WHERE id = ?
        ''', (
            data.get('id'), data.get('nome'), data.get('telefone'), data.get('aparelho'), data.get('marca'), data.get('modelo'),
            data.get('defeito_relatado'), data.get('estado_entrada'), data.get('observacao'),
            data.get('defeito_encontrado'), data.get('valor_conserto') or 0.0, data.get('valor_pecas') or 0.0,
            data.get('tecnico_responsavel'), data.get('status_retirada'), data.get('data_saida') or None, 
            data.get('old_id')
        ))
        conn.commit()
    except sqlite3.IntegrityError:
        flash('Erro: ID já existe ou conflito de integridade.', 'error')
    conn.close()
    return redirect(url_for('index'))

@app.route('/print/<int:os_id>')
def print_os(os_id):
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM ordens_servico WHERE id = ?', (os_id,))
    os_data = c.fetchone()
    conn.close()
    
    if os_data:
        os_dict = dict(os_data)
        os_dict['data_entrada'] = datetime.strptime(os_dict['data_entrada'], '%Y-%m-%d').strftime('%d/%m/%Y')
        if os_dict.get('data_saida'):
            try:
                os_dict['data_saida'] = datetime.strptime(os_dict['data_saida'], '%Y-%m-%d').strftime('%d/%m/%Y')
            except:
                pass
        return render_template_string(PRINT_TEMPLATE, os=os_dict)
    return "OS não localizada", 404

# --- NOVA ROTA DE IMPORTAÇÃO JSON (COMPATÍVEL COM SEU FORMATO) ---
@app.route('/import', methods=['POST'])
def import_json():
    if 'json_file' not in request.files:
        flash('Nenhum arquivo enviado.', 'error')
        return redirect(url_for('index'))

    file = request.files['json_file']
    if file.filename == '':
        flash('Nome de arquivo vazio.', 'error')
        return redirect(url_for('index'))

    if not file.filename.lower().endswith('.json'):
        flash('Formato inválido. Apenas arquivos .json são aceitos.', 'error')
        return redirect(url_for('index'))

    try:
        content = file.read().decode('utf-8')
        data = json.loads(content)
    except Exception as e:
        flash(f'Erro ao ler o JSON: {str(e)}', 'error')
        return redirect(url_for('index'))

    # Se for o formato exportado (com "ordens"), extrai a lista
    if isinstance(data, dict) and 'ordens' in data:
        lista_ordens = data['ordens']
    elif isinstance(data, list):
        lista_ordens = data
    elif isinstance(data, dict):
        lista_ordens = [data]   # objeto único (formato antigo)
    else:
        flash('Formato de JSON não reconhecido.', 'error')
        return redirect(url_for('index'))

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    inseridos = 0
    erros = 0

    for item in lista_ordens:
        if not isinstance(item, dict):
            erros += 1
            continue

        # ---- MAPEAMENTO DO SEU JSON (campos: cliente, whatsapp, aparelho, marca, defeito, etc.) ----
        if 'cliente' in item:   # formato do seu JSON
            nome = item.get('cliente', '').strip()
            # Extrai apenas dígitos do whatsapp
            fone_bruto = item.get('whatsapp', '')
            telefone = re.sub(r'\D', '', fone_bruto)  # remove tudo que não for dígito
            aparelho = item.get('aparelho', '').strip()
            marca = item.get('marca', '').strip()
            modelo = item.get('modelo', '').strip()
            defeito_relatado = item.get('defeito', '').strip()
            observacao = item.get('observacoes', '').strip()
            servico = item.get('servico', '').strip()
            valor_str = item.get('valorTotal', '0').replace(',', '.')
            try:
                valor_conserto = float(valor_str)
            except:
                valor_conserto = 0.0

            status_orig = item.get('status', 'Aberta').strip()
            # Mapeamento de status
            status_map = {
                'Aberta': 'Na Loja',
                'Em Andamento': 'Na Loja',
                'Aguardando': 'Na Loja',
                'Finalizada': 'Entregue',
                'Cancelada': 'Abandonado'
            }
            status_retirada = status_map.get(status_orig, 'Na Loja')

            # Data de entrada (createdAt)
            data_entrada = None
            raw_date = item.get('createdAt', '')
            try:
                # Converte ISO para date
                dt = datetime.fromisoformat(raw_date.replace('Z', '+00:00'))
                data_entrada = dt.strftime('%Y-%m-%d')
            except:
                data_entrada = datetime.now().strftime('%Y-%m-%d')

            # Se tiver número OS original, guarda na observação
            num_original = item.get('numero', '')
            if num_original:
                observacao = f"OS Original: {num_original} | " + observacao

            # Se tiver serviço, coloca em defeito_encontrado
            defeito_encontrado = servico if servico else ''

            # Monta tupla para inserção (sem forçar ID)
            try:
                c.execute('''
                    INSERT INTO ordens_servico
                    (nome, telefone, aparelho, marca, modelo, defeito_relatado, estado_entrada, observacao,
                     defeito_encontrado, valor_conserto, status_retirada, data_entrada)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (nome, telefone, aparelho, marca, modelo, defeito_relatado, '', observacao,
                      defeito_encontrado, valor_conserto, status_retirada, data_entrada))
                inseridos += 1
            except Exception as e:
                erros += 1

        else:
            # Formato antigo (objetos com nome, telefone, etc.)
            nome = item.get('nome', '').strip()
            telefone = item.get('telefone', '').strip()
            aparelho = item.get('aparelho', '').strip()
            defeito = item.get('defeito_relatado', '').strip()
            if not nome or not telefone or not aparelho or not defeito:
                erros += 1
                continue

            marca = item.get('marca', '').strip()
            modelo = item.get('modelo', '').strip()
            estado = item.get('estado_entrada', '').strip()
            obs = item.get('observacao', '').strip()
            status = item.get('status_retirada', 'Na Loja').strip()
            data_entrada = item.get('data_entrada', datetime.now().strftime('%Y-%m-%d')).strip()
            try:
                datetime.strptime(data_entrada, '%Y-%m-%d')
            except:
                data_entrada = datetime.now().strftime('%Y-%m-%d')

            try:
                c.execute('''
                    INSERT INTO ordens_servico
                    (nome, telefone, aparelho, marca, modelo, defeito_relatado, estado_entrada, observacao, status_retirada, data_entrada)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (nome, telefone, aparelho, marca, modelo, defeito, estado, obs, status, data_entrada))
                inseridos += 1
            except:
                erros += 1

    conn.commit()
    conn.close()

    flash(f'Importação concluída: {inseridos} ordens inseridas, {erros} ignoradas/erros.', 'success')
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)