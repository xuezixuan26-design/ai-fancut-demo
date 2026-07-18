from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Any

from app.models.schemas import ProjectState
from app.services.aspect_ratio import output_size
from app.utils.file_utils import project_asset_dir, project_dir
from app.utils.json_utils import write_json


def export_visual_layers_project(state: ProjectState) -> dict[str, Any]:
    timeline = state.timeline or {}
    items = timeline.get("timeline", []) or []
    if not items:
        raise ValueError("Timeline not generated")

    export_dir = project_dir(state.project_id) / "hyperframes"
    export_dir.mkdir(parents=True, exist_ok=True)
    html_path = export_dir / "index.html"
    manifest_path = export_dir / "manifest.json"
    manifest = _manifest(state, timeline, items)
    write_json(manifest_path, manifest)
    html_path.write_text(_html(state, timeline, items, manifest), encoding="utf-8")
    return {
        "schema": "ai-fancut.visual-layer-export.v1",
        "project_id": state.project_id,
        "html_file": str(html_path),
        "manifest_file": str(manifest_path),
        "preview_url": f"/api/hyperframes/preview/{state.project_id}",
        "manifest_url": f"/api/hyperframes/manifest/{state.project_id}",
        "features": [
            "light_layers",
            "split_screen",
            "before_after_wipe",
            "info_panels",
            "intro_outro",
            "complex_css_animation",
            "gsap_three_lottie_mounts",
        ],
    }


def _manifest(state: ProjectState, timeline: dict[str, Any], items: list[dict[str, Any]]) -> dict[str, Any]:
    width, height = output_size(timeline.get("aspect_ratio") or state.aspect_ratio)
    families = []
    for item in items:
        source = str(item.get("source") or "")
        family = source.split("_", 1)[1] if "_" in source else source
        if family and family not in families:
            families.append(family)
    return {
        "project_id": state.project_id,
        "width": width,
        "height": height,
        "aspect_ratio": timeline.get("aspect_ratio") or state.aspect_ratio,
        "duration": timeline.get("target_duration"),
        "style": timeline.get("style") or timeline.get("title") or "AI Fancut",
        "source_families": families,
        "clip_count": len(items),
        "visual_layers": {
            "subtitle": False,
            "light_effects": True,
            "split_screen": len(families) >= 2,
            "before_after_wipe": len(families) >= 2,
            "info_panels": True,
            "intro_outro": True,
            "css_animation": True,
            "lottie_gsap_three_mounts": True,
        },
    }


