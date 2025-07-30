# 📦 #### Imports
import os
import re
import json
import datetime
import requests

import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from google.cloud import bigquery
from google.auth import default
import openai
from dotenv import load_dotenv
from agents import Agent, function_tool

# Carregar variáveis de ambiente
load_dotenv()
openai_api_key = os.getenv('OPENAI_API_KEY')
if not openai_api_key:
    raise ValueError('A variável de ambiente OPENAI_API_KEY não está definida.')
openai_client = openai.OpenAI(api_key=openai_api_key)

# Função para resumir decisões
@function_tool
def resumir_decisao(decisao: str) -> str:
    prompt = f"""
Resuma de forma clara, objetiva e técnica a decisão judicial e as informações de sanções abaixo, destacando o que foi decidido, as penas aplicadas, absolvições, homologações, sanções, fontes, datas ou outros pontos relevantes para análise de risco:

{decisao}
"""
    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Você é um analista jurídico especializado em resumir decisões judiciais e sanções."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=500,
        temperature=0.3
    )
    return response.choices[0].message.content

# Função para análise de risco
@function_tool
def analisar_risco(dados: dict, resumos: list) -> str:
    prompt = f"""
Você é um analista jurídico de uma fintech, especializado em compliance e avaliação de risco de clientes. Seja cético e criterioso. Analise os dados abaixo e, para cada processo criminal, avalie o tipo, contexto, partes envolvidas, decisões (traga um resumo detalhado do conteúdo da decisão), homologações e demais detalhes relevantes. Considere o histórico, quantidade, gravidade e natureza dos processos para emitir um parecer objetivo sobre o risco de manter esse cliente na base (baixo, médio ou alto risco), justificando sua conclusão de forma clara e técnica.

Dados cadastrais e de compliance:
{json.dumps(dados, ensure_ascii=False, indent=2)}

Resumos das decisões:
{json.dumps(resumos, ensure_ascii=False, indent=2)}
"""
    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Você é um assistente que resume dados de pessoas."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=1000,
        temperature=0.3
    )
    return response.choices[0].message.content

# Criação dos agentes
agente_resumo = Agent(
    name="Resumidor de Decisões",
    instructions="Resuma decisões judiciais de forma clara, técnica e objetiva, destacando pontos relevantes para análise de risco.",
    model="gpt-4o-mini",
    tools=[resumir_decisao],
)

agente_risco = Agent(
    name="Analista de Risco",
    instructions="Analise o histórico, contexto e gravidade dos processos e emita um parecer de risco (baixo, médio, alto), justificando tecnicamente.",
    model="gpt-4o-mini",
    tools=[analisar_risco],
)

# ⚙️ #### Setup BigQuery (ambiente local)
# Se necessário, configure as credenciais do Google Cloud via variável de ambiente ou arquivo json
# Exemplo: export GOOGLE_APPLICATION_CREDENTIALS='caminho/para/credenciais.json'

bq_client = bigquery.Client(project='ai-services-sae')

# 🔐 #### Credenciais 
bigdata_token_id = os.getenv('BIGDATA_TOKEN_ID')
bigdata_token_hash = os.getenv('BIGDATA_TOKEN_HASH')
if not bigdata_token_id or not bigdata_token_hash:
    raise ValueError('As variáveis de ambiente BIGDATA_TOKEN_ID e/ou BIGDATA_TOKEN_HASH não estão definidas.')

# 🧠 #### Função para buscar dados na API

def fetch_bdc_data(
    document_number: str,
    url: str,
    dataset: str,
    token_hash: str,
    token_id: str
):
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "AccessToken": token_hash,
        "TokenId": token_id
    }
    payload = {
        "q": f"doc{{{document_number}}}",
        "Datasets": dataset
    }
    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()
    return response.json()

def formatar_sancoes_detalhadas(sancoes):
    if not sancoes or sancoes == "Nenhuma sanção detalhada encontrada":
        return "Nenhuma sanção detalhada encontrada."
    texto = []
    for idx, s in enumerate(sancoes, 1):
        texto.append(f"\n---\nSanção #{idx}:")
        texto.append(f"Fonte: {s.get('Fonte', '')}")
        texto.append(f"Tipo: {s.get('Tipo', '')} ({s.get('Tipo Padronizado', '')})")
        texto.append(f"Status: {s.get('Status', '')}")
        texto.append(f"Órgão: {s.get('Órgão', '')}")
        texto.append(f"Data de Início: {s.get('Data de Início', '')}")
        texto.append(f"Data de Fim: {s.get('Data de Fim', '')}")
        texto.append(f"Número do Processo: {s.get('Número do Processo', '')}")
        texto.append(f"Número do Mandado: {s.get('Número do Mandado', '')}")
        texto.append(f"Regime: {s.get('Regime', '')}")
        texto.append(f"Tempo de Pena: {s.get('Tempo de Pena', '')}")
        texto.append(f"Recaptura: {s.get('Recaptura', '')}")
        texto.append(f"Nome na Lista: {s.get('Nome na Lista', '')}")
        texto.append(f"Data de Nascimento: {s.get('Data de Nascimento', '')}")
        texto.append(f"Descrição da Decisão: {s.get('Descrição', '')}")
    return '\n'.join(texto)

