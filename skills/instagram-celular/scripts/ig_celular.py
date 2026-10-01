#!/usr/bin/env python3
"""
ig_celular.py — controla uma conta do Instagram pelo terminal se passando pelo APP DE CELULAR
(Android), usando a biblioteca instagrapi (API privada do app).

Isso dá ao Claude o que a API oficial não dá: seguir, curtir, comentar em posts de terceiros,
mandar DM para qualquer pessoa, ler a inbox inteira, ver stories, buscar hashtag, etc.

Instalação:  pip install -U instagrapi pillow

Credenciais (variáveis de ambiente ou ~/.ig_celular/config.env):
  IG_USERNAME, IG_PASSWORD
  IG_TOTP_SEED   (opcional) chave do app autenticador para 2FA automático
  IG_PROXY       (opcional) http://user:senha@host:porta — proxy residencial/4G do Brasil
  IG_SESSIONID   (opcional, PLANO B) cookie "sessionid" copiado do navegador logado no
                 instagram.com — evita login por senha (útil se aparecer "versão desatualizada")
  IG_APP_VERSION, IG_VERSION_CODE, IG_BLOKS_ID  (opcional) força outra versão do app Android

Sessão e "aparelho" ficam em ~/.ig_celular/sessao-<usuario>.json. O mesmo aparelho é reutilizado
sempre (trocar de aparelho a cada login é o que mais gera bloqueio).

Códigos de verificação (desafio por e-mail/SMS): o script espera até 10 min pelo arquivo
~/.ig_celular/codigo.txt. Quem estiver operando escreve o código lá:
    echo 123456 > ~/.ig_celular/codigo.txt

Toda saída é JSON no stdout.
"""
import argparse
import datetime
import json
import os
import pathlib
import random
import sys
import time

BASE = pathlib.Path(os.environ.get("IG_CELULAR_DIR", pathlib.Path.home() / ".ig_celular"))
CONFIG_FILE = BASE / "config.env"
CODIGO_FILE = BASE / "codigo.txt"
CONTADOR_FILE = BASE / "contador.json"

# Limites diários conservadores (conta com meses de uso). Conta nova: use metade.
LIMITES = {"seguir": 60, "deixar_de_seguir": 60, "curtir": 150, "comentar": 30,
           "dm": 40, "post": 5, "story": 15}


class ErroIG(Exception):
    pass


def saida(obj):
    print(json.dumps(obj, ensure_ascii=False, indent=2, default=str))


def carregar_config():
    if CONFIG_FILE.exists():
        for linha in CONFIG_FILE.read_text().splitlines():
            linha = linha.strip()
            if linha and not linha.startswith("#") and "=" in linha:
                k, v = linha.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def salvar_config(chave, valor):
    BASE.mkdir(parents=True, exist_ok=True)
    linhas = CONFIG_FILE.read_text().splitlines() if CONFIG_FILE.exists() else []
    linhas = [l for l in linhas if not l.startswith(chave + "=")] + [f"{chave}={valor}"]
    CONFIG_FILE.write_text("\n".join(linhas) + "\n")
    os.chmod(CONFIG_FILE, 0o600)


# ---------------------------------------------------------------- limites
def contar(acao, forcar=False):
    hoje = datetime.date.today().isoformat()
    dados = json.loads(CONTADOR_FILE.read_text()) if CONTADOR_FILE.exists() else {}
    if dados.get("dia") != hoje:
        dados = {"dia": hoje}
    usado = dados.get(acao, 0)
    limite = int(os.environ.get(f"IG_LIMITE_{acao.upper()}", LIMITES[acao]))
    if usado >= limite and not forcar:
        raise ErroIG(f"Limite diário de '{acao}' atingido ({usado}/{limite}). "
                     f"Espere até amanhã ou use --forcar (arrisca bloqueio).")
    dados[acao] = usado + 1
    BASE.mkdir(parents=True, exist_ok=True)
    CONTADOR_FILE.write_text(json.dumps(dados))


def pausa_humana(minimo=3, maximo=9):
    time.sleep(random.uniform(minimo, maximo))