def _html(state: ProjectState, timeline: dict[str, Any], items: list[dict[str, Any]], manifest: dict[str, Any]) -> str:
    clips = "\n".join(_clip_section(state, item, index, len(items)) for index, item in enumerate(items))
    panels = "\n".join(_info_panel(item, index) for index, item in enumerate(items[:8]))
    width = int(manifest["width"])
    height = int(manifest["height"])
    duration = float(manifest.get("duration") or 0)
    title = escape(str(timeline.get("title") or "AI Fancut Visual Package"))
    style = escape(str(timeline.get("style") or timeline.get("color_grade") or "visual overlay"))
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{title}</title>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/gsap.min.js"></script>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r160/three.min.js"></script>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/lottie-web/5.12.2/lottie.min.js"></script>
  <style>
    :root {{
      --w: {width};
      --h: {height};
      --accent: #ff6f61;
      --ice: #dff9ff;
      --ink: #080b0e;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      min-height: 100vh;
      display: grid;
      place-items: center;
      background: #0a0d10;
      color: white;
      font-family: Inter, "Microsoft YaHei", system-ui, sans-serif;
    }}
    .stage {{
      position: relative;
      width: min(96vw, calc(96vh * {width} / {height}));
      aspect-ratio: {width} / {height};
      overflow: hidden;
      background: #030406;
      border-radius: 8px;
      isolation: isolate;
    }}
    .clip {{
      position: absolute;
      inset: 0;
      opacity: 0;
      animation: clipShow var(--dur) linear forwards;
      animation-delay: var(--at);
    }}
    .clip video {{
      width: 100%;
      height: 100%;
      object-fit: cover;
      filter: contrast(1.08) saturate(1.04) brightness(1.02);
      transform: scale(1.08);
      animation: cameraMove var(--dur) ease-in-out forwards;
    }}
    .clip.setup video {{ filter: contrast(0.98) saturate(0.82) brightness(0.92); }}
    .clip.reveal video {{ filter: contrast(1.16) saturate(1.12) brightness(1.05); }}
    .clip.bridge video {{ animation-name: bridgeCamera; filter: contrast(1.22) saturate(1.18) brightness(1.08); }}
    @keyframes clipShow {{
      0%, 2% {{ opacity: 0; }}
      7%, 92% {{ opacity: 1; }}
      100% {{ opacity: 0; }}
    }}
    @keyframes cameraMove {{
      from {{ transform: scale(1.03) translate3d(-1%, 0, 0); }}
      to {{ transform: scale(1.13) translate3d(1%, -1%, 0); }}
    }}
    @keyframes bridgeCamera {{
      0% {{ transform: scale(1.0) rotate(0deg); filter: blur(0); }}
      45% {{ transform: scale(1.34) rotate(4deg); filter: blur(2px); }}
      100% {{ transform: scale(1.08) rotate(0deg); filter: blur(0); }}
    }}
    .lightLayer, .lightLayer::before, .lightLayer::after {{
      position: absolute;
      inset: -20%;
      content: "";
      pointer-events: none;
      mix-blend-mode: screen;
      z-index: 20;
    }}
    .lightLayer {{
      background:
        radial-gradient(circle at 18% 20%, rgba(255,255,255,.34), transparent 18%),
        linear-gradient(115deg, transparent 0 32%, rgba(255,255,255,.22) 44%, transparent 56% 100%);
      animation: lightSweep 4.6s ease-in-out infinite;
      opacity: .72;
    }}
    .lightLayer::before {{
      background: linear-gradient(75deg, transparent 0 42%, rgba(255,111,97,.36), transparent 58% 100%);
      animation: warmSwipe 2.8s ease-in-out infinite;
    }}
    .lightLayer::after {{
      background: radial-gradient(circle at 72% 78%, rgba(130,225,255,.32), transparent 22%);
      animation: pulseGlow 2.2s ease-in-out infinite alternate;
    }}
    @keyframes lightSweep {{ 0%,100% {{ transform: translateX(-8%); }} 50% {{ transform: translateX(9%); }} }}
    @keyframes warmSwipe {{ 0% {{ transform: translateX(-45%) rotate(4deg); opacity: .08; }} 52% {{ opacity: .72; }} 100% {{ transform: translateX(45%) rotate(4deg); opacity: .05; }} }}
    @keyframes pulseGlow {{ from {{ opacity: .2; transform: scale(.96); }} to {{ opacity: .8; transform: scale(1.06); }} }}
    .splitFrame {{
      position: absolute;
      inset: 0;
      z-index: 15;
      pointer-events: none;
      background: linear-gradient(90deg, rgba(0,0,0,.26) 0 48.8%, rgba(255,255,255,.86) 49.4% 50.2%, rgba(255,255,255,.05) 50.8% 100%);
      clip-path: polygon(0 0, 100% 0, 100% 100%, 0 100%);
      animation: splitPulse 3.2s ease-in-out infinite;
      mix-blend-mode: overlay;
    }}
    @keyframes splitPulse {{ 0%,100% {{ opacity: .22; }} 50% {{ opacity: .58; }} }}
    .wipe {{
      position: absolute;
      inset: 0;
      z-index: 18;
      pointer-events: none;
      background: linear-gradient(100deg, transparent 0 44%, rgba(255,255,255,.86) 50%, transparent 56% 100%);
      transform: translateX(-120%);
      animation: compareWipe 5.8s cubic-bezier(.2,.8,.2,1) infinite;
      mix-blend-mode: screen;
    }}
    @keyframes compareWipe {{ 0%,18% {{ transform: translateX(-120%); }} 44%,54% {{ transform: translateX(0); }} 82%,100% {{ transform: translateX(120%); }} }}
    .introCard, .outroCard {{
      position: absolute;
      inset: 0;
      z-index: 40;
      display: grid;
      place-items: center;
      background: radial-gradient(circle at 50% 45%, rgba(255,255,255,.13), rgba(0,0,0,.86));
      letter-spacing: 0;
      pointer-events: none;
    }}
    .introCard {{ animation: introExit 2s ease forwards; }}
    .outroCard {{ opacity: 0; animation: outroEnter 1.4s ease forwards; animation-delay: {max(0, duration - 1.4):.2f}s; }}
    .introCard b, .outroCard b {{
      max-width: 82%;
      text-align: center;
      font-size: clamp(24px, 7vw, 74px);
      line-height: 1;
      text-transform: uppercase;
    }}
    .introCard small, .outroCard small {{ margin-top: 12px; display: block; font-size: clamp(12px, 2vw, 18px); color: rgba(255,255,255,.68); }}
    @keyframes introExit {{ 0%,68% {{ opacity: 1; transform: scale(1); }} 100% {{ opacity: 0; transform: scale(1.08); }} }}
    @keyframes outroEnter {{ from {{ opacity: 0; transform: scale(1.08); }} to {{ opacity: 1; transform: scale(1); }} }}
    .infoPanel {{
      position: absolute;
      right: 3.5%;
      bottom: 4%;
      z-index: 35;
      min-width: min(280px, 48%);
      border: 1px solid rgba(255,255,255,.2);
      border-radius: 8px;
      padding: 12px;
      background: rgba(6,10,14,.54);
      backdrop-filter: blur(16px);
      opacity: 0;
      animation: panelShow 1.1s ease forwards;
      animation-delay: var(--panel-at);
    }}
    .infoPanel b {{ display: block; font-size: 13px; }}
    .infoPanel span {{ display: block; margin-top: 5px; color: rgba(255,255,255,.68); font-size: 12px; }}
    @keyframes panelShow {{ 0% {{ opacity: 0; transform: translateY(18px); }} 20%,80% {{ opacity: 1; transform: translateY(0); }} 100% {{ opacity: 0; transform: translateY(-8px); }} }}
    #threeMount, #lottieMount {{
      position: absolute;
      inset: 0;
      z-index: 22;
      pointer-events: none;
      mix-blend-mode: screen;
    }}
  </style>
