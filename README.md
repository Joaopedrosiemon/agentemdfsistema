# 🪵 Agente MDF - Copiloto de Substituição

> **Versão 1.3.1** | Sistema inteligente de recomendação de alternativas para produtos MDF

Um assistente de IA especializado para consultas de estoque, substituições de produtos e alternativas inteligentes em chapas de MDF, utilizando Claude AI para processamento de linguagem natural.

---

## 📋 Sobre o Projeto

O **Agente MDF** é um copiloto inteligente desenvolvido para auxiliar vendedores e atendentes na busca rápida por:
- ✅ Substituições de produtos MDF indisponíveis
- ✅ Alternativas em outras localidades/estoques
- ✅ Equivalências baseadas em tabelas de similaridade
- ✅ Cálculo automático de consumo de fita de borda
- ✅ Busca web quando não há alternativas internas

---

## 🚀 Funcionalidades

### 🔍 Consultas Inteligentes
- Processamento de linguagem natural via Claude AI
- Busca por código, descrição ou características do produto
- Recomendações contextualizadas baseadas em estoque real

### 📊 Gestão de Estoque
- Integração com planilhas de estoque (Excel)
- Visualização de disponibilidade por localização
- Atualização automática via upload de arquivos

### 🔄 Sistema de Substituições
- Tabela de equivalências e similaridades
- Alternativas em outras localidades
- Busca web quando necessário (Brave Search API)

### 🎨 Fitas de Borda
- Cálculo automático de metros necessários
- Verificação de estoque de fitas compatíveis
- Recomendações de cores similares

### 📝 Feedback e Aprendizado
- Sistema de avaliação de recomendações (👍/👎)
- Melhoria contínua baseada em feedback

---

## 🛠️ Tecnologias Utilizadas

- **Python 3.11+**
- **Streamlit** - Interface web interativa
- **Anthropic Claude AI** - Processamento de linguagem natural
- **SQLite** - Banco de dados local
- **Pandas** - Manipulação de dados
- **OpenpyXL** - Leitura de planilhas Excel
- **Brave Search API** - Busca web externa

---

## 📦 Instalação

### 1. Clone o repositório
```bash
git clone https://github.com/SEU_USUARIO/agente-mdf.git
cd agente-mdf
```

### 2. Crie um ambiente virtual
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows
```

### 3. Instale as dependências
```bash
pip install -r requirements.txt
```

### 4. Configure as variáveis de ambiente
```bash
cp .env.example .env
```

Edite o arquivo `.env` com suas credenciais:
```env
ANTHROPIC_API_KEY=sk-ant-api03-...  # Obtenha em https://console.anthropic.com/
BRAVE_API_KEY=BSA...                 # Obtenha em https://brave.com/search/api/
PRIMARY_LOCATION=Gmad Fortaleza      # Sua localização principal
APP_PASSWORD=                        # Senha de acesso (opcional)
```

### 5. Prepare os dados iniciais

Coloque seus arquivos Excel na pasta `data/raw/`:
- **Tabela de Similaridade**: `TABELA_SIMILARIDADE_GRUPO_LOCATELLI_XXXX.xlsx`
- **Estoque Atual**: `Estoque Atual_XXXX.xlsx`
- **Central de Trocas**: `Central de Trocas_XXXX.xlsx` (opcional)

### 6. Execute a aplicação
```bash
streamlit run app.py
```

A aplicação estará disponível em `http://localhost:8501`

---

## 📁 Estrutura do Projeto

```
agente-mdf/
├── app.py                      # Ponto de entrada principal
├── config/                     # Configurações
│   ├── settings.py            # Variáveis de ambiente
│   └── constants.py           # Constantes do sistema
├── src/
│   ├── ai/                    # Integração com Claude AI
│   │   ├── claude_client.py
│   │   ├── prompts.py
│   │   ├── tools.py
│   │   └── response_formatter.py
│   ├── database/              # Gerenciamento de dados
│   │   ├── schema.py
│   │   ├── queries.py
│   │   ├── import_data.py
│   │   └── preload_data.py
│   ├── models/                # Modelos de dados
│   ├── services/              # Lógica de negócio
│   │   ├── product_service.py
│   │   ├── stock_service.py
│   │   ├── substitution_orchestrator.py
│   │   ├── edging_tape_service.py
│   │   └── web_search_service.py
│   └── ui/                    # Interface Streamlit
│       ├── chat_interface.py
│       ├── sidebar.py
│       └── components.py
├── data/
│   ├── raw/                   # Planilhas Excel
│   └── db/                    # Banco SQLite
└── requirements.txt           # Dependências Python
```

---

## 🎯 Como Usar

### 1️⃣ Faça upload dos arquivos de estoque
Use a barra lateral para importar:
- Tabela de similaridade
- Estoque atual
- Central de trocas (opcional)

### 2️⃣ Faça perguntas em linguagem natural
Exemplos:
- *"Tem MDF 15mm Branco Texturizado?"*
- *"Preciso de 10 chapas de MDF 18mm Preto TX, quanto de fita?"*
- *"Alternativas para MDF 6mm Freijó no estoque de Maracanaú?"*

### 3️⃣ Avalie as respostas
Use 👍 ou 👎 para ajudar o sistema a melhorar

---

## 🔐 Segurança

- ⚠️ **NUNCA** commite o arquivo `.env` com suas chaves reais
- ✅ Use `.env.example` apenas como template
- ✅ Configure variáveis de ambiente no Streamlit Cloud para deploy
- ✅ Mantenha o repositório privado se contém dados sensíveis

---

## 📄 Licença

Este projeto é de uso interno. Todos os direitos reservados.

---

## 🤝 Contribuindo

Para melhorias ou correções:
1. Faça um fork do projeto
2. Crie uma branch para sua feature (`git checkout -b feature/MinhaFeature`)
3. Commit suas mudanças (`git commit -m 'Adiciona MinhaFeature'`)
4. Push para a branch (`git push origin feature/MinhaFeature`)
5. Abra um Pull Request

---

## 📞 Suporte

Para dúvidas ou problemas, entre em contato com a equipe de desenvolvimento.

---

**Desenvolvido com ❤️ para otimizar o atendimento ao cliente**