# ---------------------------------------------------------------- login
def handler_codigo(username, choice=None):
    BASE.mkdir(parents=True, exist_ok=True)
    if CODIGO_FILE.exists():
        CODIGO_FILE.unlink()
    print(json.dumps({"aguardando_codigo": True, "via": str(choice), "usuario": username,
                      "instrucao": f"Escreva o código recebido em {CODIGO_FILE}"}), file=sys.stderr, flush=True)
    fim = time.time() + 600
    while time.time() < fim:
        if CODIGO_FILE.exists():
            codigo = CODIGO_FILE.read_text().strip()
            if codigo:
                CODIGO_FILE.unlink()
                return codigo
        time.sleep(3)
    raise ErroIG("Tempo esgotado esperando o código de verificação.")


def cliente(logar=True):
    try:
        from instagrapi import Client
        from instagrapi.exceptions import LoginRequired
    except ImportError:
        raise ErroIG("instagrapi não instalado. Rode: pip install -U instagrapi pillow")

    usuario = os.environ.get("IG_USERNAME")
    senha = os.environ.get("IG_PASSWORD")
    sessionid = os.environ.get("IG_SESSIONID")
    if not usuario or not (senha or sessionid):
        raise ErroIG("Configure IG_USERNAME e IG_PASSWORD (ou IG_SESSIONID). "
                     "Ex.: ig_celular.py config IG_USERNAME fulano")

    import logging
    logging.getLogger("instagrapi").setLevel(logging.DEBUG if os.environ.get("IG_DEBUG") else logging.CRITICAL)
    logging.getLogger("private_request").setLevel(logging.CRITICAL)
    logging.getLogger("public_request").setLevel(logging.CRITICAL)

    BASE.mkdir(parents=True, exist_ok=True)
    sessao = BASE / f"sessao-{usuario}.json"

    cl = Client()
    cl.delay_range = [2, 6]
    cl.challenge_code_handler = handler_codigo
    if os.environ.get("IG_PROXY"):
        cl.set_proxy(os.environ["IG_PROXY"])

    if sessao.exists():
        cl.load_settings(sessao)
    else:
        cl.set_locale("pt_BR")
        cl.set_country("BR")
        cl.set_country_code(55)
        cl.set_timezone_offset(-3 * 3600)
        if os.environ.get("IG_APP_VERSION"):
            dev = dict(cl.device_settings)
            dev["app_version"] = os.environ["IG_APP_VERSION"]
            dev["version_code"] = os.environ.get("IG_VERSION_CODE", dev["version_code"])
            dev["bloks_versioning_id"] = os.environ.get("IG_BLOKS_ID", dev["bloks_versioning_id"])
            cl.set_device(dev)

    if not logar:
        return cl

    def codigo_2fa():
        seed = os.environ.get("IG_TOTP_SEED")
        return cl.totp_generate_code(seed) if seed else ""

    if sessionid and not sessao.exists():
        cl.login_by_sessionid(sessionid)
    elif sessao.exists():
        try:
            cl.login(usuario, senha, verification_code=codigo_2fa())
            cl.get_timeline_feed()  # valida a sessão como o app faria ao abrir
        except LoginRequired:
            if not senha:
                raise ErroIG("Sessão expirou. Copie um novo sessionid do navegador e rode: "
                             "ig_celular.py sair && ig_celular.py config IG_SESSIONID <valor> && ig_celular.py login")
            antigo = cl.get_settings()
            cl.set_settings({})
            cl.set_uuids(antigo["uuids"])  # mantém o mesmo "aparelho"
            cl.login(usuario, senha, verification_code=codigo_2fa())
    else:
        cl.login(usuario, senha, verification_code=codigo_2fa())
    cl.dump_settings(sessao)
    return cl


def uid(cl, alvo):
    alvo = alvo.lstrip("@")
    return alvo if alvo.isdigit() else cl.user_id_from_username(alvo)


def media_id(cl, alvo):
    if alvo.startswith("http"):
        return cl.media_id(cl.media_pk_from_url(alvo))
    return alvo if "_" in alvo else cl.media_id(alvo)