</head>
<body>
  <main class="stage" data-hyperframes-composition data-duration="{duration:.2f}">
    {clips}
    <div class="splitFrame"></div>
    <div class="wipe"></div>
    <div class="lightLayer"></div>
    <div id="threeMount"></div>
    <div id="lottieMount"></div>
    {panels}
    <div class="introCard"><b>{title}<small>{style}</small></b></div>
    <div class="outroCard"><b>MEMORY LOCK<small>{duration:.1f}s / {manifest.get("aspect_ratio")}</small></b></div>
  </main>
  <script>
    document.querySelectorAll("video[data-media-start]").forEach((video) => {{
      video.addEventListener("loadedmetadata", () => {{
        const start = Number(video.dataset.mediaStart || 0);
        if (Number.isFinite(start)) video.currentTime = start;
      }}, {{ once: true }});
      video.play().catch(() => undefined);
    }});
    if (window.gsap) {{
      gsap.to(".infoPanel", {{ x: -8, repeat: -1, yoyo: true, duration: 1.8, ease: "sine.inOut", stagger: .18 }});
    }}
    if (window.THREE) {{
      const mount = document.getElementById("threeMount");
      const scene = new THREE.Scene();
      const camera = new THREE.PerspectiveCamera(60, 1, 0.1, 100);
      const renderer = new THREE.WebGLRenderer({{ alpha: true, antialias: true }});
      renderer.setSize(mount.clientWidth || 720, mount.clientHeight || 1280);
      mount.appendChild(renderer.domElement);
      const geo = new THREE.TorusGeometry(1.6, .006, 8, 120);
      const mat = new THREE.MeshBasicMaterial({{ color: 0xdff9ff, transparent: true, opacity: .34 }});
      const ring = new THREE.Mesh(geo, mat);
      scene.add(ring);
      camera.position.z = 4;
      function tick() {{
        ring.rotation.x += .004;
        ring.rotation.y += .007;
        renderer.render(scene, camera);
        requestAnimationFrame(tick);
      }}
      tick();
    }}
  </script>
</body>
</html>
"""


def _clip_section(state: ProjectState, item: dict[str, Any], index: int, total: int) -> str:
    start = float(item.get("output_start") or 0)
    end = float(item.get("output_end") or start + 1)
    duration = max(0.1, end - start)
    role = str(item.get("role") or "")
    role_class = "bridge" if "bridge" in role or "transform" in role else "reveal" if "reveal" in role or index > total * 0.46 else "setup"
    source = escape(str(item.get("source") or ""))
    media_start = max(0.0, float(item.get("start") or 0))
    return f"""    <section class="clip {role_class}" style="--at:{start:.3f}s;--dur:{duration:.3f}s">
      <video src="/api/hyperframes/asset/{state.project_id}/{source}" muted playsinline preload="metadata" data-media-start="{media_start:.3f}"></video>
    </section>"""


def _info_panel(item: dict[str, Any], index: int) -> str:
    at = float(item.get("output_start") or 0) + 0.16
    role = escape(str(item.get("role") or "clip"))
    effect = escape(str(item.get("effect") or "visual"))
    transition = escape(str(item.get("transition") or "hard_cut"))
    return f"""    <aside class="infoPanel" style="--panel-at:{at:.3f}s">
      <b>{role}</b><span>{effect} / {transition}</span>
    </aside>"""


def visual_export_path(project_id: str) -> Path:
    return project_dir(project_id) / "hyperframes" / "index.html"


def visual_manifest_path(project_id: str) -> Path:
    return project_dir(project_id) / "hyperframes" / "manifest.json"


def visual_asset_path(project_id: str, filename: str) -> Path:
    return project_asset_dir("raw_videos", project_id) / Path(filename).name
