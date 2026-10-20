---
name: instagram-celular
description: Controla uma conta do Instagram pelo terminal como se fosse o APP DO CELULAR (simula um Android via instagrapi) — seguir e deixar de seguir, curtir, comentar em posts de outras pessoas, mandar e ler DMs de qualquer pessoa, ver inbox e solicitações, ver stories, feed, perfis, seguidores, buscar hashtag e também postar foto/carrossel/reels/story direto de arquivo local. Use quando o usuário pedir para o Claude "usar o Instagram como celular", interagir com outros perfis, prospectar, responder direct, engajar, ou quando algo não é possível pela API oficial (skill instagram-api).
---

# Instagram "como celular" (instagrapi)

O script `scripts/ig_celular.py` faz login como um celular Android e fala com os mesmos servidores
que o app usa. Isso dá autonomia total, mas **não é oficial**: o Instagram pode pedir verificação ou
bloquear ações se o uso parecer robô. Siga as regras da seção 4 à risca.

```bash
CEL="python3 <pasta-desta-skill>/scripts/ig_celular.py"
```

## 1. Instalação (uma vez)

```bash
pip install -U instagrapi pillow      # (se precisar: pip install --user ... ou use um venv)
$CEL config IG_USERNAME "usuario_sem_arroba"
$CEL config IG_PASSWORD "senha"
# opcional, se a conta tem 2FA por app autenticador (chave base32 mostrada ao ativar o 2FA):
$CEL config IG_TOTP_SEED "ABCD EFGH ..."
# opcional, recomendado se o Claude roda na nuvem (IP de datacenter é suspeito):
$CEL config IG_PROXY "http://user:senha@proxy-residencial-br:porta"
```

Tudo fica em `~/.ig_celular/` (config com permissão 600 + sessão + contador diário).

## 2. Login

Rode **em segundo plano**, porque o Instagram pode pedir um código:

```bash
$CEL login
```

- Se o stderr mostrar `"aguardando_codigo": true`, peça ao usuário o código que chegou por
  e-mail/SMS e grave: `echo 123456 > ~/.ig_celular/codigo.txt` (o script espera 10 min).
- Se pedir "Foi você?", o usuário deve abrir o app no celular, tocar **"Fui eu"**, e rodar `login` de novo.
- Se der **"versão do Instagram desatualizada"** (ou qualquer bloqueio de login por senha), use o
  **Plano B – sessionid**: o usuário entra no instagram.com pelo navegador, abre F12 → Application
  (Aplicativo) → Cookies → `https://www.instagram.com` → copia o valor de `sessionid`. Então:
  ```bash
  $CEL sair
  $CEL config IG_SESSIONID "<valor copiado>"
  $CEL login
  ```
- Depois do primeiro login a sessão é reutilizada; **não** faça login repetido sem necessidade e
  nunca apague `~/.ig_celular/sessao-*.json` à toa (ela guarda o "aparelho").

## 3. Comandos

| O que | Comando |
|---|---|
| Meu perfil / perfil de alguém | `$CEL perfil` / `$CEL perfil @fulano` |
| Posts de alguém | `$CEL posts-de @fulano --qtd 12` |
| Feed inicial | `$CEL feed --qtd 20` |
| Postar foto / reels | `$CEL postar arquivo.jpg -l "legenda"` (mp4 vira reels) |
| Carrossel | `$CEL postar 1.jpg 2.jpg 3.jpg -l "legenda"` |
| Story | `$CEL story arte.jpg` |
| Seguir / deixar de seguir | `$CEL seguir @a @b` / `$CEL deixar-de-seguir @a` |
| Curtir (URL, pk ou id) | `$CEL curtir https://www.instagram.com/p/XXXX/` (`--desfazer`) |
| Comentar / responder | `$CEL comentar <url> "texto" [--responder-a <comentario_pk>]` |
| Ler comentários | `$CEL comentarios <url> --qtd 30` |
| Mandar DM | `$CEL dm "texto" --para @fulano` ou `--thread <id>` |
| Inbox | `$CEL inbox [--nao-lidas] [--pendentes]` |
| Ler uma conversa | `$CEL conversa <thread_id> --qtd 30` |
| Seguidores / seguindo | `$CEL seguidores [@fulano] --qtd 100 [--seguindo]` |
| Hashtag (recentes) | `$CEL hashtag marketingdigital --qtd 20` |
| Stories de alguém | `$CEL stories-de @fulano [--marcar-vistos]` |
| Uso de hoje vs. limite | `$CEL limites` |
| Apagar sessão | `$CEL sair` |

Opção global `--forcar` ignora o limite diário (use só se o usuário pedir explicitamente).

## 4. Regras de segurança (obrigatórias)

1. **Respeite os limites diários** do script (seguir 60, curtir 150, comentar 30, DM 40, post 5,
   story 15). Conta nova (<3 meses) ou recém-bloqueada: metade. Ajuste com
   `$CEL config IG_LIMITE_SEGUIR 30` etc.
2. **Espalhe as ações no dia.** Nada de 40 DMs em 5 minutos: faça em lotes de 5–10 com intervalos
   de 10–30 min. O script já espera 20–60 s entre follows em lote.
3. **Varie o texto** de DMs e comentários (personalize com nome/assunto do post). Mensagens idênticas
   em massa = bloqueio.
4. Ao receber `FeedbackRequired` ou "Action Blocked": **pare tudo por 24–48 h** e avise o usuário.
   `PleaseWaitFewMinutes`: espere 30 min.
5. Não faça login em várias contas do mesmo IP; uma sessão por conta.
6. Sempre confirme com o usuário antes de ações em massa (>10 pessoas) e mostre um resumo no fim.

## 5. Quando usar qual skill

- **instagram-api** (oficial): publicar conteúdo da marca, métricas, responder comentários e DMs
  recebidas. Zero risco de bloqueio → prefira para publicar.
- **instagram-celular** (esta): tudo que envolve **outras contas** — seguir, curtir, comentar fora,
  DM ativa, ler inbox completa, pesquisar perfis/hashtags; ou postar sem precisar hospedar mídia.

Detalhes de erros e boas práticas: **references/seguranca.md**.