def resumo_media(m):
    return {"pk": m.pk, "id": m.id, "code": m.code, "url": f"https://www.instagram.com/p/{m.code}/",
            "tipo": m.media_type, "legenda": (m.caption_text or "")[:300],
            "curtidas": m.like_count, "comentarios": m.comment_count, "data": m.taken_at,
            "autor": m.user.username if m.user else None}


def resumo_user(u):
    d = u.model_dump() if hasattr(u, "model_dump") else dict(u)
    campos = ["pk", "username", "full_name", "is_private", "is_verified", "follower_count",
              "following_count", "media_count", "biography", "external_url", "is_business"]
    return {k: d.get(k) for k in campos if k in d}


# ---------------------------------------------------------------- comandos
def c_config(a):
    salvar_config(a.chave, a.valor)
    return {"salvo": a.chave, "arquivo": str(CONFIG_FILE)}


def c_login(a):
    cl = cliente()
    info = cl.account_info()
    return {"logado": True, "usuario": info.username, "pk": info.pk,
            "sessao": str(BASE / f"sessao-{os.environ['IG_USERNAME']}.json")}


def c_perfil(a):
    cl = cliente()
    return resumo_user(cl.user_info_by_username(a.usuario.lstrip("@"), use_cache=False)) if a.usuario \
        else resumo_user(cl.user_info(cl.user_id))


def c_posts_de(a):
    cl = cliente()
    return {"posts": [resumo_media(m) for m in cl.user_medias(uid(cl, a.usuario), amount=a.qtd)]}


def c_feed(a):
    cl = cliente()
    r = cl.get_timeline_feed()
    itens = []
    for it in r.get("feed_items", []):
        m = it.get("media_or_ad")
        if m and not m.get("injected"):
            itens.append({"pk": m.get("pk"), "id": m.get("id"), "code": m.get("code"),
                          "autor": (m.get("user") or {}).get("username"),
                          "legenda": ((m.get("caption") or {}).get("text") or "")[:200],
                          "curtidas": m.get("like_count")})
    return {"feed": itens[: a.qtd]}


def c_postar(a):
    cl = cliente()
    contar("post", a.forcar)
    arqs = [pathlib.Path(x).expanduser() for x in a.arquivos]
    for p in arqs:
        if not p.is_file():
            raise ErroIG(f"Arquivo não encontrado: {p}")
    legenda = a.legenda or ""
    if len(arqs) > 1:
        m = cl.album_upload(arqs, legenda)
    elif arqs[0].suffix.lower() in (".mp4", ".mov"):
        m = cl.clip_upload(arqs[0], legenda)
    else:
        m = cl.photo_upload(arqs[0], legenda)
    return {"publicado": True, **resumo_media(m)}


def c_story(a):
    cl = cliente()
    contar("story", a.forcar)
    p = pathlib.Path(a.arquivo).expanduser()
    s = cl.video_upload_to_story(p) if p.suffix.lower() in (".mp4", ".mov") else cl.photo_upload_to_story(p)
    return {"publicado": True, "story_pk": s.pk, "id": s.id}


def c_seguir(a):
    cl = cliente()
    feitos = []
    for alvo in a.usuarios:
        contar("seguir", a.forcar)
        feitos.append({"usuario": alvo, "ok": cl.user_follow(uid(cl, alvo))})
        pausa_humana(20, 60) if len(a.usuarios) > 1 else None
    return {"seguidos": feitos}


def c_deixar(a):
    cl = cliente()
    feitos = []
    for alvo in a.usuarios:
        contar("deixar_de_seguir", a.forcar)
        feitos.append({"usuario": alvo, "ok": cl.user_unfollow(uid(cl, alvo))})
        pausa_humana(20, 60) if len(a.usuarios) > 1 else None
    return {"deixou_de_seguir": feitos}


def c_curtir(a):
    cl = cliente()
    contar("curtir", a.forcar)
    return {"curtido": cl.media_like(media_id(cl, a.post), revert=a.desfazer)}


def c_comentar(a):
    cl = cliente()
    contar("comentar", a.forcar)
    c = cl.media_comment(media_id(cl, a.post), a.texto,
                         replied_to_comment_id=int(a.responder_a) if a.responder_a else None)
    return {"comentario_pk": c.pk, "texto": c.text}


