# Google Calendar Desktop Widget

Widget de calendário do Google para área de trabalho com interface moderna e transparente.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![PyQt6](https://img.shields.io/badge/GUI-PyQt6-green)

## Funcionalidades

- **Autenticação Google Calendar** - OAuth2 com fluxo automático
- **Widget transparente** - Interface moderna com bordas arredondadas
- **Calendário mensal** - Visualização completa do mês atual
- **Destaque visual** - Dia atual, fins de semana e feriados brasileiros com cores distintas
- **Ícone na bandeja** - Acesso rápido via system tray (perto do relógio)
- **Gerenciar compromissos** - Ver, criar, editar e excluir eventos
- **Redimensionável** - Arraste e redimensione livremente
- **Auto-atualização** - Atualiza automaticamente a cada 5 minutos

## Instalação

### 1. Requisitos

- Python 3.10 ou superior
- pip

### 2. Instalar dependências

```bash
pip install -r requirements.txt
```

### 3. Configurar credenciais do Google

1. Acesse o [Google Cloud Console](https://console.cloud.google.com/)
2. Crie um novo projeto (ou use um existente)
3. Ative a **Google Calendar API**
4. Vá em **Credenciais** > **Criar Credenciais** > **ID do cliente OAuth 2.0**
5. Selecione **Aplicativo para computador**
6. Baixe o arquivo JSON

### 4. Executar

```bash
python run.py
```

Na primeira execução, uma janela de configuração será exibida para importar as credenciais JSON e autorizar o acesso ao Google Calendar.

## Uso

### Interface do Widget

- **Navegação**: Use os botões ◀ e ▶ para mudar de mês
- **Hoje**: Clique no botão "Hoje" para voltar ao mês atual
- **Novo evento**: Clique no botão "+" ou duplo-clique em um dia
- **Ver evento**: Clique em um evento no calendário
- **Editar evento**: Abra um evento e clique em "Editar"
- **Mover widget**: Clique e arraste na área do cabeçalho
- **Redimensionar**: Use o grip no canto inferior direito

### Cores do Calendário

| Cor | Significado |
|-----|-------------|
| 🟢 Verde/Teal | Dia atual |
| 🔴 Rosa | Fins de semana |
| 🟡 Laranja | Feriados brasileiros |
| 🔵 Azul/Roxo | Dias da semana |

### Ícone na Bandeja (System Tray)

- **Clique**: Mostrar/ocultar widget
- **Clique direito**: Menu com opções
  - Mostrar/Ocultar Widget
  - Atualizar
  - Novo Compromisso
  - Sair

## Estrutura do Projeto

```
google-calendar-widget/
├── run.py                  # Ponto de entrada
├── requirements.txt        # Dependências
├── calendar_widget/
│   ├── __init__.py
│   ├── main.py            # Controlador principal
│   ├── auth.py            # Autenticação OAuth2
│   ├── calendar_api.py    # API do Google Calendar
│   ├── widget.py          # Widget principal do calendário
│   ├── tray.py            # Ícone na bandeja do sistema
│   ├── dialogs.py         # Diálogos de eventos
│   ├── holidays_br.py     # Feriados brasileiros
│   └── styles.py          # Estilos e temas
└── README.md
```

## Tecnologias

- **PyQt6** - Interface gráfica
- **Google Calendar API** - Integração com calendário
- **google-auth-oauthlib** - Autenticação OAuth2
- **holidays** - Detecção de feriados brasileiros