def formatar_sancoes_detalhadas_html(sancoes):
    if not sancoes or sancoes == "Nenhuma sanção detalhada encontrada":
        return "<div class='no-sanction'>Nenhuma sanção detalhada encontrada.</div>"
    html = []
    for idx, s in enumerate(sancoes, 1):
        html.append(f"""
        <div class='sanction-block'>
            <div class='sanction-title'>Sanção #{idx}</div>
            <div><b>Fonte:</b> {s.get('Fonte', '')}</div>
            <div><b>Tipo:</b> {s.get('Tipo', '')} ({s.get('Tipo Padronizado', '')})</div>
            <div><b>Status:</b> {s.get('Status', '')}</div>
            <div><b>Órgão:</b> {s.get('Órgão', '')}</div>
            <div><b>Data de Início:</b> {s.get('Data de Início', '')}</div>
            <div><b>Data de Fim:</b> {s.get('Data de Fim', '')}</div>
            <div><b>Número do Processo:</b> {s.get('Número do Processo', '')}</div>
            <div><b>Número do Mandado:</b> {s.get('Número do Mandado', '')}</div>
            <div><b>Regime:</b> {s.get('Regime', '')}</div>
            <div><b>Tempo de Pena:</b> {s.get('Tempo de Pena', '')}</div>
            <div><b>Recaptura:</b> {s.get('Recaptura', '')}</div>
            <div><b>Nome na Lista:</b> {s.get('Nome na Lista', '')}</div>
            <div><b>Data de Nascimento:</b> {s.get('Data de Nascimento', '')}</div>
            <div><b>Descrição da Decisão:</b> <pre style='white-space:pre-wrap'>{s.get('Descrição', '')}</pre></div>
        </div>
        """)
    return '\n'.join(html)