def c_comentarios(a):
    cl = cliente()
    cs = cl.media_comments(media_id(cl, a.post), amount=a.qtd)
    return {"comentarios": [{"pk": c.pk, "usuario": c.user.username, "texto": c.text,
                             "data": c.created_at_utc, "curtidas": c.like_count} for c in cs]}


def c_dm(a):
    cl = cliente()
    contar("dm", a.forcar)
    if a.thread:
        m = cl.direct_answer(int(a.thread), a.texto)
    else:
        m = cl.direct_send(a.texto, user_ids=[int(uid(cl, a.para))])
    return {"enviado": True, "thread_id": m.thread_id, "msg_id": m.id}


def c_inbox(a):
    cl = cliente()
    threads = cl.direct_pending_inbox(a.qtd) if a.pendentes else \
        cl.direct_threads(a.qtd, selected_filter="unread" if a.nao_lidas else None)
    out = []
    for t in threads:
        ult = t.messages[0] if t.messages else None
        out.append({"thread_id": t.id, "com": [u.username for u in t.users],
                    "ultima": getattr(ult, "text", None) if ult else None,
                    "de_mim": (str(ult.user_id) == str(cl.user_id)) if ult else None,
                    "quando": getattr(ult, "timestamp", None) if ult else None})
    return {"conversas": out}


def c_conversa(a):
    cl = cliente()
    msgs = cl.direct_messages(int(a.thread), amount=a.qtd)
    return {"mensagens": [{"id": m.id, "de_mim": str(m.user_id) == str(cl.user_id), "texto": m.text,
                           "tipo": m.item_type, "quando": m.timestamp} for m in reversed(msgs)]}


def c_seguidores(a):
    cl = cliente()
    alvo = uid(cl, a.usuario) if a.usuario else cl.user_id
    fn = cl.user_following if a.seguindo else cl.user_followers
    us = fn(alvo, amount=a.qtd)
    return {"total_retornado": len(us), "usuarios": [{"pk": u.pk, "username": u.username,
                                                      "nome": u.full_name} for u in us.values()]}


def c_hashtag(a):
    cl = cliente()
    return {"posts": [resumo_media(m) for m in cl.hashtag_medias_recent(a.tag.lstrip("#"), amount=a.qtd)]}


def c_stories_de(a):
    cl = cliente()
    ss = cl.user_stories(uid(cl, a.usuario))
    if a.marcar_vistos and ss:
        cl.story_seen([s.pk for s in ss])
    return {"stories": [{"pk": s.pk, "tipo": s.media_type, "quando": s.taken_at,
                         "url": str(s.thumbnail_url or s.video_url)} for s in ss]}


def c_limites(a):
    dados = json.loads(CONTADOR_FILE.read_text()) if CONTADOR_FILE.exists() else {}
    hoje = datetime.date.today().isoformat()
    if dados.get("dia") != hoje:
        dados = {"dia": hoje}
    return {"dia": hoje, "uso": {k: f"{dados.get(k, 0)}/{os.environ.get(f'IG_LIMITE_{k.upper()}', v)}"
                                 for k, v in LIMITES.items()}}


def c_sair(a):
    usuario = os.environ.get("IG_USERNAME", "")
    s = BASE / f"sessao-{usuario}.json"
    if s.exists():
        s.unlink()
    return {"sessao_apagada": str(s)}


