# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com>
SOUNDS_LIB = r"""
function _tone(ctx,t0,freq,dur,peak,type){
  type=type||'sine';
  var o=ctx.createOscillator(), g=ctx.createGain();
  o.type=type; o.frequency.value=freq; o.connect(g); g.connect(ctx.destination);
  g.gain.setValueAtTime(Math.max(peak,0.0001),t0);
  g.gain.exponentialRampToValueAtTime(0.0001,t0+dur);
  o.start(t0); o.stop(t0+dur+0.02);
}
function _toneA(ctx,t0,freq,dur,peak,atk,type){
  type=type||'sine';
  var o=ctx.createOscillator(), g=ctx.createGain();
  o.type=type; o.frequency.value=freq; o.connect(g); g.connect(ctx.destination);
  g.gain.setValueAtTime(0.0001,t0);
  g.gain.exponentialRampToValueAtTime(peak,t0+atk);
  g.gain.exponentialRampToValueAtTime(0.0001,t0+dur);
  o.start(t0); o.stop(t0+dur+0.02);
}
function _bell(ctx,t0,base,dur,peak){
  var P=[[1,1.0],[2.0,0.5],[2.76,0.25],[5.4,0.12]];
  for(var i=0;i<P.length;i++){ _toneA(ctx,t0,base*P[i][0],dur*(1-i*0.12),peak*P[i][1],0.006,'sine'); }
}
function _fm(ctx,t0,carrier,ratio,index,dur,peak){
  var c=ctx.createOscillator(), m=ctx.createOscillator(), mg=ctx.createGain(), g=ctx.createGain();
  m.frequency.value=carrier*ratio;
  mg.gain.setValueAtTime(carrier*ratio*index,t0);
  mg.gain.exponentialRampToValueAtTime(carrier*ratio*0.01,t0+dur*0.6);
  m.connect(mg); mg.connect(c.frequency);
  c.frequency.value=carrier; c.connect(g); g.connect(ctx.destination);
  g.gain.setValueAtTime(0.0001,t0);
  g.gain.exponentialRampToValueAtTime(peak,t0+0.005);
  g.gain.exponentialRampToValueAtTime(0.0001,t0+dur);
  c.start(t0); m.start(t0); c.stop(t0+dur+0.02); m.stop(t0+dur+0.02);
}
function _slide(ctx,t0,f1,f2,dur,peak){
  var o=ctx.createOscillator(), g=ctx.createGain();
  o.type='sine';
  o.frequency.setValueAtTime(f1,t0);
  o.frequency.exponentialRampToValueAtTime(f2,t0+dur*0.8);
  o.connect(g); g.connect(ctx.destination);
  g.gain.setValueAtTime(peak,t0);
  g.gain.exponentialRampToValueAtTime(0.0001,t0+dur);
  o.start(t0); o.stop(t0+dur+0.02);
}
var NOTE={C5:523.25,D5:587.33,E5:659.25,F5:698.46,G5:783.99,A5:880,B5:987.77,C6:1046.5,D6:1174.66,E6:1318.51};
var SOUNDS={
 ping:{label:'Ping \u2605',desc:'Single clean sine \u2014 the one you liked. Default.',dur:0.40,play:function(c,t){_tone(c,t,880,0.35,0.25);}},
 soft:{label:'Soft ping',desc:'Lower, mellower single tone.',dur:0.55,play:function(c,t){_tone(c,t,660,0.5,0.2);}},
 chime:{label:'Chime',desc:'Bright bell with a short tail.',dur:0.95,play:function(c,t){_bell(c,t,660,0.9,0.22);}},
 bell:{label:'Bell (low)',desc:'Deeper, resonant bell.',dur:1.25,play:function(c,t){_bell(c,t,440,1.2,0.22);}},
 marimba:{label:'Marimba',desc:'Warm wooden mallet.',dur:0.55,play:function(c,t){_fm(c,t,523,3,2,0.5,0.3);}},
 xylophone:{label:'Xylophone',desc:'Bright, glassy mallet.',dur:0.40,play:function(c,t){_fm(c,t,1046,3,3,0.35,0.24);}},
 glass:{label:'Glass',desc:'Crystalline shimmer.',dur:0.75,play:function(c,t){_toneA(c,t,1200,0.7,0.18,0.006);_toneA(c,t,2412,0.5,0.07,0.006);_toneA(c,t,3600,0.35,0.03,0.006);}},
 doorbell:{label:'Doorbell',desc:'Two-note ding-dong.',dur:1.30,play:function(c,t){_bell(c,t,NOTE.E5,0.6,0.2);_bell(c,t+0.34,NOTE.C5,0.95,0.2);}},
 arpup:{label:'Arpeggio up',desc:'Rising major triad \u2014 \u201cdone\u201d.',dur:0.60,play:function(c,t){_tone(c,t,NOTE.C5,0.28,0.2);_tone(c,t+0.10,NOTE.E5,0.28,0.2);_tone(c,t+0.20,NOTE.G5,0.34,0.2);}},
 success:{label:'Success',desc:'Four-note completion jingle.',dur:0.90,play:function(c,t){_tone(c,t,NOTE.C5,0.22,0.2);_tone(c,t+0.09,NOTE.E5,0.22,0.2);_tone(c,t+0.18,NOTE.G5,0.22,0.2);_tone(c,t+0.30,NOTE.C6,0.5,0.22);}},
 twotone:{label:'Two-tone',desc:'Gentle rising interval.',dur:0.50,play:function(c,t){_tone(c,t,NOTE.C5,0.26,0.2);_tone(c,t+0.14,NOTE.G5,0.3,0.2);}},
 swell:{label:'Swell (soft)',desc:'Slow, pad-like \u2014 least jarring.',dur:1.10,play:function(c,t){_toneA(c,t,NOTE.G5,1.0,0.14,0.15);_toneA(c,t,NOTE.C6,1.0,0.10,0.18);}},
 pop:{label:'Pop',desc:'Tiny blip \u2014 most subtle.',dur:0.18,play:function(c,t){_slide(c,t,700,180,0.12,0.32);}},
 knock:{label:'Knock',desc:'Low double thump \u2014 non-tonal.',dur:0.40,play:function(c,t){_slide(c,t,180,90,0.10,0.5);_slide(c,t+0.16,180,90,0.10,0.5);}}
};
"""

