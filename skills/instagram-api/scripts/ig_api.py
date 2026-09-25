#!/usr/bin/env python3
"""
ig_api.py — Instagram pela API OFICIAL da Meta (Graph API), só com a biblioteca padrão do Python.

Configuração (variáveis de ambiente ou arquivo ~/.ig_api/config.env):
  IG_ACCESS_TOKEN   token de longa duração (obrigatório)
  IG_USER_ID        id da conta profissional (opcional; descoberto via /me)
  IG_GRAPH_HOST     graph.instagram.com (padrão, "Instagram Login")
                    ou graph.facebook.com ("Facebook Login", conta ligada a Página)
  IG_API_VERSION    padrão v23.0
  GITHUB_TOKEN      para hospedar mídia local num repositório público (comando `hospedar`)
  GITHUB_REPO       dono/repositorio (ex.: fulano/ig-midia)
  GITHUB_BRANCH     padrão main

Toda saída é JSON no stdout. Código de saída != 0 em caso de erro.
"""
import argparse
import base64
import json
import mimetypes
import os
import pathlib
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

CONFIG_DIR = pathlib.Path.home() / ".ig_api"
CONFIG_FILE = CONFIG_DIR / "config.env"


# ---------------------------------------------------------------- config
def carregar_config():
    if CONFIG_FILE.exists():
        for linha in CONFIG_FILE.read_text().splitlines():
            linha = linha.strip()
            if not linha or linha.startswith("#") or "=" not in linha:
                continue
            k, v = linha.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def salvar_config(chave, valor):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    linhas = CONFIG_FILE.read_text().splitlines() if CONFIG_FILE.exists() else []
    linhas = [l for l in linhas if not l.startswith(chave + "=")]
    linhas.append(f"{chave}={valor}")
    CONFIG_FILE.write_text("\n".join(linhas) + "\n")
    os.chmod(CONFIG_FILE, 0o600)
    os.environ[chave] = valor


def env(nome, padrao=None, obrigatorio=False):
    v = os.environ.get(nome, padrao)
    if obrigatorio and not v:
        falhar(f"Variável {nome} não configurada. Rode: ig_api.py config {nome} <valor>")
    return v


def saida(obj):
    print(json.dumps(obj, ensure_ascii=False, indent=2, default=str))


class ErroIG(Exception):
    def __init__(self, msg, extra=None):
        super().__init__(msg)
        self.extra = extra


def falhar(msg, extra=None):
    raise ErroIG(msg, extra)


