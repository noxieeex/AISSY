# AISSY

Assistente pessoal em Python, feita para rodar **localmente** (via Ollama), com conversa em português, inglês e espanhol, memória de longo prazo e uso de ferramentas (tool calling). É um projeto pessoal, em desenvolvimento contínuo.

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
- Erros de ferramentas voltam ao modelo como resultado, em vez de derrubar a conversa. A data e a hora atuais entram no contexto de cada resposta.
- Mensagem amigável quando o Ollama está fora do ar.
- Script de avaliação que compara busca por palavras, busca semântica e busca híbrida em um conjunto de perguntas.
- Suíte de testes automatizados com `pytest`, usando LLM e embedder falsos, sem depender de GPU.

### Em desenvolvimento

- Persona e tom de voz da AISSY (ajuste fino).
- Notificações de lembretes no horário combinado (hoje só aparecem no resumo).

### Ideias (não implementadas)

- Voz (reconhecimento e síntese de fala).
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
  tasks.py                  tarefas e lembretes (SQLite)
  briefing.py               resumo do dia
  commands.py               comandos /hoje, /tarefas, /feito, /apagar
  errors.py                 erros próprios da aplicação
  providers/
    ollama_provider.py      LLM local
    openai_provider.py      LLM em nuvem (não validado)
evaluation/                 avaliação da recuperação de memórias
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
| Semântica | _a preencher_ | _a preencher_ | _a preencher_ |
| Híbrida | _a preencher_ | _a preencher_ | _a preencher_ |

O conjunto de avaliação é pequeno e feito à mão, então os números servem para comparar métodos, não como medida absoluta.

## Limitações conhecidas

- A detecção de idioma é uma heurística (português do Brasil, inglês e espanhol). Mensagens fixas do sistema, como confirmações, existem só em português e inglês.
- Lembretes não disparam notificação no horário; aparecem no resumo do dia.
- O `OpenAIProvider` não foi validado com chamadas reais.
- É um projeto de uso pessoal, para um único usuário e sem autenticação.
- Modelos locais de 7B erram às vezes, inclusive ao decidir quando chamar uma ferramenta.

## Licença

Ainda não definida.
