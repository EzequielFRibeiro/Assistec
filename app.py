from flask import Flask, request, render_template_string, redirect, url_for, flash, session
from datetime import datetime
import json
import re
import hashlib
from db import query, execute, init_tables, load_users, IntegrityError

app = Flask(__name__)
app.secret_key = 'ezetec_super_secret_key_2025'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max upload

init_tables()

# --- TEMPLATE INTERFACE PREMIUM (UI/UX) ---
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="pt-BR" data-theme="light">
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

        /* TEMA ESCURO */
        [data-theme="dark"] {
            --primary: #8ab4f8;
            --primary-hover: #aecbfa;
            --bg-main: #121212;
            --card-bg: #1e1e1e;
            --text-dark: #e0e0e0;
            --text-muted: #b0b0b0;
            --border-color: #3c4043;
            --status-loja: #1a3a5c; --status-loja-txt: #8ab4f8;
            --status-entregue: #1b3b1b; --status-entregue-txt: #81c784;
            --status-abandonado: #3b1b1b; --status-abandonado-txt: #f28b82;
            --status-retirado: #3b3a1a; --status-retirado-txt: #fdd663;
            --status-vendido: #3b1b3b; --status-vendido-txt: #ce93d8;
        }

        body { font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: var(--bg-main); color: var(--text-dark); margin: 0; padding: 25px; transition: background-color 0.3s, color 0.3s; }
        header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 25px; border-bottom: 1px solid var(--border-color); padding-bottom: 15px; }
        header h1 { margin: 0; font-size: 24px; color: var(--primary); display: flex; align-items: center; gap: 10px; }
        
        .dashboard { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 25px; }
        .card-stat { background: var(--card-bg); padding: 15px 20px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); border-left: 4px solid var(--primary); transition: background 0.2s; }
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
        input, select, textarea { padding: 10px 12px; border: 1px solid var(--border-color); border-radius: 6px; font-size: 14px; box-sizing: border-box; background: var(--card-bg); color: var(--text-dark); }
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
        .search-box input { border: 2px solid var(--primary); border-radius: 6px; padding: 10px; font-size: 14px; width: 100%; background: var(--card-bg); color: var(--text-dark); }
        
        .status-filters { display: flex; gap: 5px; }
        .filter-btn { padding: 6px 12px; border: 1px solid var(--border-color); background: var(--card-bg); border-radius: 20px; font-size: 12px; font-weight: bold; cursor: pointer; color: var(--text-dark); }
        .filter-btn.active { background: var(--primary); color: white; border-color: var(--primary); }

        .table-container { overflow-x: auto; max-height: 550px; border: 1px solid var(--border-color); border-radius: 6px; }
        table { width: 100%; border-collapse: collapse; font-size: 13px; }
        th, td { padding: 12px; border-bottom: 1px solid var(--border-color); text-align: left; color: var(--text-dark); }
        th { background-color: #f1f3f4; color: var(--text-dark); font-weight: 600; position: sticky; top: 0; z-index: 10; }
        [data-theme="dark"] th { background-color: #2c2c2c; }
        tr:hover { background-color: rgba(0,0,0,0.05); }
        [data-theme="dark"] tr:hover { background-color: rgba(255,255,255,0.05); }
        
        .alerta-laranja { background-color: #fff3e0 !important; }
        [data-theme="dark"] .alerta-laranja { background-color: #3a2e1a !important; }
        
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
        .modal-content { background: var(--card-bg); margin: 2% auto; padding: 25px; width: 90%; max-width: 650px; border-radius: 8px; box-shadow: 0 4px 24px rgba(0,0,0,0.15); max-height: 90vh; overflow-y: auto; color: var(--text-dark); }
        
        .flash-messages { margin-bottom: 15px; }
        .flash-msg { padding: 10px 15px; border-radius: 6px; margin-bottom: 8px; font-weight: bold; }
        .flash-success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
        .flash-error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
        
        /* Botão de alternância de tema */
        #themeToggle { background: var(--card-bg); color: var(--text-dark); border: 1px solid var(--border-color); padding: 8px 16px; border-radius: 20px; cursor: pointer; font-size: 16px; display: flex; align-items: center; gap: 6px; transition: all 0.3s; }
        #themeToggle:hover { border-color: var(--primary); color: var(--primary); }
        
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
            <button id="themeToggle" onclick="toggleTheme()">🌙 Modo Noturno</button>
            <a href="/backup/download" class="btn-primary" style="width: auto; padding: 8px 20px; background: #0f9d58; text-decoration: none;">📥 Baixar Backup</a>
            <button class="btn-primary" style="width: auto; padding: 8px 20px; background: #4285f4;" onclick="document.getElementById('modalImport').style.display='block'">📤 Importar</button>
            <button class="btn-primary" style="width: auto; padding: 8px 20px; background: #f4b400; color: #202124;" onclick="document.getElementById('modalRestore').style.display='block'">🔄 Restaurar</button>
            <div style="font-size: 13px; color: var(--text-muted); display: flex; align-items: center; gap: 8px;">
                <span>👤 {{ session['username'] }}</span>
                {% if session.get('role') == 'admin' %}
                <a href="/manage_users" style="color: var(--primary); text-decoration: none; font-weight: 600;">👥 Usuários</a>
                {% endif %}
                <a href="/logout" style="color: #c5221f; text-decoration: none; font-weight: 600;">🚪 Sair</a>
            </div>
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
                                <button type="button" class="btn-zap" onclick="abrirModalWhatsApp(this)" data-telefone="{{ os.telefone }}" data-nome="{{ os.nome }}" data-id="{{ os.id }}" data-msg="{{ os.msg_padrao }}">Zap</button>
                                <button type="button" class="btn-edit" 
                                    data-id="{{ os.id }}" data-nome="{{ os.nome }}" data-telefone="{{ os.telefone }}"
                                    data-aparelho="{{ os.aparelho }}" data-marca="{{ os.marca }}" data-modelo="{{ os.modelo }}"
                                    data-defeito_relatado="{{ os.defeito_relatado }}" data-estado_entrada="{{ os.estado_entrada }}"
                                    data-observacao="{{ os.observacao }}" data-defeito_encontrado="{{ os.defeito_encontrado }}"
                                    data-valor="{{ os.valor_conserto }}" data-pecas="{{ os.valor_pecas }}"
                                    data-tecnico="{{ os.tecnico_responsavel }}" data-status="{{ os.status_retirada }}"
                                    data-data_entrada="{{ os.data_entrada_fmt }}" data-saida="{{ os.data_saida }}" onclick="abrirModalEdicao(this)">Editar</button>
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
                    <label>Data de Entrada</label>
                    <input type="date" name="data_entrada" id="mod_data_entrada">
                </div>
                <div class="form-group">
                    <label>Data de Saída</label>
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
                    <input type="text" name="defeito_encontrado" id="mod_defeito_encontrado">
                </div>
                <div class="form-group">
                    <label>Valor da Mão de Obra (R$)</label>
                    <input type="number" step="0.01" name="valor_conserto" id="mod_valor">
                </div>
                <div class="form-group">
                    <label>Valor das Peças (R$)</label>
                    <input type="number" step="0.01" name="valor_pecas" id="mod_pecas">
                </div>
                <div class="form-group full-width">
                    <label>Técnico Responsável</label>
                    <input type="text" name="tecnico_responsavel" id="mod_tecnico">
                </div>
                <div class="form-group full-width">
                    <button type="submit" class="btn-primary">ATUALIZAR ORDEM DE SERVIÇO</button>
                </div>
                <div class="form-group full-width">
                    <button type="button" class="btn-primary" style="background: #c5221f;" onclick="confirmarExclusao()">🗑️ EXCLUIR ORDEM DE SERVIÇO</button>
                </div>
            </form>
        </div>
    </div>

    <!-- MODAL DE IMPORTAÇÃO JSON -->
    <div id="modalImport" class="modal">
        <div class="modal-content">
            <h3>Importar Dados via JSON</h3>
            <p style="color: var(--text-muted); font-size: 13px; margin-bottom: 15px;">
                Aceita formatos antigos e novos. O sistema detecta automaticamente.
            </p>
            <form action="/import" method="POST">
                <div class="form-group">
                    <label>Cole o JSON aqui:</label>
                    <textarea name="json_data" class="fixed-size" style="height:150px;" placeholder='Cole o JSON de qualquer formato...'></textarea>
                </div>
                <button type="submit" class="btn-primary">IMPORTAR</button>
                <button type="button" class="btn-primary" style="background:#5f6368; margin-top:10px;" onclick="document.getElementById('modalImport').style.display='none'">Cancelar</button>
            </form>
        </div>
    </div>

    <!-- MODAL WHATSAPP -->
    <div id="modalWhatsApp" class="modal">
        <div class="modal-content">
            <h3 style="border-bottom: 2px solid #25d366; padding-bottom: 8px; margin-top:0;">💬 Mensagem WhatsApp</h3>
            <div class="form-group">
                <label>Edite a mensagem antes de enviar:</label>
                <textarea id="whatsapp_msg" class="fixed-size" style="height:120px; resize:vertical;"></textarea>
            </div>
            <div style="display: flex; gap: 10px;">
                <button type="button" class="btn-primary" style="background: #25d366;" onclick="enviarWhatsApp()">📤 Enviar via WhatsApp</button>
                <button type="button" class="btn-primary" style="background: #5f6368;" onclick="document.getElementById('modalWhatsApp').style.display='none'">Cancelar</button>
            </div>
        </div>
    </div>

    <!-- MODAL RESTAURAR BACKUP -->
    <div id="modalRestore" class="modal">
        <div class="modal-content">
            <h3 style="border-bottom: 2px solid #f4b400; padding-bottom: 8px; margin-top:0;">🔄 Restaurar Backup</h3>
            <p style="color: var(--text-muted); font-size: 13px; margin-bottom: 15px;">
                Aceita arquivos JSON de qualquer formato (backup antigo, exportação de outros sistemas, etc.).
                O sistema detecta automaticamente o formato e mapeia os campos.
            </p>
            <form action="/restore" method="POST" enctype="multipart/form-data">
                <div class="form-group">
                    <label>Selecione o arquivo JSON:</label>
                    <input type="file" name="backup_file" accept=".json" required style="padding: 10px;">
                </div>
                <div style="display: flex; gap: 10px;">
                    <button type="submit" class="btn-primary" style="background: #f4b400; color: #202124;">🔄 RESTAURAR</button>
                    <button type="button" class="btn-primary" style="background:#5f6368;" onclick="document.getElementById('modalRestore').style.display='none'">Cancelar</button>
                </div>
            </form>
        </div>
    </div>

    <script>
        // ---------- FUNÇÃO PÁGINA NOTURNA ----------
        function toggleTheme() {
            const html = document.documentElement;
            const btn = document.getElementById('themeToggle');
            if (html.getAttribute('data-theme') === 'dark') {
                html.setAttribute('data-theme', 'light');
                btn.innerHTML = '🌙 Modo Noturno';
                localStorage.setItem('ezetec_theme', 'light');
            } else {
                html.setAttribute('data-theme', 'dark');
                btn.innerHTML = '☀️ Modo Claro';
                localStorage.setItem('ezetec_theme', 'dark');
            }
        }

        // Aplica tema salvo ao carregar
        (function() {
            const savedTheme = localStorage.getItem('ezetec_theme') || 'light';
            document.documentElement.setAttribute('data-theme', savedTheme);
            const btn = document.getElementById('themeToggle');
            if (savedTheme === 'dark') {
                btn.innerHTML = '☀️ Modo Claro';
            } else {
                btn.innerHTML = '🌙 Modo Noturno';
            }
        })();

        // ---------- DEMAIS SCRIPTS ----------
        function toggleFaturamento(el) {
            const txt = el.querySelector('#txt-faturamento');
            const isHidden = txt.innerText.includes('••••');
            if (isHidden) {
                txt.innerText = txt.dataset.real;
            } else {
                txt.innerText = 'R$ ••••';
            }
        }

        function filtrarTabela() {
            const input = document.getElementById('buscaInput');
            const filter = input.value.toUpperCase();
            const rows = document.querySelectorAll('#tabelaCorpo tr');
            rows.forEach(row => {
                const text = row.innerText.toUpperCase();
                row.style.display = text.includes(filter) ? '' : 'none';
            });
        }

        function filtrarStatus(status) {
            const buttons = document.querySelectorAll('.filter-btn');
            buttons.forEach(btn => btn.classList.remove('active'));
            event.target.classList.add('active');

            const rows = document.querySelectorAll('#tabelaCorpo tr');
            rows.forEach(row => {
                const rowStatus = row.dataset.statusRow;
                if (status === 'TODOS' || rowStatus === status || (status === 'Vendido' && rowStatus.includes('Vendido'))) {
                    row.style.display = '';
                } else {
                    row.style.display = 'none';
                }
            });
        }

        function abrirModalEdicao(btn) {
            document.getElementById('mod_old_id').value = btn.dataset.id;
            document.getElementById('mod_id').value = btn.dataset.id;
            document.getElementById('mod_nome').value = btn.dataset.nome;
            document.getElementById('mod_telefone').value = btn.dataset.telefone;
            document.getElementById('mod_aparelho').value = btn.dataset.aparelho;
            document.getElementById('mod_marca').value = btn.dataset.marca;
            document.getElementById('mod_modelo').value = btn.dataset.modelo;
            document.getElementById('mod_defeito_relatado').value = btn.dataset.defeito_relatado;
            document.getElementById('mod_estado_entrada').value = btn.dataset.estado_entrada;
            document.getElementById('mod_observacao').value = btn.dataset.observacao;
            document.getElementById('mod_defeito_encontrado').value = btn.dataset.defeito_encontrado;
            document.getElementById('mod_valor').value = btn.dataset.valor;
            document.getElementById('mod_pecas').value = btn.dataset.pecas;
            document.getElementById('mod_tecnico').value = btn.dataset.tecnico;
            document.getElementById('mod_status').value = btn.dataset.status;
            document.getElementById('mod_data_entrada').value = btn.dataset.data_entrada;
            document.getElementById('mod_saida').value = btn.dataset.saida;
            document.getElementById('modalEdicao').style.display = 'block';
        }

        // ---------- WHATSAPP ----------
        var whatsappTelefone = '';
        function abrirModalWhatsApp(btn) {
            whatsappTelefone = btn.dataset.telefone;
            document.getElementById('whatsapp_msg').value = btn.dataset.msg;
            document.getElementById('modalWhatsApp').style.display = 'block';
        }
        function enviarWhatsApp() {
            const msg = document.getElementById('whatsapp_msg').value;
            const telLimpo = whatsappTelefone.replace(/\\D/g, '');
            const url = 'https://wa.me/55' + telLimpo + '?text=' + encodeURIComponent(msg);
            window.open(url, '_blank');
            document.getElementById('modalWhatsApp').style.display = 'none';
        }

        // ---------- EXCLUIR ----------
        function confirmarExclusao() {
            const id = document.getElementById('mod_old_id').value;
            if (confirm('Tem certeza que deseja excluir a OS #' + id + '? Esta ação não pode ser desfeita.')) {
                var form = document.createElement('form');
                form.method = 'POST';
                form.action = '/delete/' + id;
                document.body.appendChild(form);
                form.submit();
            }
        }

        // Fecha modais ao clicar fora
        window.onclick = function(event) {
            if (event.target.classList.contains('modal')) {
                event.target.style.display = 'none';
            }
        }
    </script>
</body>
</html>
'''

# --- TEMPLATE DE LOGIN ---
LOGIN_HTML = '''
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Ezetec Pro - Login</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Roboto, Arial, sans-serif;
            background: linear-gradient(135deg, #1a73e8, #0d47a1);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .login-card {
            background: white;
            border-radius: 16px;
            padding: 40px;
            width: 400px;
            max-width: 90vw;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }
        .login-card h1 {
            color: #1a73e8;
            font-size: 24px;
            text-align: center;
            margin-bottom: 8px;
        }
        .login-card .subtitle {
            color: #5f6368;
            text-align: center;
            margin-bottom: 30px;
            font-size: 14px;
        }
        .form-group { margin-bottom: 20px; }
        .form-group label {
            display: block;
            font-size: 13px;
            font-weight: 600;
            color: #202124;
            margin-bottom: 6px;
        }
        .form-group input {
            width: 100%;
            padding: 12px 14px;
            border: 2px solid #dadce0;
            border-radius: 8px;
            font-size: 14px;
            transition: border-color 0.2s;
        }
        .form-group input:focus {
            border-color: #1a73e8;
            outline: none;
        }
        button {
            width: 100%;
            padding: 14px;
            background: #1a73e8;
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 15px;
            font-weight: bold;
            cursor: pointer;
            transition: background 0.2s;
        }
        button:hover { background: #1557b0; }
        .flash-msg {
            padding: 10px 15px;
            border-radius: 6px;
            margin-bottom: 15px;
            font-weight: bold;
            text-align: center;
        }
        .flash-success { background: #d4edda; color: #155724; }
        .flash-error { background: #f8d7da; color: #721c24; }
    </style>
</head>
<body>
    <div class="login-card">
        <h1>Ezetec Pro</h1>
        <div class="subtitle">Sistema de Gestão de Assistência</div>
        {% with messages = get_flashed_messages(with_categories=true) %}
          {% if messages %}
            {% for category, message in messages %}
              <div class="flash-msg flash-{{ category }}">{{ message }}</div>
            {% endfor %}
          {% endif %}
        {% endwith %}
        <form method="POST">
            <div class="form-group">
                <label>Usuário</label>
                <input type="text" name="username" placeholder="Digite seu usuário" required autofocus>
            </div>
            <div class="form-group">
                <label>Senha</label>
                <input type="password" name="password" placeholder="Digite sua senha" required>
            </div>
            <button type="submit">ENTRAR</button>
        </form>
    </div>
</body>
</html>
'''

# --- TEMPLATE DE GERENCIAMENTO DE USUÁRIOS ---
USERS_HTML = '''
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Ezetec Pro - Usuários</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Roboto, Arial, sans-serif;
            background: #f8f9fa;
            padding: 30px;
            color: #202124;
        }
        .container { max-width: 700px; margin: 0 auto; }
        h1 { color: #1a73e8; margin-bottom: 8px; }
        .subtitle { color: #5f6368; margin-bottom: 25px; }
        .card {
            background: white;
            border-radius: 8px;
            padding: 25px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        .card h2 {
            font-size: 18px;
            margin-bottom: 15px;
            padding-bottom: 8px;
            border-bottom: 2px solid #1a73e8;
        }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 10px 12px; border-bottom: 1px solid #dadce0; text-align: left; }
        th { background: #f1f3f4; font-weight: 600; }
        .form-group { margin-bottom: 15px; }
        .form-group label { display: block; font-size: 13px; font-weight: 600; margin-bottom: 5px; }
        .form-group input {
            width: 100%; padding: 10px 12px;
            border: 1px solid #dadce0; border-radius: 6px; font-size: 14px;
        }
        .btn {
            padding: 10px 20px; border: none; border-radius: 6px;
            font-weight: bold; cursor: pointer; font-size: 14px;
        }
        .btn-primary { background: #1a73e8; color: white; }
        .btn-primary:hover { background: #1557b0; }
        .btn-secondary { background: #5f6368; color: white; text-decoration: none; display: inline-block; }
        .flash-msg {
            padding: 10px 15px; border-radius: 6px; margin-bottom: 15px; font-weight: bold;
        }
        .flash-success { background: #d4edda; color: #155724; }
        .flash-error { background: #f8d7da; color: #721c24; }
        .top-bar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 25px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="top-bar">
            <div>
                <h1>Gerenciar Usuários</h1>
                <div class="subtitle">Administração do sistema Ezetec Pro</div>
            </div>
            <a href="/" class="btn btn-secondary" style="padding: 8px 16px;">Voltar</a>
        </div>
        {% with messages = get_flashed_messages(with_categories=true) %}
          {% if messages %}
            {% for category, message in messages %}
              <div class="flash-msg flash-{{ category }}">{{ message }}</div>
            {% endfor %}
          {% endif %}
        {% endwith %}
        <div class="card">
            <h2>Usuários Cadastrados</h2>
            <table>
                <thead>
                    <tr><th>Usuário</th><th>Função</th></tr>
                </thead>
                <tbody>
                    {% for user, data in users.items() %}
                    <tr>
                        <td>{{ user }}</td>
                        <td>{% if data.role == 'admin' %}Administrador{% else %}Operador{% endif %}</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
        <div class="card">
            <h2>Adicionar Novo Usuário</h2>
            <form method="POST">
                <div class="form-group">
                    <label>Nome de Usuário</label>
                    <input type="text" name="username" placeholder="Ex: operador1" required>
                </div>
                <div class="form-group">
                    <label>Senha</label>
                    <input type="password" name="password" placeholder="Mínimo 4 caracteres" required minlength="4">
                </div>
                <button type="submit" class="btn btn-primary">CRIAR USUÁRIO</button>
            </form>
        </div>
    </div>
</body>
</html>
'''

# --- FUNÇÃO DE MAPEAMENTO DE FORMATOS DE BACKUP ---
def map_ordem_record(reg):
    """Detecta automaticamente o formato do registro e mapeia para o schema atual."""
    mapeado = {}
    
    # Formato novo (nome/telefone) - retorna direto
    if 'nome' in reg and 'telefone' in reg:
        mapeado = {
            'nome': reg.get('nome', 'Sem nome'),
            'telefone': reg.get('telefone', ''),
            'aparelho': reg.get('aparelho', ''),
            'marca': reg.get('marca', ''),
            'modelo': reg.get('modelo', ''),
            'defeito_relatado': reg.get('defeito_relatado', reg.get('defeito', '')),
            'estado_entrada': reg.get('estado_entrada', ''),
            'observacao': reg.get('observacao', reg.get('observacoes', '')),
            'defeito_encontrado': reg.get('defeito_encontrado', reg.get('servico', '')),
            'valor_conserto': reg.get('valor_conserto', reg.get('maoDeObra', 0)),
            'valor_pecas': reg.get('valor_pecas', 0),
            'tecnico_responsavel': reg.get('tecnico_responsavel', ''),
            'status_retirada': reg.get('status_retirada', 'Na Loja'),
            'data_entrada': reg.get('data_entrada', datetime.now().strftime('%Y-%m-%d')),
            'data_saida': reg.get('data_saida', '')
        }
        return mapeado
    
    # Formato antigo (cliente/whatsapp)
    if 'cliente' in reg:
        status = reg.get('status', 'Aberta')
        status_map = {'Aberta': 'Na Loja', 'Fechada': 'Entregue', 'Entregue': 'Entregue',
                      'Cancelada': 'Abandonado', 'Na Loja': 'Na Loja'}
        data_raw = reg.get('createdAt', '')
        data_entrada = data_raw[:10] if data_raw and len(data_raw) >= 10 else datetime.now().strftime('%Y-%m-%d')
        
        valor = reg.get('maoDeObra', '0') or reg.get('valorTotal', '0') or '0'
        try:
            valor = float(valor.replace('R$', '').replace(',', '.').strip())
        except (ValueError, AttributeError):
            valor = 0.0
        
        telefone = reg.get('whatsapp', '')
        telefone = re.sub(r'\D', '', telefone)
        
        mapeado = {
            'nome': reg.get('cliente', 'Sem nome'),
            'telefone': telefone,
            'aparelho': reg.get('aparelho', ''),
            'marca': reg.get('marca', ''),
            'modelo': reg.get('modelo', ''),
            'defeito_relatado': reg.get('defeito', reg.get('defeito_relatado', '')),
            'estado_entrada': reg.get('estado_entrada', ''),
            'observacao': reg.get('observacoes', reg.get('observacao', '')),
            'defeito_encontrado': reg.get('servico', reg.get('defeito_encontrado', '')),
            'valor_conserto': valor,
            'valor_pecas': 0.0,
            'tecnico_responsavel': reg.get('tecnico_responsavel', ''),
            'status_retirada': status_map.get(status, 'Na Loja'),
            'data_entrada': data_entrada,
            'data_saida': ''
        }
        return mapeado
    
    # Fallback: tenta usar o que tiver disponível
    mapeado = {
        'nome': reg.get('nome', reg.get('cliente', reg.get('nome_cliente', 'Sem nome'))),
        'telefone': reg.get('telefone', reg.get('whatsapp', reg.get('tel', reg.get('fone', '')))),
        'aparelho': reg.get('aparelho', reg.get('equipamento', reg.get('produto', ''))),
        'marca': reg.get('marca', ''),
        'modelo': reg.get('modelo', ''),
        'defeito_relatado': reg.get('defeito_relatado', reg.get('defeito', reg.get('problema', ''))),
        'estado_entrada': reg.get('estado_entrada', reg.get('avarias', '')),
        'observacao': reg.get('observacao', reg.get('observacoes', reg.get('obs', ''))),
        'defeito_encontrado': reg.get('defeito_encontrado', reg.get('servico', reg.get('diagnostico', ''))),
        'valor_conserto': reg.get('valor_conserto', reg.get('maoDeObra', reg.get('valor', 0))),
        'valor_pecas': reg.get('valor_pecas', reg.get('pecas', 0)),
        'tecnico_responsavel': reg.get('tecnico_responsavel', reg.get('tecnico', '')),
        'status_retirada': reg.get('status_retirada', reg.get('status', 'Na Loja')),
        'data_entrada': reg.get('data_entrada', reg.get('createdAt', reg.get('data', datetime.now().strftime('%Y-%m-%d')))),
        'data_saida': reg.get('data_saida', reg.get('updatedAt', ''))
    }
    # Limpar data_entrada (pegar só YYYY-MM-DD)
    de = mapeado['data_entrada']
    if de and isinstance(de, str) and len(de) >= 10:
        mapeado['data_entrada'] = de[:10]
    elif not de:
        mapeado['data_entrada'] = datetime.now().strftime('%Y-%m-%d')
    
    return mapeado


def detectar_registros(data):
    """Extrai lista de registros de qualquer formato de backup."""
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        if 'ordens' in data:
            return data['ordens']
        if 'ordens_servico' in data:
            return data['ordens_servico']
        if 'clientes' in data:
            return data['clientes']
        for v in data.values():
            if isinstance(v, list):
                return v
    return []


# --- ROTAS DO SISTEMA ---
@app.route('/')
def index():
    rows = query("SELECT * FROM ordens_servico ORDER BY id DESC")
    
    ordens = []
    hoje = datetime.now().date()
    stats = {'na_loja': 0, 'entregues': 0, 'alertas': 0, 'faturamento': 0.0}
    
    for r in rows:
        data_entrada = datetime.strptime(r['data_entrada'], '%Y-%m-%d').date() if r['data_entrada'] else hoje
        dias = (hoje - data_entrada).days
        alerta = r['status_retirada'] == 'Na Loja' and dias > 90
        
        if r['status_retirada'] == 'Na Loja':
            stats['na_loja'] += 1
            if dias > 90:
                stats['alertas'] += 1
        elif r['status_retirada'] in ('Entregue', 'Retirado'):
            stats['entregues'] += 1
            if r['valor_conserto']:
                stats['faturamento'] += float(r['valor_conserto'])
            if r['valor_pecas']:
                stats['faturamento'] += float(r['valor_pecas'])
        elif r['status_retirada'] == 'Vendido para a loja':
            stats['entregues'] += 1
            if r['valor_conserto']:
                stats['faturamento'] += float(r['valor_conserto'])
            if r['valor_pecas']:
                stats['faturamento'] += float(r['valor_pecas'])
        
        # Link WhatsApp
        tel_limpo = re.sub(r'\D', '', r['telefone'])
        msg_padrao = f"Olá {r['nome'].split()[0]}, aqui é da Ezetec sobre sua OS #{r['id']}."
        
        ordens.append({
            'id': r['id'],
            'nome': r['nome'],
            'telefone': r['telefone'],
            'aparelho': r['aparelho'],
            'marca': r['marca'] or '',
            'modelo': r['modelo'] or '',
            'defeito_relatado': r['defeito_relatado'],
            'estado_entrada': r['estado_entrada'] or '',
            'observacao': r['observacao'] or '',
            'defeito_encontrado': r['defeito_encontrado'] or '',
            'valor_conserto': r['valor_conserto'] or 0.0,
            'valor_pecas': r['valor_pecas'] or 0.0,
            'tecnico_responsavel': r['tecnico_responsavel'] or '',
            'status_retirada': r['status_retirada'] or 'Na Loja',
            'data_entrada_fmt': r['data_entrada'],
            'data_saida': r['data_saida'] or '',
            'alerta_laranja': alerta,
            'msg_padrao': msg_padrao
        })
    
    return render_template_string(HTML_TEMPLATE, ordens=ordens, stats=stats)

@app.route('/add', methods=['POST'])
def add():
    nome = request.form['nome']
    telefone = request.form['telefone']
    aparelho = request.form['aparelho']
    marca = request.form.get('marca', '')
    modelo = request.form.get('modelo', '')
    defeito_relatado = request.form['defeito_relatado']
    estado_entrada = request.form.get('estado_entrada', '')
    observacao = request.form.get('observacao', '')
    status_retirada = request.form.get('status_retirada', 'Na Loja')
    data_entrada = datetime.now().strftime('%Y-%m-%d')

    execute('''INSERT INTO ordens_servico 
        (nome, telefone, aparelho, marca, modelo, defeito_relatado, estado_entrada, observacao, status_retirada, data_entrada)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        (nome, telefone, aparelho, marca, modelo, defeito_relatado, estado_entrada, observacao, status_retirada, data_entrada))
    flash('Ordem de serviço cadastrada com sucesso!', 'success')
    return redirect(url_for('index'))

@app.route('/update', methods=['POST'])
def update():
    old_id = request.form['old_id']
    new_id = request.form['id']
    nome = request.form['nome']
    telefone = request.form['telefone']
    aparelho = request.form['aparelho']
    marca = request.form.get('marca', '')
    modelo = request.form.get('modelo', '')
    defeito_relatado = request.form['defeito_relatado']
    estado_entrada = request.form.get('estado_entrada', '')
    observacao = request.form.get('observacao', '')
    defeito_encontrado = request.form.get('defeito_encontrado', '')
    valor_conserto = request.form.get('valor_conserto', '0')
    valor_pecas = request.form.get('valor_pecas', '0')
    tecnico = request.form.get('tecnico_responsavel', '')
    status_retirada = request.form.get('status_retirada', 'Na Loja')
    data_entrada = request.form.get('data_entrada', '')
    data_saida = request.form.get('data_saida', '')

    try:
        execute('''UPDATE ordens_servico SET 
            id=?, nome=?, telefone=?, aparelho=?, marca=?, modelo=?, defeito_relatado=?,
            estado_entrada=?, observacao=?, defeito_encontrado=?, valor_conserto=?, valor_pecas=?,
            tecnico_responsavel=?, status_retirada=?, data_entrada=?, data_saida=?
            WHERE id=?''',
            (new_id, nome, telefone, aparelho, marca, modelo, defeito_relatado,
             estado_entrada, observacao, defeito_encontrado, valor_conserto, valor_pecas,
             tecnico, status_retirada, data_entrada, data_saida, old_id))
        flash('Ordem de serviço atualizada!', 'success')
    except IntegrityError:
        flash('Erro: ID já existe. Escolha outro número.', 'error')
    return redirect(url_for('index'))

@app.route('/import', methods=['POST'])
def import_json():
    data = request.form.get('json_data', '')
    try:
        parsed = json.loads(data)
        registros = detectar_registros(parsed)
        if not registros:
            flash('Nenhum registro encontrado no JSON.', 'error')
            return redirect(url_for('index'))
        
        inseridos = 0
        for reg in registros:
            m = map_ordem_record(reg)
            execute('''INSERT INTO ordens_servico 
                (nome, telefone, aparelho, marca, modelo, defeito_relatado, estado_entrada, observacao,
                 status_retirada, data_entrada, defeito_encontrado, valor_conserto, valor_pecas,
                 tecnico_responsavel, data_saida)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (m['nome'], m['telefone'], m['aparelho'], m['marca'], m['modelo'],
                 m['defeito_relatado'], m['estado_entrada'], m['observacao'],
                 m['status_retirada'], m['data_entrada'], m['defeito_encontrado'],
                 m['valor_conserto'], m['valor_pecas'], m['tecnico_responsavel'], m['data_saida']))
            inseridos += 1
        
        flash(f'{inseridos} registros importados com sucesso! (formato detectado automaticamente)', 'success')
    except Exception as e:
        flash(f'Erro na importação: {str(e)}', 'error')
    return redirect(url_for('index'))

@app.route('/restore', methods=['POST'])
def restore_backup():
    if 'backup_file' not in request.files:
        flash('Nenhum arquivo enviado.', 'error')
        return redirect(url_for('index'))
    
    file = request.files['backup_file']
    if file.filename == '':
        flash('Nenhum arquivo selecionado.', 'error')
        return redirect(url_for('index'))
    
    try:
        content = file.read().decode('utf-8')
        parsed = json.loads(content)
        registros = detectar_registros(parsed)
        
        if not registros:
            flash('Nenhum registro encontrado no arquivo.', 'error')
            return redirect(url_for('index'))
        
        inseridos = 0
        erros = 0
        for reg in registros:
            try:
                m = map_ordem_record(reg)
                execute('''INSERT INTO ordens_servico 
                    (nome, telefone, aparelho, marca, modelo, defeito_relatado, estado_entrada, observacao,
                     status_retirada, data_entrada, defeito_encontrado, valor_conserto, valor_pecas,
                     tecnico_responsavel, data_saida)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                    (m['nome'], m['telefone'], m['aparelho'], m['marca'], m['modelo'],
                     m['defeito_relatado'], m['estado_entrada'], m['observacao'],
                     m['status_retirada'], m['data_entrada'], m['defeito_encontrado'],
                     m['valor_conserto'], m['valor_pecas'], m['tecnico_responsavel'], m['data_saida']))
                inseridos += 1
            except Exception:
                erros += 1
        
        nome_arquivo = file.filename
        flash(f'Backup "{nome_arquivo}" restaurado: {inseridos} registros importados' +
              (f', {erros} erros' if erros else '') + '!', 'success')
    except Exception as e:
        flash(f'Erro ao restaurar backup: {str(e)}', 'error')
    return redirect(url_for('index'))

@app.route('/backup/download')
def backup_download():
    rows = query("SELECT * FROM ordens_servico ORDER BY id")
    usuarios = load_users()
    data = {
        'ordens': [dict(r) for r in rows],
        'usuarios': usuarios,
        'version': 1
    }
    return (json.dumps(data, indent=2, ensure_ascii=False),
            200,
            {'Content-Type': 'application/json',
             'Content-Disposition': f'attachment; filename=ezetec_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'})

@app.route('/delete/<int:id>', methods=['POST'])
def delete_os(id):
    execute("DELETE FROM ordens_servico WHERE id=?", (id,))
    flash(f'Ordem de serviço #{id} excluída com sucesso!', 'success')
    return redirect(url_for('index'))

@app.route('/print/<int:id>')
def print_os(id):
    rows = query("SELECT * FROM ordens_servico WHERE id=?", (id,))
    os = rows[0] if rows else None
    
    if not os:
        return "OS não encontrada", 404
    
    vc = float(os['valor_conserto']) if os['valor_conserto'] else 0.0
    vp = float(os['valor_pecas']) if os['valor_pecas'] else 0.0
    
    html = f'''
    <html><head><meta charset="UTF-8"><title>OS #{os['id']}</title>
    <style>
        body {{ font-family: Arial; padding: 30px; font-size: 14px; }}
        h1 {{ color: #1a73e8; border-bottom: 2px solid #1a73e8; padding-bottom: 8px; }}
        .info {{ margin-bottom: 20px; }}
        .info p {{ margin: 5px 0; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 15px; }}
        td, th {{ border: 1px solid #ddd; padding: 10px; text-align: left; vertical-align: top; }}
        th {{ background: #f1f3f4; width: 200px; }}
        .total {{ font-size: 16px; font-weight: bold; color: #0f9d58; }}
        @media print {{ body {{ padding: 15px; }} }}
    </style></head><body>
    <h1>Ordem de Serviço #{os['id']}</h1>
    <div class="info">
        <p><strong>Cliente:</strong> {os['nome']} | <strong>Telefone:</strong> {os['telefone']}</p>
        <p><strong>Equipamento:</strong> {os['aparelho']} - {os['marca'] or '-'} {os['modelo'] or '-'}</p>
        <p><strong>Data de Entrada:</strong> {os['data_entrada']} | <strong>Data de Saída:</strong> {os['data_saida'] or '-'}</p>
        <p><strong>Status:</strong> {os['status_retirada']} | <strong>Técnico:</strong> {os['tecnico_responsavel'] or '-'}</p>
    </div>
    <table>
        <tr><th>Defeito Relatado</th><td>{os['defeito_relatado']}</td></tr>
        <tr><th>Estado de Entrada</th><td>{os['estado_entrada'] or '-'}</td></tr>
        <tr><th>Observações</th><td>{os['observacao'] or '-'}</td></tr>
        <tr><th>Diagnóstico Técnico</th><td>{os['defeito_encontrado'] or '-'}</td></tr>
        <tr><th>Valor Mão de Obra</th><td>R$ {vc:.2f}</td></tr>
        <tr><th>Valor Peças</th><td>R$ {vp:.2f}</td></tr>
        <tr><th class="total">Valor Total</th><td class="total">R$ {(vc + vp):.2f}</td></tr>
    </table>
    <script>window.print();</script>
    </body></html>
    '''
    return html

# --- ROTAS DE AUTENTICAÇÃO ---
PUBLIC_ROUTES = {'login'}

@app.before_request
def check_auth():
    if request.endpoint is None or request.endpoint in PUBLIC_ROUTES:
        return
    if 'username' not in session:
        return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        users = load_users()
        if username in users and users[username]['password'] == hashlib.sha256(password.encode()).hexdigest():
            session['username'] = username
            session['role'] = users[username]['role']
            flash('Login realizado com sucesso!', 'success')
            return redirect(url_for('index'))
        flash('Usuário ou senha inválidos!', 'error')
    return render_template_string(LOGIN_HTML)

@app.route('/logout')
def logout():
    session.clear()
    flash('Logout realizado!', 'success')
    return redirect(url_for('login'))

@app.route('/manage_users', methods=['GET', 'POST'])
def manage_users():
    if session.get('role') != 'admin':
        flash('Acesso restrito a administradores!', 'error')
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        users = load_users()
        if username in users:
            flash('Usuário já existe!', 'error')
        else:
            execute(
                "INSERT INTO usuarios (username, password, role) VALUES (?, ?, ?)",
                (username, hashlib.sha256(password.encode()).hexdigest(), 'user')
            )
            flash(f'Usuário "{username}" criado com sucesso!', 'success')
        return redirect(url_for('manage_users'))
    users = load_users()
    return render_template_string(USERS_HTML, users=users)

if __name__ == '__main__':
    app.run(debug=True, port=5000)