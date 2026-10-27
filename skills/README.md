# Skills de automação do Instagram para o Claude

Duas skills que se complementam:

| Skill | Como funciona | Para quê |
|---|---|---|
| `instagram-api` | API oficial da Meta (Graph API) | Postar (foto, carrossel, reels, story), métricas, responder comentários e DMs. Sem risco de bloqueio. |
| `instagram-celular` | Script no terminal que simula o app Android (instagrapi) | Seguir, curtir, comentar em outros perfis, DM para qualquer pessoa, inbox, stories, hashtags, postar direto do arquivo. |

## Instalar

**Claude Code (terminal/desktop)** — copie as pastas para as skills do usuário:
```bash
mkdir -p ~/.claude/skills
cp -r instagram-api instagram-celular ~/.claude/skills/
pip install -U instagrapi pillow     # só a skill instagram-celular precisa
```
(Ou dentro de um projeto: `.claude/skills/`.)

**claude.ai / app Claude** — Configurações → Capacidades → Skills → *Enviar skill* e envie
`instagram-api.zip` e `instagram-celular.zip` (um de cada vez). O ambiente precisa ter execução de
código e acesso à internet liberado.

## Primeiro uso
Peça ao Claude: *"configure o Instagram pela API"* e depois *"faça login no Instagram como celular"*.
Ele segue os passos de cada SKILL.md e pede só o que for manual (token da Meta, senha, código).

Requisitos: Python 3.9+. Credenciais ficam em `~/.ig_api/` e `~/.ig_celular/` (nunca versionar).