def pipeline_analise_cpf(cpf_input: str):
    """
    Executa toda a pipeline de análise de risco a partir de um CPF, retornando os dados principais, resumos e parecer.
    """
    cpf_sanitizado = re.sub(r'\D', '', cpf_input)
    bdc_data = fetch_bdc_data(
        document_number=cpf_sanitizado,
        url="https://plataforma.bigdatacorp.com.br/pessoas",
        dataset="""basic_data,
                   processes.filter(partypolarity = PASSIVE, courttype = CRIMINAL),
                   kyc.filter(standardized_type, standardized_sanction_type, type, sanctions_source = Conselho Nacional de Justiça)""",
        token_hash=bigdata_token_hash,
        token_id=bigdata_token_id
    )
    print("\n===== RESULTADO BRUTO DA API (bdc_data) =====\n")
    print(json.dumps(bdc_data, ensure_ascii=False, indent=2))
    print("\n===== FIM DO RESULTADO BRUTO =====\n")
    try:
        pessoa = bdc_data["Result"][0]
        basic = pessoa.get("BasicData", {})
        kyc = pessoa.get("KycData", {})
        processos = pessoa.get("Processes", {})
        detalhes_processos = []
        if processos.get("Lawsuits"):
            for proc in processos["Lawsuits"]:
                if proc.get("CourtType") == "CRIMINAL":
                    conteudo = proc.get("Content", "")
                    decisao = proc.get("Decision", "")
                    descricao = proc.get("Description") or proc.get("Summary") or proc.get("Details") or ""
                    homologacao = False
                    for texto in [conteudo, decisao, descricao]:
                        if texto and "homologada" in texto.lower():
                            homologacao = True
                            break
                    partes = proc.get("Parties", [])
                    is_reu = False
                    partes_resumo = []
                    for parte in partes:
                        papel = parte.get("Type", "")
                        nome = parte.get("Name", "")
                        espec = parte.get("PartyDetails", {}).get("SpecificType", "")
                        partes_resumo.append(f"{nome} ({papel}{' - ' + espec if espec else ''})")
                        if papel.upper() == "DEFENDANT" or papel.upper() == "RÉU" or espec.upper() == "RÉU":
                            if basic.get("Name", "").strip().upper() in nome.strip().upper():
                                is_reu = True
                    detalhes_processos.append({
                        "Número": proc.get("CaseNumber") or proc.get("Number"),
                        "É Réu": "Sim" if is_reu else "Não",
                        "Tipo": proc.get("Type"),
                        "Assunto Principal": proc.get("MainSubject"),
                        "Assunto CNJ": proc.get("InferredCNJSubjectName"),
                        "Tipo Procedimento CNJ": proc.get("InferredCNJProcedureTypeName"),
                        "Outros Assuntos": proc.get("OtherSubjects"),
                        "Data": proc.get("FilingDate"),
                        "Órgão": proc.get("CourtName"),
                        "Órgão Julgador": proc.get("JudgingBody"),
                        "Nível da Corte": proc.get("CourtLevel"),
                        "Comarca": proc.get("CourtDistrict"),
                        "Estado": proc.get("State"),
                        "Juiz": proc.get("Judge"),
                        "Situação": proc.get("Status"),
                        "Data de Encerramento": proc.get("CloseDate"),
                        "Última Movimentação": proc.get("LastMovementDate"),
                        "Partes": partes_resumo,
                        "Decisão": decisao,
                        "Descrição": descricao,
                        "Conteúdo": conteudo,
                        "Homologação": "Sim" if homologacao else "Não"
                    })
        # Extrair todas as sanções detalhadas
        sancoes_detalhadas = []
        for sancao in kyc.get("SanctionsHistory", []):
            detalhes = sancao.get("Details", {})
            sancoes_detalhadas.append({
                "Fonte": sancao.get("Source"),
                "Tipo": sancao.get("Type"),
                "Tipo Padronizado": sancao.get("StandardizedSanctionType"),
                "Data de Início": sancao.get("StartDate"),
                "Data de Fim": sancao.get("EndDate"),
                "Status": detalhes.get("Status"),
                "Órgão": detalhes.get("Agency"),
                "Número do Processo": detalhes.get("ProcessNumber"),
                "Número do Mandado": detalhes.get("ArrestWarrantNumber"),
                "Descrição": detalhes.get("Decision"),
                "Regime": detalhes.get("PrisonRegime"),
                "Tempo de Pena": detalhes.get("PenaltyTime"),
                "Recaptura": detalhes.get("Recapture"),
                "Data de Nascimento": detalhes.get("BirthDate"),
                "Nome na Lista": detalhes.get("NameInSanctionList"),
                "Outros Detalhes": detalhes
            })
        dados_principais = {
            "Nome": basic.get("Name"),
            "CPF": basic.get("TaxIdNumber"),
            "Idade": basic.get("Age"),
            "Situação Cadastral": basic.get("TaxIdStatus"),
            "Órgão de Origem": basic.get("TaxIdOrigin"),
            "Processos": processos.get("TotalLawsuits"),
            "Sanções": kyc.get("IsCurrentlySanctioned"),
            "PEP": kyc.get("IsCurrentlyPEP"),
            "Última Sanção": kyc.get("LastSanctionDate"),
            "Sanções Detalhadas": formatar_sancoes_detalhadas(sancoes_detalhadas),
            "Processos Criminais Detalhes": detalhes_processos if detalhes_processos else "Nenhum processo criminal encontrado"
        }
    except Exception as e:
        dados_principais = {"erro": f"Não foi possível extrair dados principais: {e}"}
        processos = {}
        kyc = {}
    lista_decision_content = []
    if processos.get("Lawsuits"):
        lista_decision_content = extrair_decisoes([
            proc for proc in processos["Lawsuits"] if proc.get("CourtType") == "CRIMINAL"
        ])
    resumos = []
    if lista_decision_content:
        sanctions_info = ""
        if kyc:
            sanctions_info = f"""
Sanções:
- Atualmente sancionado: {kyc.get('IsCurrentlySanctioned')}
- Última sanção: {kyc.get('LastSanctionDate')}
- PEP: {kyc.get('IsCurrentlyPEP')}
"""
        for item in lista_decision_content:
            texto_decisao = f"""
Processo: {item['Número']}
Tipo: {item['TipoDecisao']}
Data: {item.get('DecisionDate', '')}
Decisão: {item['DecisionContent']}
{sanctions_info}
"""
            resumo = agente_resumo.run(decisao=texto_decisao)
            resumos.append({
                "Processo": item['Número'],
                "Resumo": resumo
            })
    parecer = agente_risco.run(dados=dados_principais, resumos=resumos)
    return dados_principais, resumos, parecer

def classificar_tipo_decisao(texto):
    texto_lower = texto.lower()
    if "homolog" in texto_lower:
        return "Homologação"
    if "conden" in texto_lower:
        return "Condenação"
    if "absolv" in texto_lower:
        return "Absolvição"
    if "suspensão condicional" in texto_lower:
        return "Suspensão Condicional"
    return "Outro"

