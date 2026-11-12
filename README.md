# AISSY

Assistente pessoal em Python, feita para rodar **localmente** (via Ollama), com conversa por texto ou voz, em português, inglês e espanhol, memória de longo prazo e uso de ferramentas (tool calling). É um projeto pessoal, em desenvolvimento contínuo.

> Este README separa o que **existe e está testado**, o que está **em desenvolvimento** e o que é **apenas ideia**.

## Estado atual

### Implementado e testado

- Chat no terminal com histórico persistente (JSON, uma conversa por UUID). O comando `/new` inicia uma conversa limpa e `exit` encerra.
- Provedor de LLM trocável. O `OllamaProvider` é o usado no dia a dia (modelo `qwen2.5:7b-instruct`). O `OpenAIProvider` está escrito, mas **não foi validado** com chamadas reais.
- Tool calling com laço de agente (até 5 rodadas) e ferramentas de data e hora (`get_current_datetime`, `get_date`).
- Memória de longo prazo em SQLite: criar, listar, atualizar e excluir. Pede confirmação antes de salvar e de excluir. Cada memória tem visibilidade `normal` ou `private`, e memórias privadas nunca são enviadas ao modelo nem usadas na busca.
- Recuperação híbrida de memórias: busca por palavras-chave combinada com similaridade semântica por embeddings (`bge-m3`, via Ollama), fundidas por Reciprocal Rank Fusion. Se os embeddings falharem, a busca volta para palavras-chave.
- Tarefas e lembretes em SQLite (`data/tasks.db`): a AISSY cria, lista e conclui tarefas por conversa (tool calling) ou por comandos (`/tarefas`, `/feito N`, `/apagar N`).
- Abertura proativa: ao iniciar e com `/hoje`, mostra saudação, data e tarefas atrasadas, de hoje e sem prazo. O resumo é montado em código, sem depender do modelo.
- Pedidos como "me lembra de X amanhã às 10h" são interpretados em código (data, hora e título), sem depender do modelo.
- Erros de ferramentas voltam ao modelo como resultado, em vez de derrubar a conversa. A data e a hora atuais entram no contexto de cada resposta.
- **Safety Layer** (fase 1): toda ação com efeito (tarefas, abrir apps) passa por uma camada independente do modelo, com allowlist, blocklist permanente, alvos protegidos (Riot/Vanguard), origem da ação, log de auditoria, parada de emergência (`/parar`) e política de bloquear na dúvida. Detalhes em [`docs/SAFETY.md`](docs/SAFETY.md).
- Mensagem amigável quando o Ollama está fora do ar.
- Modo voz opcional e 100% local: reconhecimento de fala com `faster-whisper` e fala com as vozes do Windows (`pyttsx3`), preferindo vozes femininas. Enter começa a gravação e Enter encerra. A lógica é testada com peças falsas; o áudio em si depende de microfone e das vozes instaladas, e foi validado manualmente.
- Persona definida em `aissy/persona.py` e conferida por um script (`evaluation/persona_check.py`) que roda 11 frases no modelo e verifica idioma, frases de chatbot genérico, forma feminina, tamanho da resposta e emojis. Com `qwen2.5:7b-instruct` o resultado foi 9/11, e varia entre execuções.
- Script de avaliação que compara busca por palavras, busca semântica e busca híbrida em um conjunto de perguntas.
- Suíte de testes automatizados com `pytest`, usando LLM e embedder falsos, sem depender de GPU.

### Em desenvolvimento

- Ajuste fino da persona: o modelo de 7B ainda escorrega para frases genéricas e erros de gramática.
- Avisos de lembrete no horário (a AISSY fala ou escreve o lembrete quando vence). A lógica é testada com peças falsas; falta validar no uso real.
- Abrir aplicativos por comando de voz ou texto, só de uma lista de apps permitidos (`aissy/apps.py`, extensível em `data/apps.json`). A lógica é testada com peças falsas; falta validar no Windows.

### Ideias (não implementadas)

- Voz mais natural (a atual, do Windows, soa robótica), palavra de ativação e execução em segundo plano.
- Interface gráfica.
- Integração com calendário.
- Pesquisa na web.
- Hub de jogos (backlog, lançamentos, atualizações).
- Modo de estudo de idiomas.

## Arquitetura

