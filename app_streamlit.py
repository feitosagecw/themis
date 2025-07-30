import re
import streamlit as st
from app import pipeline_analise_cpf
from datetime import datetime

def highlight_keywords(text):
    if not text:
        return ''
    keywords = [r'condena[çc][aã]o', r'pena[s]?', r'pris[aã]o']
    pattern = re.compile(r'(' + '|'.join(keywords) + r')', re.IGNORECASE)
    return pattern.sub(r"<span style='color:#e53935;font-weight:bold;'>\\1</span>", text)

def format_date(date_str):
    if not date_str or not isinstance(date_str, str):
        return ''
    try:
        if 'T' in date_str:
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        else:
            dt = datetime.strptime(date_str, '%Y/%m/%d')
        return dt.strftime('%d/%m/%Y')
    except Exception:
        return date_str

st.set_page_config(page_title="Análise de Risco Jurídico", layout="wide")
st.title("Análise de Risco Jurídico")

cpf_input = st.text_input("Digite o CPF para análise:")

if st.button("Analisar"):
    if not cpf_input or len(cpf_input) < 11:
        st.warning("Por favor, digite um CPF válido.")
    else:
        with st.spinner("Analisando dados, por favor aguarde..."):
            try:
                dados_principais, resumos, parecer = pipeline_analise_cpf(cpf_input)
                st.subheader("Dados Principais")
                st.json(dados_principais)

                # Exibir sanções detalhadas com visual super moderno e limpo
                sancoes = dados_principais.get('Sanções Detalhadas', [])
                st.subheader("Sanções Detalhadas")
                css = '''
                <style>
                .sanction-card {
                    background: #fff;
                    border-radius: 18px;
                    box-shadow: 0 4px 24px rgba(44, 62, 80, 0.13);
                    margin: 32px 0 32px 0;
                    padding: 30px 32px 24px 32px;
                    position: relative;
                    transition: box-shadow 0.2s, border 0.2s;
                    border: 1.5px solid #e3e8f0;
                    max-width: 700px;
                    display: flex;
                    flex-direction: column;
                    gap: 10px;
                }
                .sanction-card:hover {
                    box-shadow: 0 8px 32px rgba(44, 62, 80, 0.18);
                    border: 1.5px solid #b3cdf6;
                }
                .sanction-title-modern {
                    font-size: 1.35em;
                    font-weight: 700;
                    color: #2563eb;
                    margin-bottom: 10px;
                    display: flex;
                    align-items: center;
                    gap: 10px;
                }
                .sanction-badge {
                    display: inline-block;
                    padding: 4px 14px;
                    border-radius: 16px;
                    font-size: 0.95em;
                    font-weight: 600;
                    color: #fff;
                    background: #f59e42;
                    margin-left: 10px;
                }
                .sanction-badge.pendente { background: #f59e42; }
                .sanction-badge.cumprido { background: #22c55e; }
                .sanction-badge.outro { background: #64748b; }
                .sanction-field {
                    margin-bottom: 0px;
                    font-size: 1.08em;
                    display: flex;
                    gap: 8px;
                }
                .sanction-label {
                    font-weight: 600;
                    color: #374151;
                    min-width: 170px;
                    display: inline-block;
                }
                .sanction-icon {
                    font-size: 1.5em;
                    margin-right: 6px;
                }
                .sanction-desc {
                    background: #f3f6fa;
                    border-radius: 8px;
                    padding: 12px 14px;
                    font-size: 1em;
                    color: #2d3748;
                    font-family: 'Fira Mono', 'Consolas', 'Menlo', monospace;
                    white-space: pre-wrap;
                    margin-top: 8px;
                }
                .sanction-separator {
                    border-top: 2px dashed #e3e8f0;
                    margin: 36px 0 0 0;
                }
                @media (max-width: 700px) {
                    .sanction-card { padding: 14px 4vw 12px 4vw; }
                    .sanction-label { min-width: 110px; }
                }
                </style>
                '''
                st.markdown(css, unsafe_allow_html=True)
                if isinstance(sancoes, str):
                    st.markdown(f"<div class='no-sanction-streamlit'>{highlight_keywords(sancoes)}</div>", unsafe_allow_html=True)
                else:
                    for idx, s in enumerate(sancoes, 1):
                        status = (s.get('Status', '') or '').strip().lower()
                        badge_class = 'outro'
                        badge_text = status.capitalize() if status else 'Outro'
                        if 'pendente' in status:
                            badge_class = 'pendente'
                        elif 'cumprido' in status or 'preso' in status:
                            badge_class = 'cumprido'
                        icon = '⚖️'
                        html = f"""
                        <div class='sanction-card'>
                            <div class='sanction-title-modern'>{icon} Sanção #{idx}
                                <span class='sanction-badge {badge_class}'>{badge_text}</span>
                            </div>
                            <div class='sanction-field'><span class='sanction-label'>Fonte:</span> {highlight_keywords(s.get('Fonte', ''))}</div>
                            <div class='sanction-field'><span class='sanction-label'>Tipo:</span> {highlight_keywords(s.get('Tipo', ''))} ({highlight_keywords(s.get('Tipo Padronizado', ''))})</div>
                            <div class='sanction-field'><span class='sanction-label'>Órgão:</span> {highlight_keywords(s.get('Órgão', ''))}</div>
                            <div class='sanction-field'><span class='sanction-label'>Data de Início:</span> {format_date(s.get('Data de Início', ''))}</div>
                            <div class='sanction-field'><span class='sanction-label'>Data de Fim:</span> {format_date(s.get('Data de Fim', ''))}</div>
                            <div class='sanction-field'><span class='sanction-label'>Número do Processo:</span> {s.get('Número do Processo', '')}</div>
                            <div class='sanction-field'><span class='sanction-label'>Número do Mandado:</span> {s.get('Número do Mandado', '')}</div>
                            <div class='sanction-field'><span class='sanction-label'>Regime:</span> {highlight_keywords(s.get('Regime', ''))}</div>
                            <div class='sanction-field'><span class='sanction-label'>Tempo de Pena:</span> {highlight_keywords(s.get('Tempo de Pena', ''))}</div>
                            <div class='sanction-field'><span class='sanction-label'>Recaptura:</span> {highlight_keywords(s.get('Recaptura', ''))}</div>
                            <div class='sanction-field'><span class='sanction-label'>Nome na Lista:</span> {highlight_keywords(s.get('Nome na Lista', ''))}</div>
                            <div class='sanction-field'><span class='sanction-label'>Data de Nascimento:</span> {format_date(s.get('Data de Nascimento', ''))}</div>
                            <div class='sanction-field'><span class='sanction-label'>Descrição da Decisão:</span></div>
                            <div class='sanction-desc'>{highlight_keywords(s.get('Descrição', ''))}</div>
                        </div>
                        <div class='sanction-separator'></div>
                        """
                        st.markdown(html, unsafe_allow_html=True)

                st.subheader("Resumos das Decisões")
                if resumos:
                    for r in resumos:
                        st.markdown(f"**Processo:** {r['Processo']}")
                        st.write(r['Resumo'])
                        st.markdown("---")
                else:
                    st.info("Nenhum resumo de decisão encontrado.")
                st.subheader("Parecer Final de Risco")
                st.code(parecer, language="markdown")
            except Exception as e:
                st.error(f"Erro ao processar análise: {e}") 