ALERT_TMPL = r"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Alert</title>
<style>
  :root { color-scheme: light dark; }
  html,body { height:100%; margin:0; }
  body { font:16px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
         display:flex; align-items:center; justify-content:center; }
  .card { max-width:640px; width:100%; margin:1.5rem; text-align:center; }
  .banner { border-radius:18px; padding:2.2rem 1.6rem; background:#f59e0b;
            color:#1a1205; box-shadow:0 10px 40px #0003; transition:background .25s; }
  .banner.flash { background:#ef4444; color:#fff; }
  .bell { font-size:3rem; line-height:1; }
  h1 { font-size:1.6rem; margin:.6rem 0 .2rem; }
  .detail { font-size:1.05rem; opacity:.85; margin:.2rem 0 0; }
  .ts { font-size:.8rem; opacity:.6; margin-top:.5rem; }
  .row { margin-top:1.1rem; display:flex; gap:.6rem; justify-content:center; flex-wrap:wrap; }
  button { font-size:1rem; padding:.6rem 1.1rem; border-radius:10px; border:1px solid #0002;
           cursor:pointer; background:#1118; color:#fff; }
  button.primary { background:#2563eb; border-color:#2563eb; }
  button:hover { filter:brightness(1.08); }
  .diag { margin-top:1rem; font:12.5px ui-monospace,Menlo,monospace; opacity:.7;
          white-space:pre-wrap; text-align:left; background:#8881; padding:.7rem .9rem;
          border-radius:10px; }
  .hint { font-size:.85rem; opacity:.7; margin-top:.6rem; }
</style></head>
<body>
  <div class="card">
    <div class="banner" id="banner">
      <div class="bell" id="bell">&#128276;</div>
      <h1 id="msg"></h1>
      <p class="detail" id="detail"></p>
      <p class="ts" id="ts"></p>
    </div>
    <div class="row">
      <button class="primary" onclick="playNow()">&#128266; Play alert</button>
      <button onclick="dismiss()">Dismiss</button>
      <button onclick="requestNotify()">Enable OS notification</button>
    </div>
    <p class="hint" id="hint">If you didn't hear it, click "Play alert" (your browser may block sound until you interact).</p>
    <div class="diag" id="diag">running self-check&#8230;</div>
    <audio id="custom" preload="auto"></audio>
  </div>
<script>
var CFG = __CFG__;
__SOUNDS__
var origTitle = "Task alert";
var ctx = null, flashTimer = null, alive = true, played = false;
function AC(){ return window.AudioContext || window.webkitAudioContext; }
function chosen(){ return SOUNDS[CFG.sound] || SOUNDS.ping; }
function playOnce(){
  if(CFG.audio_src){
    var el = document.getElementById("custom");
    if(el && !el.src){ el.src = CFG.audio_src; }
    var n = 0;
    function once(){
      if(n >= CFG.repeat) return;
      n++;
      var a = el.cloneNode(true); a.currentTime = 0;
      var p = a.play();
      if(p && p.then){ p.then(function(){ setTimeout(once, (a.duration||0.6)*1000 + 120); })
                        .catch(function(e){ setDiag(false, e.name); }); }
    }
    once(); played = true; return true;
  }
  if(!ctx) return false;
  var s = chosen(), t0 = ctx.currentTime + 0.03, gap = (s.dur || 0.5) + 0.12;
  for(var i=0;i<CFG.repeat;i++){ s.play(ctx, t0 + i*gap); }
  played = true; return true;
}
function ensureCtx(){
  if(ctx) return Promise.resolve(ctx);
  var C = AC(); if(!C) return Promise.reject(new Error("no AudioContext"));
  ctx = new C();
  return (ctx.state === "suspended") ? ctx.resume().then(function(){return ctx;}) : Promise.resolve(ctx);
}
function playNow(){
  ensureCtx().then(function(){
    playOnce(); setDiag(true);
    document.getElementById("hint").textContent = "Played: " + (chosen().label || CFG.sound);
  }).catch(function(e){ setDiag(false, e.message); });
}
function startFlash(){
  var on = false;
  flashTimer = setInterval(function(){
    if(!alive){ clearInterval(flashTimer); document.title = origTitle; return; }
    on = !on;
    document.getElementById("banner").classList.toggle("flash", on);
    document.title = on ? ("\ud83d\udd14 " + CFG.message) : origTitle;
  }, 650);
}
function dismiss(){
  alive = false;
  if(flashTimer) clearInterval(flashTimer);
  document.getElementById("banner").classList.remove("flash");
  document.title = origTitle;
  document.getElementById("hint").textContent = "Dismissed.";
}
function requestNotify(){
  if(!("Notification" in window)){ alert("Notification API not available in this frame."); return; }
  Notification.requestPermission().then(function(perm){
    if(perm === "granted"){
      try { new Notification(CFG.message, { body: CFG.detail || "Your Claude Science task finished." }); } catch(e){}
    }
    setDiag(played);
  });
}
function setDiag(autoplayOk, blockName){
  var hasAC = !!AC();
  var inFrame = (window.self !== window.top);
  var notif = ("Notification" in window) ? Notification.permission : "unavailable";
  var lines = [
    "self-check:",
    "  sound         : " + (CFG.audio_src ? ("custom file x" + CFG.repeat) : (CFG.sound + " x" + CFG.repeat)),
    "  Web Audio API : " + (hasAC ? "available" : "MISSING"),
    "  autoplay      : " + (autoplayOk === true ? "ALLOWED (hands-free)"
                       : autoplayOk === false ? ("BLOCKED" + (blockName ? " ("+blockName+")" : "") + " -- plays on your first click/focus")
                       : "pending (interact once)"),
    "  in iframe     : " + inFrame,
    "  notifications : " + notif
  ];
  document.getElementById("diag").textContent = lines.join("\n");
}
window.addEventListener("load", function(){
  document.getElementById("msg").textContent = CFG.message;
  document.getElementById("detail").textContent = CFG.detail || "";
  document.getElementById("ts").textContent = "fired " + new Date().toLocaleString();
  origTitle = document.title = CFG.message;
  startFlash();
  var C = AC();
  if(C){ ctx = new C(); if(ctx.state === "running"){ playOnce(); setDiag(true); } else { setDiag(false); } }
  else { setDiag(false, "no AudioContext"); }
  var armed = false;
  function arm(){ if(armed || played) return; armed = true;
    ensureCtx().then(function(){ if(!played && alive) playOnce(); setDiag(true); }); }
  ["pointerdown","keydown","touchstart"].forEach(function(ev){
    window.addEventListener(ev, arm, { once:true, passive:true });
  });
  document.addEventListener("visibilitychange", function(){
    if(document.visibilityState === "visible") arm();
  });
});
</script>
</body></html>"""

import json, base64, os, mimetypes

def emit_alert(message="Task complete", detail="", sound="soft", repeat=1,
               sound_file=None, out_path="alert.html"):
    """Write a self-contained, cross-platform audible+visual alert page and
    return its path. Browser-only, so it is OS-independent (macOS/Linux/Windows
    identical); the only variance is the browser autoplay policy, which the
    page detects and degrades around automatically.

    sound      : built-in synthesized sound (no files/network). One of:
                 ping soft(default) chime bell marimba xylophone glass doorbell
                 arpup success twotone swell pop knock.
                 Audition all of them in sound_picker.html.
    sound_file : OPTIONAL path to a downloaded audio file (.mp3/.wav/.ogg) to
                 use INSTEAD of a synthesized sound. It is base64-embedded into
                 the page as a data URI, so the result stays fully self-contained
                 (no network at open time). Use this for a sound picked from the
                 online index in ONLINE_ALERT_SOUNDS.md. Overrides `sound`.
    repeat     : how many times to play it (default 1). The original annoyance
                 was a 12-beep default, not the tone itself.

    Four layers, all active: visual banner + flashing title / first-interaction
    + return-to-tab play / autoplay-on-load / manual Play button.

        emit_alert("Run finished", "442 candidates scored")           # soft ping
        emit_alert("Done", sound="chime", repeat=2)                   # built-in
        emit_alert("Done", sound_file="notify.mp3")                   # your file
    """
    valid = ["ping","soft","chime","bell","marimba","xylophone","glass",
             "doorbell","arpup","success","twotone","swell","pop","knock"]
    if sound not in valid:
        raise ValueError("unknown sound %r; choose one of %s" % (sound, valid))
    try:
        repeat = max(1, int(repeat))
    except (TypeError, ValueError):
        repeat = 1
    audio_src = ""
    if sound_file:
        if not os.path.exists(sound_file):
            raise FileNotFoundError("sound_file not found: %s" % sound_file)
        mime = mimetypes.guess_type(sound_file)[0] or "audio/mpeg"
        with open(sound_file, "rb") as fh:
            audio_src = "data:%s;base64,%s" % (mime, base64.b64encode(fh.read()).decode())
    cfg = {"message": message, "detail": detail, "sound": sound,
           "repeat": repeat, "audio_src": audio_src}
    html = ALERT_TMPL.replace("__SOUNDS__", SOUNDS_LIB).replace("__CFG__", json.dumps(cfg))
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    return out_path