# ---------------------------------------------------------------- CLI
def main():
    carregar_config()
    p = argparse.ArgumentParser(description="Instagram 'como celular' via instagrapi")
    p.add_argument("--forcar", action="store_true", help="ignora o limite diário de segurança")
    s = p.add_subparsers(dest="cmd", required=True)

    def cmd(nome, fn, ajuda=""):
        x = s.add_parser(nome, help=ajuda)
        x.set_defaults(f=fn)
        return x

    x = cmd("config", c_config, "salva variável em ~/.ig_celular/config.env"); x.add_argument("chave"); x.add_argument("valor")
    cmd("login", c_login, "faz/valida login e salva sessão")
    cmd("sair", c_sair, "apaga a sessão salva")
    cmd("limites", c_limites, "uso de hoje vs. limite de segurança")
    x = cmd("perfil", c_perfil, "dados de um perfil (sem argumento = o seu)"); x.add_argument("usuario", nargs="?")
    x = cmd("posts-de", c_posts_de); x.add_argument("usuario"); x.add_argument("--qtd", type=int, default=12)
    x = cmd("feed", c_feed, "timeline inicial"); x.add_argument("--qtd", type=int, default=20)
    x = cmd("postar", c_postar, "1 arquivo = foto/reels; vários = carrossel"); x.add_argument("arquivos", nargs="+"); x.add_argument("--legenda", "-l")
    x = cmd("story", c_story); x.add_argument("arquivo")
    x = cmd("seguir", c_seguir); x.add_argument("usuarios", nargs="+")
    x = cmd("deixar-de-seguir", c_deixar); x.add_argument("usuarios", nargs="+")
    x = cmd("curtir", c_curtir, "post por URL, pk ou id"); x.add_argument("post"); x.add_argument("--desfazer", action="store_true")
    x = cmd("comentar", c_comentar); x.add_argument("post"); x.add_argument("texto"); x.add_argument("--responder-a")
    x = cmd("comentarios", c_comentarios); x.add_argument("post"); x.add_argument("--qtd", type=int, default=30)
    x = cmd("dm", c_dm, "--para @usuario OU --thread id"); x.add_argument("texto"); x.add_argument("--para"); x.add_argument("--thread")
    x = cmd("inbox", c_inbox); x.add_argument("--qtd", type=int, default=20); x.add_argument("--nao-lidas", action="store_true"); x.add_argument("--pendentes", action="store_true", help="solicitações de mensagem")
    x = cmd("conversa", c_conversa, "mensagens de uma thread"); x.add_argument("thread"); x.add_argument("--qtd", type=int, default=30)
    x = cmd("seguidores", c_seguidores); x.add_argument("usuario", nargs="?"); x.add_argument("--qtd", type=int, default=100); x.add_argument("--seguindo", action="store_true")
    x = cmd("hashtag", c_hashtag); x.add_argument("tag"); x.add_argument("--qtd", type=int, default=20)
    x = cmd("stories-de", c_stories_de); x.add_argument("usuario"); x.add_argument("--marcar-vistos", action="store_true")

    a = p.parse_args()
    if a.cmd == "dm" and not (a.para or a.thread):
        p.error("dm precisa de --para ou --thread")
    try:
        saida({"ok": True, **a.f(a)})
    except ErroIG as e:
        saida({"ok": False, "erro": str(e)})
        sys.exit(1)
    except Exception as e:  # erros do instagrapi (ChallengeRequired, FeedbackRequired, PleaseWaitFewMinutes...)
        nome = type(e).__name__
        dica = {
            "FeedbackRequired": "Instagram bloqueou a ação temporariamente. PARE por 24-48h.",
            "PleaseWaitFewMinutes": "Muitas requisições. Espere 15-30 min.",
            "ChallengeRequired": "Abra o app no celular, confirme 'Fui eu' e rode login de novo.",
            "BadPassword": "Senha errada ou IP bloqueado. Confira a senha / use IG_PROXY.",
            "TwoFactorRequired": "Conta com 2FA: configure IG_TOTP_SEED.",
            "LoginRequired": "Sessão expirou. Rode: ig_celular.py login",
        }.get(nome, "")
        if "desatualizada" in str(e) or "out of date" in str(e) or "needs_upgrade" in str(e):
            dica = ("Instagram recusou a versão do app simulada. Plano B: faça login no instagram.com "
                    "pelo navegador, copie o cookie 'sessionid' (F12 > Application > Cookies) e rode "
                    "`ig_celular.py config IG_SESSIONID <valor>` e depois `ig_celular.py login`. "
                    "Também ajuda: pip install -U instagrapi.")
        saida({"ok": False, "erro": nome, "mensagem": str(e)[:500], "dica": dica})
        sys.exit(1)


if __name__ == "__main__":
    main()
