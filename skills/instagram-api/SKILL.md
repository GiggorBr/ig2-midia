---
name: instagram-api
description: Publica e gerencia uma conta profissional do Instagram pela API OFICIAL da Meta (Graph API) — posts de foto, carrossel, reels e stories, legendas, métricas/insights, comentários (ler, responder, ocultar) e respostas de DM. Use sempre que o usuário pedir para postar, agendar, publicar, ver métricas, alcance, responder comentários ou mexer no Instagram "pela API", "de forma oficial" ou "segura". Para seguir/curtir/DM para qualquer pessoa, use a skill instagram-celular.
---

# Instagram pela API oficial (Graph API)

Tudo roda pelo script `scripts/ig_api.py` (só Python 3 padrão, sem instalar nada).
Toda saída é JSON; `"ok": false` traz `erro` e `detalhe` com a resposta da Meta.

```bash
IG="python3 <pasta-desta-skill>/scripts/ig_api.py"
```

## 1. Primeira vez: configurar

1. Rode `$IG diagnostico`. Se `token` for `false`, siga **references/configuracao.md** com o usuário
   (criar app na Meta, conta profissional, gerar token). É o único passo manual.
2. Salve os valores (ficam em `~/.ig_api/config.env`, permissão 600):
   ```bash
   $IG config IG_ACCESS_TOKEN "<token>"
   $IG config GITHUB_TOKEN "<token github com permissão de escrita no repo>"   # para hospedar mídia
   $IG config GITHUB_REPO "usuario/nome-do-repo-publico"
   ```
3. `$IG diagnostico` de novo → precisa mostrar `conta.username`.

## 2. Por que existe o `hospedar`

A API **não aceita upload de arquivo**: ela baixa a mídia de uma **URL pública**. O script resolve
sozinho: se você passar um caminho local, ele sobe o arquivo num repositório público do GitHub e usa
o link `raw.githubusercontent.com`. Se já tiver URL pública (Drive público, S3, site), passe a URL.

## 3. Comandos

| O que | Comando |
|---|---|
| Foto no feed | `$IG post foto.jpg -l "legenda #tags"` |
| Carrossel (2–10) | `$IG carrossel 1.jpg 2.jpg 3.mp4 -l "legenda"` |
| Reels | `$IG reels video.mp4 -l "legenda" [--capa capa.jpg] [--so-reels]` |
| Story | `$IG story arte.jpg` |
| Só hospedar | `$IG hospedar arquivo.jpg` → devolve `url` |
| Dados da conta | `$IG eu` |
| Últimos posts | `$IG posts --limite 10` |
| Métricas de um post | `$IG insights --media-id <id>` |
| Métricas da conta | `$IG insights --metricas reach,follower_count --periodo day` |
| Comentários | `$IG comentarios <media_id>` |
| Responder comentário | `$IG responder <comentario_id> "texto"` |
| Comentar no próprio post | `$IG comentar <media_id> "texto"` |
| Ocultar comentário | `$IG ocultar <comentario_id>` (`--mostrar` desfaz) |
| Listar DMs | `$IG conversas` |
| Responder DM | `$IG dm <id_do_usuario> "texto"` |
| Cota de publicação | `$IG limite` |
| Renovar token (60 dias) | `$IG renovar-token` |

## 4. Regras da mídia (se quebrar, a Meta devolve erro no container)

- Foto: **JPEG**, proporção entre 4:5 e 1.91:1, até 8 MB. PNG/WEBP → converta:
  `ffmpeg -i in.png -q:v 2 out.jpg` (ou Pillow).
- Reels: MP4 H.264 + AAC, 9:16 recomendado, 3 s a 15 min, até 300 MB (o GitHub aceita até ~95 MB;
  comprima: `ffmpeg -i in.mp4 -vcodec libx264 -crf 28 -preset veryfast -acodec aac out.mp4`).
- Story: foto 9:16 JPEG ou vídeo até 60 s.
- Legenda até 2.200 caracteres, no máximo 30 hashtags e 20 @menções.
- Limite: 100 publicações por 24 h (`$IG limite`).

## 5. Fluxo de trabalho recomendado

1. Antes de publicar: confira arquivo (formato/proporção) e mostre a legenda final.
2. Publique e **sempre devolva o `permalink`** ao usuário.
3. Depois de 24–48 h, use `insights` para relatar alcance, salvamentos e compartilhamentos.
4. Rotina diária sugerida: `comentarios` dos últimos posts → responder os sem resposta.
5. Uma vez por mês: `renovar-token` (o token expira em 60 dias se não for renovado).

## 6. Erros comuns

| Erro | Causa / solução |
|---|---|
| code 190 | Token inválido/expirado → gerar novo (references/configuracao.md) |
| code 10 / 200 | Falta permissão no app (`instagram_business_content_publish`, etc.) |
| `Media download has failed` / 9004 | URL não é pública ou não é JPEG. Teste a URL com `curl -I` |
| Container `ERROR` | Formato de vídeo fora do padrão → reencode com ffmpeg |
| code 4 / 32 | Muitas chamadas → espere 1 h |
| DM `outside of allowed window` | Só dá para responder até 24 h após a última mensagem da pessoa |

Se o token vier de **Facebook Login** (conta ligada a Página do Facebook), configure também
`IG_GRAPH_HOST=graph.facebook.com` e `IG_USER_ID=<id da conta IG>`.