# ---------------------------------------------------------------- http
def http(metodo, url, params=None, corpo=None, headers=None):
    if params:
        url += ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
    dados = None
    headers = dict(headers or {})
    if corpo is not None:
        if isinstance(corpo, (dict, list)) and headers.get("Content-Type") == "application/json":
            dados = json.dumps(corpo).encode()
        else:
            dados = urllib.parse.urlencode(corpo).encode()
    req = urllib.request.Request(url, data=dados, method=metodo, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            txt = r.read().decode()
            return json.loads(txt) if txt else {}
    except urllib.error.HTTPError as e:
        txt = e.read().decode(errors="replace")
        try:
            detalhe = json.loads(txt)
        except Exception:
            detalhe = txt
        falhar(f"HTTP {e.code} em {metodo} {url.split('?')[0]}", detalhe)


def graph(metodo, caminho, **params):
    host = env("IG_GRAPH_HOST", "graph.instagram.com")
    versao = env("IG_API_VERSION", "v23.0")
    params["access_token"] = env("IG_ACCESS_TOKEN", obrigatorio=True)
    url = f"https://{host}/{versao}/{caminho.lstrip('/')}"
    if metodo == "GET":
        return http("GET", url, params=params)
    return http(metodo, url, corpo=params)


def user_id():
    uid = env("IG_USER_ID")
    if uid:
        return uid
    host = env("IG_GRAPH_HOST", "graph.instagram.com")
    if "facebook" in host:
        falhar("Com graph.facebook.com defina IG_USER_ID (id da conta IG ligada à Página).")
    me = graph("GET", "me", fields="user_id,username")
    uid = me.get("user_id") or me.get("id")
    salvar_config("IG_USER_ID", uid)
    return uid


# ---------------------------------------------------------------- publicação
def aguardar_container(cid, limite=600):
    inicio = time.time()
    while True:
        st = graph("GET", cid, fields="status_code,status")
        code = st.get("status_code")
        if code == "FINISHED":
            return st
        if code in ("ERROR", "EXPIRED"):
            falhar(f"Container {cid} falhou: {code}", st)
        if time.time() - inicio > limite:
            falhar(f"Container {cid} não terminou em {limite}s", st)
        time.sleep(5)


def url_da_midia(origem):
    """Aceita URL pública ou caminho local (que é hospedado no GitHub)."""
    if origem.startswith("http://") or origem.startswith("https://"):
        return origem
    return hospedar_arquivo(origem)["url"]


def eh_video(origem):
    return origem.lower().split("?")[0].endswith((".mp4", ".mov"))


def criar_container(**params):
    r = graph("POST", f"{user_id()}/media", **params)
    return r["id"]


def publicar(cid):
    aguardar_container(cid)
    r = graph("POST", f"{user_id()}/media_publish", creation_id=cid)
    mid = r["id"]
    info = graph("GET", mid, fields="id,permalink,media_type,timestamp")
    return {"ok": True, "media_id": mid, **info}


def cmd_post(a):
    u = url_da_midia(a.midia)
    if eh_video(u):
        cid = criar_container(media_type="REELS", video_url=u, caption=a.legenda or "")
    else:
        cid = criar_container(image_url=u, caption=a.legenda or "")
    saida(publicar(cid))


def cmd_reels(a):
    params = dict(media_type="REELS", video_url=url_da_midia(a.video), caption=a.legenda or "",
                  share_to_feed="true" if not a.so_reels else "false")
    if a.capa:
        params["cover_url"] = url_da_midia(a.capa)
    saida(publicar(criar_container(**params)))


def cmd_carrossel(a):
    if not 2 <= len(a.midias) <= 10:
        falhar("Carrossel precisa de 2 a 10 mídias.")
    filhos = []
    for m in a.midias:
        u = url_da_midia(m)
        if eh_video(u):
            cid = criar_container(media_type="VIDEO", video_url=u, is_carousel_item="true")
        else:
            cid = criar_container(image_url=u, is_carousel_item="true")
        aguardar_container(cid)
        filhos.append(cid)
    cid = criar_container(media_type="CAROUSEL", children=",".join(filhos), caption=a.legenda or "")
    saida(publicar(cid))


def cmd_story(a):
    u = url_da_midia(a.midia)
    chave = "video_url" if eh_video(u) else "image_url"
    saida(publicar(criar_container(media_type="STORIES", **{chave: u})))


# ---------------------------------------------------------------- leitura / interação
def cmd_eu(a):
    host = env("IG_GRAPH_HOST", "graph.instagram.com")
    if "facebook" in host:
        r = graph("GET", user_id(), fields="id,username,name,followers_count,follows_count,media_count")
    else:
        r = graph("GET", "me", fields="user_id,username,name,account_type,followers_count,follows_count,media_count")
    saida({"ok": True, **r})


def cmd_posts(a):
    r = graph("GET", f"{user_id()}/media", limit=a.limite,
              fields="id,caption,media_type,permalink,timestamp,like_count,comments_count")
    saida({"ok": True, "posts": r.get("data", [])})


def cmd_insights(a):
    if a.media_id:
        r = graph("GET", f"{a.media_id}/insights", metric=a.metricas or "reach,likes,comments,saved,shares,views")
    else:
        r = graph("GET", f"{user_id()}/insights", metric=a.metricas or "reach,follower_count",
                  period=a.periodo)
    saida({"ok": True, "insights": r.get("data", r)})


def cmd_comentarios(a):
    r = graph("GET", f"{a.media_id}/comments", fields="id,text,username,timestamp,replies{id,text,username}",
              limit=a.limite)
    saida({"ok": True, "comentarios": r.get("data", [])})


def cmd_responder(a):
    r = graph("POST", f"{a.comentario_id}/replies", message=a.texto)
    saida({"ok": True, **r})


def cmd_comentar(a):
    r = graph("POST", f"{a.media_id}/comments", message=a.texto)
    saida({"ok": True, **r})


def cmd_ocultar(a):
    r = graph("POST", a.comentario_id, hide="false" if a.mostrar else "true")
    saida({"ok": True, **r})


def cmd_conversas(a):
    params = dict(fields="id,updated_time,participants,messages.limit(5){id,from,message,created_time}")
    if "facebook" in env("IG_GRAPH_HOST", "graph.instagram.com"):
        params["platform"] = "instagram"
    r = graph("GET", f"{user_id()}/conversations", **params)
    saida({"ok": True, "conversas": r.get("data", [])})


def cmd_dm(a):
    host = env("IG_GRAPH_HOST", "graph.instagram.com")
    versao = env("IG_API_VERSION", "v23.0")
    url = f"https://{host}/{versao}/{user_id()}/messages"
    corpo = {"recipient": {"id": a.destinatario_id}, "message": {"text": a.texto}}
    r = http("POST", url, corpo=corpo, headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {env('IG_ACCESS_TOKEN', obrigatorio=True)}"})
    saida({"ok": True, **r})


def cmd_limite(a):
    r = graph("GET", f"{user_id()}/content_publishing_limit", fields="config,quota_usage")
    saida({"ok": True, **r})


def cmd_renovar(a):
    host = env("IG_GRAPH_HOST", "graph.instagram.com")
    if "facebook" in host:
        falhar("Renovação automática só no Instagram Login. No Facebook Login gere token de Página (não expira).")
    r = http("GET", "https://graph.instagram.com/refresh_access_token",
             params={"grant_type": "ig_refresh_token", "access_token": env("IG_ACCESS_TOKEN", obrigatorio=True)})
    salvar_config("IG_ACCESS_TOKEN", r["access_token"])
    saida({"ok": True, "expira_em_dias": round(r.get("expires_in", 0) / 86400, 1)})


# ---------------------------------------------------------------- hospedagem (GitHub)
def hospedar_arquivo(caminho, destino=None):
    p = pathlib.Path(caminho).expanduser()
    if not p.is_file():
        falhar(f"Arquivo não encontrado: {p}")
    repo = env("GITHUB_REPO", obrigatorio=True)
    branch = env("GITHUB_BRANCH", "main")
    token = env("GITHUB_TOKEN", obrigatorio=True)
    if p.stat().st_size > 95 * 1024 * 1024:
        falhar("Arquivo maior que 95 MB; comprima antes (ffmpeg).")
    destino = destino or f"posts/{time.strftime('%Y-%m-%d')}/{int(time.time())}-{p.name}"
    url = f"https://api.github.com/repos/{repo}/contents/{urllib.parse.quote(destino)}"
    corpo = {"message": f"Mídia {destino}", "branch": branch,
             "content": base64.b64encode(p.read_bytes()).decode()}
    http("PUT", url, corpo=corpo, headers={
        "Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
        "Content-Type": "application/json", "User-Agent": "ig-api-skill"})
    raw = f"https://raw.githubusercontent.com/{repo}/{branch}/{urllib.parse.quote(destino)}"
    # espera o raw ficar acessível (CDN)
    for _ in range(12):
        try:
            with urllib.request.urlopen(urllib.request.Request(raw, method="HEAD"), timeout=20) as r:
                if r.status == 200:
                    break
        except Exception:
            time.sleep(5)
    return {"ok": True, "url": raw, "caminho": destino,
            "tipo": mimetypes.guess_type(p.name)[0]}


def cmd_hospedar(a):
    saida(hospedar_arquivo(a.arquivo, a.destino))


def cmd_config(a):
    salvar_config(a.chave, a.valor)
    saida({"ok": True, "salvo": a.chave, "arquivo": str(CONFIG_FILE)})


def cmd_diagnostico(a):
    res = {"config_arquivo": str(CONFIG_FILE), "host": env("IG_GRAPH_HOST", "graph.instagram.com"),
           "token": bool(env("IG_ACCESS_TOKEN")), "github_repo": env("GITHUB_REPO"),
           "github_token": bool(env("GITHUB_TOKEN"))}
    if res["token"]:
        try:
            host = res["host"]
            if "facebook" in host:
                res["conta"] = graph("GET", user_id(), fields="id,username")
            else:
                res["conta"] = graph("GET", "me", fields="user_id,username,account_type")
        except ErroIG as e:
            res["conta"] = {"erro": str(e), "detalhe": e.extra}
    saida({"ok": True, **res})


# ---------------------------------------------------------------- CLI
def main():
    carregar_config()
    p = argparse.ArgumentParser(description="Instagram via API oficial (Graph API)")
    s = p.add_subparsers(dest="cmd", required=True)

    x = s.add_parser("config", help="salva uma variável em ~/.ig_api/config.env"); x.add_argument("chave"); x.add_argument("valor"); x.set_defaults(f=cmd_config)
    s.add_parser("diagnostico", help="checa token e conta").set_defaults(f=cmd_diagnostico)
    s.add_parser("eu", help="dados da conta").set_defaults(f=cmd_eu)
    s.add_parser("limite", help="cota de publicação (100 posts/24h)").set_defaults(f=cmd_limite)
    s.add_parser("renovar-token", help="renova token de 60 dias").set_defaults(f=cmd_renovar)

    x = s.add_parser("hospedar", help="sobe arquivo local ao GitHub e devolve URL pública"); x.add_argument("arquivo"); x.add_argument("--destino"); x.set_defaults(f=cmd_hospedar)
    x = s.add_parser("post", help="foto (ou vídeo vira reels) no feed"); x.add_argument("midia"); x.add_argument("--legenda", "-l"); x.set_defaults(f=cmd_post)
    x = s.add_parser("reels"); x.add_argument("video"); x.add_argument("--legenda", "-l"); x.add_argument("--capa"); x.add_argument("--so-reels", action="store_true"); x.set_defaults(f=cmd_reels)
    x = s.add_parser("carrossel"); x.add_argument("midias", nargs="+"); x.add_argument("--legenda", "-l"); x.set_defaults(f=cmd_carrossel)
    x = s.add_parser("story"); x.add_argument("midia"); x.set_defaults(f=cmd_story)

    x = s.add_parser("posts", help="lista posts recentes"); x.add_argument("--limite", type=int, default=10); x.set_defaults(f=cmd_posts)
    x = s.add_parser("insights"); x.add_argument("--media-id"); x.add_argument("--metricas"); x.add_argument("--periodo", default="day"); x.set_defaults(f=cmd_insights)
    x = s.add_parser("comentarios"); x.add_argument("media_id"); x.add_argument("--limite", type=int, default=50); x.set_defaults(f=cmd_comentarios)
    x = s.add_parser("comentar"); x.add_argument("media_id"); x.add_argument("texto"); x.set_defaults(f=cmd_comentar)
    x = s.add_parser("responder", help="responde um comentário"); x.add_argument("comentario_id"); x.add_argument("texto"); x.set_defaults(f=cmd_responder)
    x = s.add_parser("ocultar", help="oculta (ou --mostrar) um comentário"); x.add_argument("comentario_id"); x.add_argument("--mostrar", action="store_true"); x.set_defaults(f=cmd_ocultar)
    s.add_parser("conversas", help="lista DMs (precisa permissão de mensagens)").set_defaults(f=cmd_conversas)
    x = s.add_parser("dm", help="responde DM (janela de 24h)"); x.add_argument("destinatario_id"); x.add_argument("texto"); x.set_defaults(f=cmd_dm)

    a = p.parse_args()
    try:
        a.f(a)
    except ErroIG as e:
        saida({"ok": False, "erro": str(e), **({"detalhe": e.extra} if e.extra else {})})
        sys.exit(1)


if __name__ == "__main__":
    main()