def extrair_decisoes(lista_lawsuits):
    """
    Extrai decisões relevantes de uma lista de processos, incluindo contexto e tipo de decisão.
    """
    decisoes = []
    for proc in lista_lawsuits:
        processo_info = {
            "Número": proc.get("CaseNumber") or proc.get("Number"),
            "Órgão": proc.get("CourtName"),
            "Comarca": proc.get("CourtDistrict"),
            "Juiz": proc.get("Judge"),
        }
        for item in proc.get("Decisions", []):
            conteudo = item.get("DecisionContent", "").strip()
            if conteudo:
                decisao = {
                    "DecisionContent": conteudo,
                    "DecisionDate": item.get("DecisionDate"),
                    "TipoDecisao": classificar_tipo_decisao(conteudo)
                }
                decisao.update(processo_info)
                decisoes.append(decisao)
    # Remover duplicatas
    visto = set()
    decisoes_unicas = []
    for d in decisoes:
        chave = (d["DecisionContent"], d.get("DecisionDate"))
        if chave not in visto:
            visto.add(chave)
            decisoes_unicas.append(d)
    # Ordenar por data (mais recente primeiro)
    decisoes_ordenadas = sorted(decisoes_unicas, key=lambda x: x.get("DecisionDate") or "", reverse=True)
    return decisoes_ordenadas

# Remover execução automática ao importar
if __name__ == "__main__":
    cpf_input = '01130380114'
    dados_principais, resumos, parecer = pipeline_analise_cpf(cpf_input)
    print("\nResumo das decisões (por agente):\n")
    for r in resumos:
        print(f"Processo: {r['Processo']}\nResumo: {r['Resumo']}\n")
    print("\nParecer final de risco (por agente):\n")
    print(parecer)
    # Geração do HTML com CSS para sanções detalhadas
    sancoes_html = ""
    if isinstance(dados_principais.get('Sanções Detalhadas'), str):
        sancoes_html = f"<div class='no-sanction'>{dados_principais.get('Sanções Detalhadas')}</div>"
    else:
        sancoes_html = formatar_sancoes_detalhadas_html([s for s in dados_principais.get('Sanções Detalhadas', []) if isinstance(s, dict)])
    html_content = f"""
<html>
<head>
<meta charset='utf-8'>
<title>Parecer de Risco</title>
<style>
    body {{
        font-family: 'Segoe UI', 'Roboto', Arial, sans-serif;
        background: linear-gradient(120deg, #f0f4f8 0%, #e9eefa 100%);
        color: #23272f;
        margin: 0;
        padding: 0 0 40px 0;
    }}
    h2 {{
        color: #2d6cdf;
        margin-top: 32px;
        margin-bottom: 18px;
        letter-spacing: 0.5px;
    }}
    .container {{
        max-width: 900px;
        margin: 32px auto 0 auto;
        background: #fff;
        border-radius: 18px;
        box-shadow: 0 6px 32px rgba(44, 62, 80, 0.10);
        padding: 36px 32px 32px 32px;
    }}
    .sanction-block {{
        background: linear-gradient(100deg, #f7faff 60%, #eaf1fb 100%);
        border: 1.5px solid #e3e8f0;
        border-radius: 12px;
        margin: 28px 0;
        padding: 22px 28px 18px 28px;
        box-shadow: 0 2px 12px rgba(44, 62, 80, 0.07);
        transition: box-shadow 0.2s, border 0.2s;
        position: relative;
    }}
    .sanction-block:hover {{
        box-shadow: 0 6px 24px rgba(44, 62, 80, 0.13);
        border: 1.5px solid #b3cdf6;
    }}
    .sanction-title {{
        font-size: 1.18em;
        font-weight: 600;
        color: #2563eb;
        margin-bottom: 14px;
        letter-spacing: 0.2px;
    }}
    .no-sanction {{
        color: #888;
        font-style: italic;
        margin: 18px 0;
    }}
    pre {{
        background: #f3f6fa;
        border-radius: 6px;
        padding: 10px 12px;
        font-size: 1em;
        margin: 0;
        color: #2d3748;
        font-family: 'Fira Mono', 'Consolas', 'Menlo', monospace;
        white-space: pre-wrap;
    }}
    .sanction-block div {{
        margin-bottom: 7px;
        line-height: 1.6;
    }}
    @media (max-width: 700px) {{
        .container {{
            padding: 12px 4vw 18px 4vw;
        }}
        .sanction-block {{
            padding: 14px 6vw 12px 6vw;
        }}
    }}
</style>
</head>
<body>
<div class='container'>
<h2>Parecer final de risco (por agente)</h2>
<pre style='font-family:inherit'>{parecer}</pre>
<h2>Sanções Detalhadas</h2>
{sancoes_html}
</div>
</body>
</html>
"""
    with open("parecer.html", "w", encoding="utf-8") as f:
        f.write(html_content)