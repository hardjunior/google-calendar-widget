# Google Calendar Desktop Widget

Um widget de calendário e agenda transparente, moderno e altamente produtivo para a área de trabalho, desenvolvido em Python (PyQt6) e integrado diretamente à API do Google Calendar.

Ele combina um visual translúcido elegante que se integra ao papel de parede com ferramentas poderosas de gerenciamento de tempo: alternância entre visão mensal e linha do tempo (agenda), gerenciador completo de tarefas (CRUD), painel lateral por dia, cores reais dos calendários e sincronização assíncrona fluida.

---

## 🚀 Funcionalidades

- **Gerenciador de Tarefas e Compromissos (CRUD)**:
  - Modal dedicado acessível pelo botão `📋 Tarefas` ou pelo menu da bandeja.
  - Filtros rápidos: `📌 Atuais (Hoje)`, `⏳ Seguintes` (amanhã e próximas) e `📅 Todas`.
  - Indicador visual em tempo real para tarefas `🟢 Em andamento`.
  - Ações diretas em cada tarefa: **Visualizar (`👁️`)**, **Editar (`✏️`)** e **Excluir (`🗑️`)**, além de **Criar (`+ Nova Tarefa`)**.
- **Visão Dupla (Mês e Agenda)**:
  - `⊞ Mês`: Grade clássica de 30 dias para uma visão panorâmica dos seus compromissos.
  - `☰ Agenda`: Linha do tempo vertical cronológica agrupada por dia (*Hoje*, *Amanhã*, etc.) com cards detalhados.
- **Painel Lateral do Dia (Day Inspector)**:
  - Clique simples em qualquer dia da grade (ou no badge `+N mais`) para abrir o painel lateral com a programação completa, horários e atalho para criar compromisso naquele dia específico.
- **Cores Reais dos Calendários**:
  - Exibe a cor real configurada em cada calendário da sua conta Google (trabalho, pessoal, estudos) ou cores personalizadas dos eventos, facilitando o reconhecimento visual imediato.
  - Legenda dinâmica no rodapé com os calendários ativos.
- **Busca Rápida Integrada**:
  - Campo de pesquisa em tempo real no cabeçalho: filtra instantaneamente compromissos na grade e na agenda por título, local ou descrição.
- **Carregamento Assíncrono com Cache**:
  - Requisições à API do Google rodam em segundo plano via thread dedicada (`FetchEventsWorker`). A interface nunca congela e navegar entre os meses é instantâneo.
- **Dia Inteiro e Presets de Duração**:
  - Suporte completo a eventos de dia inteiro (`[ ] Dia inteiro`).
  - Chips de duração rápida (`+15m`, `+30m`, `+45m`, `+1h`, `+2h`) que ajustam o término com 1 clique.
- **Links Clicáveis nas Descrições**:
  - Links e URLs em descrições de compromissos abrem automaticamente no navegador padrão com um clique.
- **Fixar no Topo (📌)**:
  - Botão no cabeçalho e opção no menu da bandeja para manter a agenda sempre visível sobre outras janelas.
- **Filtro de Agendas (☰)**:
  - Escolha facilmente quais calendários da sua conta Google exibir ou ocultar.
- **Feriados Brasileiros**:
  - Detecção e destaque automático de feriados nacionais.
- **Notificações no Desktop**:
  - Avisos nativos na bandeja do sistema (15 min antes, 5 min antes e no horário do evento).
- **Temas de Fundo**:
  - Escolha entre temas visuais pelo menu da bandeja (Escuro, Claro, Azul, Roxo, Verde).
- **Redimensionável e Arrastável**:
  - Arraste pelo cabeçalho para mover e redimensione livremente pelas bordas ou pelo canto inferior direito.
- **Ícone na Bandeja (Systray)**:
  - Atalhos rápidos perto do relógio e opção de iniciar junto com o sistema operacional (Windows e Linux).

---

## 🛠️ Como Rodar

### 1. Pré-requisitos
- Python 3.10 ou superior.

### 2. Instalar Dependências

```bash
pip install -r requirements.txt
```

### 3. Credenciais do Google (OAuth 2.0)
O aplicativo precisa das credenciais OAuth para acessar sua agenda:

1. Acesse o [Google Cloud Console](https://console.cloud.google.com/).
2. Crie um projeto e ative a **Google Calendar API**.
3. Em **Credenciais**, crie um **ID do cliente OAuth 2.0** do tipo **Aplicativo para computador**.
4. Baixe o arquivo JSON e salve-o com o nome `client_secret.json` na raiz do projeto (veja o modelo em `client_secret.json.example`).

### 4. Iniciar

```bash
python run.py
```
*(No Windows, você também pode dar duplo clique no `inciar.bat`).*

Na primeira execução, uma tela de boas-vindas será exibida. Clique em **"Conectar com o Google"**, autorize o acesso no seu navegador e pronto! Seu login fica salvo de forma segura localmente em `~/.google-calendar-widget/token.json`.

---

## 💡 Dicas de Uso

- **Mover o widget**: Clique e arraste pelo cabeçalho (onde fica o mês/ano).
- **Redimensionar**: Arraste pelas bordas ou pelo canto inferior direito.
- **Ver tarefas atuais e seguintes (CRUD)**: Clique no botão `📋 Tarefas` no cabeçalho ou no ícone da bandeja perto do relógio.
- **Alternar visão**: Alterne entre `⊞ Mês` e `☰ Agenda` no cabeçalho.
- **Inspecionar um dia**: Clique 1 vez em qualquer dia do mês para abrir o painel lateral com todos os eventos e horários.
- **Novo compromisso**: Dê duplo clique em qualquer dia ou use o botão `+`.
- **Ver/Editar evento**: Clique diretamente no nome do compromisso.
- **Sempre no topo**: Clique no ícone de alfinete `📌` no cabeçalho.
- **Trocar tema / Iniciar com o PC**: Clique com o botão direito no ícone do widget na bandeja do sistema.

---

## 📦 Tecnologias

- **Python 3**
- **PyQt6** (Interface gráfica nativa com suporte a aceleração e transparência)
- **Google Calendar API v3**
- **google-auth-oauthlib**
- **holidays** (Feriados nacionais brasileiros)
- **python-dateutil**
