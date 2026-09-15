# Google Calendar Desktop Widget

Um widget de calendário transparente e direto ao ponto para a área de trabalho, feito em Python (PyQt6) e integrado à API do Google Calendar.

Ele fica no seu desktop mostrando os compromissos do mês, destaca feriados nacionais brasileiros e permite criar, visualizar e editar eventos com facilidade. Funciona no Windows e Linux.

## Funcionalidades

- **Conexão rápida com o Google**: login direto pelo navegador com 1 clique.
- **Fixar no topo (📌)**: botão no cabeçalho e menu na bandeja para manter o calendário visível por cima de outras janelas.
- **Widget transparente**: visual escuro translúcido com cantos arredondados que combina com qualquer papel de parede.
- **Filtro de agendas (☰)**: escolha quais calendários da sua conta Google você quer exibir ou ocultar.
- **Notificações**: avisos na bandeja do sistema (15 min, 5 min antes e na hora do evento).
- **Feriados brasileiros**: detecta e destaca automaticamente feriados nacionais.
- **Gerenciar compromissos**: duplo clique no dia para criar evento, ou clique no compromisso para ver detalhes/editar.
- **Cores de fundo**: escolha entre temas visuais pelo menu da bandeja (Escuro, Vidro transparente, Meia-noite, etc.).
- **Redimensionável**: arraste pelo cabeçalho para mover e use as bordas ou canto inferior para ajustar o tamanho.
- **Ícone na bandeja (Systray)**: atalhos rápidos perto do relógio e opção de iniciar junto com o sistema.

## Como rodar

### 1. Pré-requisitos
- Python 3.10 ou superior.

### 2. Instalar dependências

```bash
pip install -r requirements.txt
```

### 3. Credenciais do Google
O aplicativo precisa das credenciais OAuth para acessar sua agenda:

- Coloque o arquivo com o nome `client_secret.json` na raiz do projeto (veja o modelo em `client_secret.json.example`).
- Se precisar gerar suas credenciais:
  1. Acesse o [Google Cloud Console](https://console.cloud.google.com/).
  2. Crie um projeto e ative a **Google Calendar API**.
  3. Em **Credenciais**, crie um **ID do cliente OAuth 2.0** do tipo **Aplicativo para computador**.
  4. Baixe o JSON e salve como `client_secret.json` na pasta do widget.

### 4. Iniciar

```bash
python run.py
```
*(No Windows, você também pode dar duplo clique no `inciar.bat`).*

Na primeira vez, vai abrir a tela de boas-vindas. Clique em **"Conectar com o Google"**, autorize o acesso no seu navegador e pronto! Seu login fica salvo localmente em `~/.google-calendar-widget/token.json`.

## Dicas de uso

- **Mover o widget**: clique e arraste pelo cabeçalho (onde fica o mês/ano).
- **Redimensionar**: arraste pelas bordas ou pelo canto inferior direito.
- **Novo evento**: dê duplo clique em qualquer dia ou use o botão `+`.
- **Ver/Editar evento**: clique no nome do compromisso dentro do dia.
- **Sempre no topo**: clique no ícone de alfinete `📌` no topo ou pelo menu de contexto da bandeja.
- **Trocar tema / Iniciar com o PC**: clique com o botão direito no ícone do widget perto do relógio.

## Tecnologias

- Python 3
- PyQt6
- Google Calendar API v3
- google-auth-oauthlib
- holidays (feriados BR)