```text
main.py                     laço de interação no terminal
aissy/
  conversation.py           fluxo da conversa, contexto, memória e tool calling
  llm.py                    validação das respostas do modelo
  memory.py                 histórico de conversas (JSON)
  long_term_memory.py       memória de longo prazo (SQLite) e busca híbrida
  embeddings.py             cliente de embeddings (Ollama)
  tools.py                  ferramentas e suas definições
  persona.py                prompt de sistema e personalidade
  voice.py                  modo voz (gravação, transcrição, fala)
  tasks.py                  tarefas e lembretes (SQLite)
  safety/                   Safety Layer: ações, política, auditoria, parada de emergência
  reminders.py              avisos de lembrete no horário
  apps.py                   abrir aplicativos permitidos
  briefing.py               resumo do dia
  commands.py               comandos /hoje, /tarefas, /feito, /apagar
  errors.py                 erros próprios da aplicação
  providers/
    ollama_provider.py      LLM local
    openai_provider.py      LLM em nuvem (não validado)
evaluation/                 avaliação da recuperação de memórias e da persona
tests/                      testes automatizados
```

Decisões principais:

- **O núcleo não depende do modelo.** A conversa fala com uma interface (`generate`, `generate_with_tools`), e cada provedor traduz isso para o seu serviço.
- **Privacidade no código, não no prompt.** O que é privado é filtrado antes de chegar ao modelo e antes do cálculo de similaridade.
- **Degradação graciosa.** Sem embeddings, a AISSY continua funcionando com busca por palavras.
- **Ações destrutivas pedem confirmação.**

## Como rodar

Pré-requisitos: Python 3.13, [Ollama](https://ollama.com) instalado.

```powershell
git clone <url-do-repositorio>
cd AISSY
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt

ollama pull qwen2.5:7b-instruct
ollama pull bge-m3

python main.py
```

Para usar o modo voz (opcional), instale também as dependências de voz e abra com `--voz`, ou digite `/voz` durante a conversa:

```powershell
pip install -r requirements-voice.txt
python main.py --voz
```

Para testar outro modelo do Ollama: `$env:AISSY_MODEL = "nome-do-modelo"`. O modelo precisa aceitar ferramentas (tool calling).

Os dados locais (conversas e memórias) ficam em `data/`, que não é versionada. Chaves de API, se usadas, ficam em um arquivo `.env`, também fora do Git.

## Testes

```powershell
python -m pytest
```

## Avaliação da recuperação de memórias

O conjunto de avaliação tem 12 memórias (em português e inglês) e 17 perguntas: com palavras em comum, com o mesmo sentido e palavras diferentes, entre idiomas e sem resposta. O script está em `evaluation/evaluate_retrieval.py`.

```powershell
python -m evaluation.evaluate_retrieval
```

| Método | hit@1 | hit@3 | Falsos positivos |
|---|---|---|---|
| Palavras-chave (busca original) | 3/13 | 4/13 | 1/4 |
| Semântica (limiar 0.5) | 10/13 | 12/13 | 0/4 |
| Híbrida (limiar 0.5) | 10/13 | 12/13 | 1/4 |

O conjunto de avaliação é pequeno e feito à mão, então os números servem para comparar métodos, não como medida absoluta. O limiar de similaridade (0.5) foi escolhido nesse mesmo conjunto, então o resultado provavelmente está otimista; com 0.6 a busca começa a perder acertos (hit@1 cai para 7/13).

## Limitações conhecidas

- A detecção de idioma é uma heurística (português do Brasil, inglês e espanhol). Mensagens fixas do sistema, como confirmações, existem só em português e inglês.
- A Safety Layer roda no mesmo processo do restante da AISSY: protege contra erros do modelo e prompt injection, não contra código malicioso com os mesmos privilégios. Confirmação genérica, permissões por pasta, backups e sandbox ainda não existem.
- Os avisos de lembrete só acontecem com a AISSY aberta; no modo texto, só aparecem depois que você aperta Enter.
- Abrir aplicativos só funciona no Windows e apenas para apps da lista permitida.
- O `OpenAIProvider` não foi validado com chamadas reais.
- É um projeto de uso pessoal, para um único usuário e sem autenticação.
- Modelos locais de 7B erram às vezes, inclusive ao decidir quando chamar uma ferramenta. Por isso pedidos claros de lembrete são interpretados por regras em código, e uma trava substitui respostas que dizem "anotei" sem que nada tenha sido salvo.
- O modelo precisa suportar tool calling no Ollama. O `gemma3:12b`, por exemplo, retornou erro 400 nos testes e não funcionou.
- A voz do Windows é robótica e só há uma voz feminina em português instalada por padrão.
- O reconhecimento de fala (`faster-whisper` small) às vezes erra palavras.

## Licença

Ainda não definida.
