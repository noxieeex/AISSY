# AISSY 💗

> uma assistente pessoal que mora no meu terminal: conversa, lembra das coisas e faz (com cuidado) o que eu peço ♡

AISSY (*Living Engine*) é o meu projeto de longo prazo: uma assistente em Python que roda um modelo de linguagem **local** (via Ollama), conversa por **voz ou texto** em português, inglês e espanhol, tem **memória** e usa **ferramentas** (tool calling). É o meu projeto de longo prazo, e eu aprendo mexendo nele ♡

## Em um minuto

- 🗣️ **Fala e escuta.** Conversa por voz (com uma voz neural opcional, bem mais natural) ou por texto, e responde frase a frase enquanto pensa.
- 🧠 **Lembra.** Memória de longo prazo com busca por palavras e por significado. O que é privado nunca chega ao modelo.
- ✅ **Organiza.** Tarefas e lembretes, com resumo do dia ao abrir.
- 🛡️ **Tem limites.** Tudo o que ela *faz* passa por uma camada de segurança independente do modelo: lista do que pode, lista do que nunca pode, registro de tudo e botão de parada. Ela vive só no terminal: **não vê a tela, não mexe em outros programas e não toca em jogos nem em anti-cheat**.
- 📏 **Medida, não só "parece que funciona".** Treinei um classificador de idioma (97% de acerto contra 72% da regra antiga), comparei métodos de busca de memória e escrevi mais de 340 testes automatizados.

> Este README separa o que **existe e está testado**, o que está **em desenvolvimento** e o que é **apenas ideia**. Prefiro dizer o que ainda não funciona a prometer o que não existe.

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
- Respostas em streaming: a AISSY mostra e fala a resposta frase a frase enquanto o modelo ainda gera, em vez de esperar o texto inteiro. A trava contra "anotei" falso é aplicada frase a frase, e atalhos em código (tarefas, abrir app, memória, data) nunca são transmitidos. Lógica testada com peças falsas; falta medir o ganho no uso real.
- Classificador de idioma **treinado** (`aissy/language_model.py`, Naive Bayes sobre n-gramas de caracteres, Python puro, modelo em JSON legível). Treino e avaliação com `python -m evaluation.train_language`: no conjunto de teste acertou 97% contra 72% da heurística antiga; num conjunto extra de 45 frases curtas, escritas à parte, 93% contra 60%. Os exemplos foram escritos à mão (270 frases): é um conjunto pequeno, então os números indicam o ganho, não uma garantia. Frases de uma palavra ("ok") continuam ambíguas. Os pedidos que executam ações (lembretes, abrir apps) continuam decididos por regras em código, de propósito: um erro de classificação não pode disparar uma ação.
- Mensagem amigável quando o Ollama está fora do ar.
- Modo voz opcional e 100% local: reconhecimento de fala com `faster-whisper` e fala com as vozes do Windows (`pyttsx3`), preferindo vozes femininas. Enter começa a gravação e Enter encerra. A lógica é testada com peças falsas; o áudio em si depende de microfone e das vozes instaladas, e foi validado manualmente.
- Persona definida em `aissy/persona.py` e conferida por um script (`evaluation/persona_check.py`) que roda 11 frases no modelo e verifica idioma, frases de chatbot genérico, forma feminina, tamanho da resposta e emojis. Com `qwen2.5:7b-instruct` o resultado foi 9/11, e varia entre execuções.
- Script de avaliação que compara busca por palavras, busca semântica e busca híbrida em um conjunto de perguntas.
- Suíte de testes automatizados com `pytest`, usando LLM e embedder falsos, sem depender de GPU.

### Em desenvolvimento

- Voz neural opcional (`--voz-online` ou `AISSY_TTS=edge`, via `edge-tts`): bem mais natural que a voz do Windows, com a voz local como reserva se faltar internet. **Privacidade:** o texto das respostas da AISSY é enviado ao serviço online da Microsoft para gerar o áudio; por padrão tudo continua local. A escolha da voz e o fallback são testados; a qualidade do áudio falta validar no uso real.
- Ajuste fino da persona: o modelo de 7B ainda escorrega para frases genéricas e erros de gramática.
- Avisos de lembrete no horário (a AISSY fala ou escreve o lembrete quando vence). A lógica é testada com peças falsas; falta validar no uso real.
- Abrir aplicativos por comando de voz ou texto, só de uma lista de apps permitidos (`aissy/apps.py`, extensível em `data/apps.json`). A lógica é testada com peças falsas; falta validar no Windows.

### Ideias (não implementadas)

- Voz natural 100% local (sem enviar texto para fora), palavra de ativação e execução em segundo plano.
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

Voz neural opcional (envia o texto das respostas à Microsoft; a local continua como reserva):

```powershell
pip install -r requirements-voice-online.txt
python main.py --voz --voz-online
```

A AISSY roda só dentro do terminal/VS Code e não tem acesso ao desktop nem ao sistema.

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

- A detecção de idioma usa um classificador treinado com poucos exemplos, com as regras antigas como reserva (português do Brasil, inglês e espanhol). Mensagens fixas do sistema, como confirmações, existem só em português e inglês.
- A Safety Layer roda no mesmo processo do restante da AISSY: protege contra erros do modelo e prompt injection, não contra código malicioso com os mesmos privilégios. Confirmação genérica, permissões por pasta, backups e sandbox ainda não existem.
- Os avisos de lembrete só acontecem com a AISSY aberta; no modo texto, só aparecem depois que você aperta Enter.
- Abrir aplicativos só funciona no Windows e apenas para apps da lista permitida.
- O `OpenAIProvider` não foi validado com chamadas reais.
- É um projeto de uso pessoal, para um único usuário e sem autenticação.
- Modelos locais de 7B erram às vezes, inclusive ao decidir quando chamar uma ferramenta. Por isso pedidos claros de lembrete são interpretados por regras em código, e uma trava substitui respostas que dizem "anotei" sem que nada tenha sido salvo.
- O modelo precisa suportar tool calling no Ollama. O `gemma3:12b`, por exemplo, retornou erro 400 nos testes e não funcionou.
- A voz padrão do Windows é robótica (a neural é opcional e usa internet) e só há uma voz feminina em português instalada por padrão.
- O reconhecimento de fala (`faster-whisper` small) às vezes erra palavras.

## Licença

Copyright (c) 2026 Geovana Ribeiro Borges. Todos os direitos reservados. O código está público para leitura e avaliação; para reutilizá-lo, entre em contato.

feito uma decisão questionável de cada vez ♡
