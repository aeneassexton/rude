.ci-screen {
  height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  position: relative;
}

/* Nav */
.ci-nav {
  display: flex;
  justify-content: space-between;
  padding: 16px 24px 0;
  flex-shrink: 0;
  position: relative;
  z-index: 10;
}

.nav-pill {
  padding: 10px 22px;
  border-radius: 999px;
  border: 1px solid;
  background: rgba(255,255,255,0.04);
  font-family: 'DM Sans', sans-serif;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.2s;
  -webkit-app-region: no-drag;
}
.nav-pill:hover { background: rgba(255,255,255,0.09); }
.nav-pill.blue   { color: #4a9eff; border-color: rgba(74,158,255,0.35); }
.nav-pill.orange { color: #e8714a; border-color: rgba(232,113,74,0.35); }

/* Heading */
.ci-heading {
  padding: 40px 28px 0;
  position: relative;
  z-index: 10;
}

.ci-title {
  font-size: clamp(2.2rem, 7vw, 3rem);
  font-weight: 300;
  line-height: 1.1;
  letter-spacing: -0.02em;
  color: var(--text-primary);
}

.ci-sub {
  margin-top: 10px;
  font-size: 13px;
  color: var(--text-muted);
  letter-spacing: 0.03em;
}

/* Wheel */
.wheel-anchor {
  position: absolute;
  bottom: 15%;
  right: -22%;
  width: 75vw;
  max-width: 400px;
  aspect-ratio: 1;
  z-index: 5;
}

.wheel-ring {
  width: 100%;
  height: 100%;
  border-radius: 50%;
  border: 1px solid rgba(255,255,255,0.07);
  background: radial-gradient(circle at 50% 50%, rgba(255,255,255,0.015) 0%, transparent 65%);
  position: relative;
  cursor: grab;
  touch-action: none;
  -webkit-app-region: no-drag;
  will-change: transform;
}
.wheel-ring:active { cursor: grabbing; }

/* Mood nodes */
.mn {
  position: absolute;
  width: 80px;
  height: 80px;
  border-radius: 50%;
  background: var(--bg-card);
  box-shadow: 0 0 0 1px rgba(255,255,255,0.06), inset 0 0 22px var(--mg);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: box-shadow 0.2s ease, background 0.2s ease;
  -webkit-app-region: no-drag;
}

.mn-on {
  box-shadow: 0 0 0 1.5px var(--mc), 0 0 32px var(--mg), inset 0 0 24px var(--mg);
  background: color-mix(in srgb, var(--mc) 15%, #141b24);
}

.mn-word {
  font-family: 'Cormorant Garamond', serif;
  font-size: 13px;
  font-weight: 400;
  letter-spacing: 0.02em;
  white-space: nowrap;
}

/* Hub */
.wheel-hub {
  position: absolute;
  top: 50%; left: 50%;
  transform: translate(-50%, -50%);
  width: 56px; height: 56px;
  border-radius: 50%;
  border: 1px solid rgba(255,255,255,0.06);
  background: #0d1117;
  pointer-events: none;
}

.ci-loading {
  position: absolute;
  bottom: 28%;
  left: 28px;
  color: var(--text-muted);
  font-size: 13px;
  z-index: 20;
}

.ci-err {
  position: absolute;
  bottom: 20px; left: 50%;
  transform: translateX(-50%);
  color: #f87171;
  font-size: 12px;
  z-index: 20;
}

/* Done state — full screen tap target */
.ci-done {
  height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 14px;
  cursor: pointer;
  -webkit-app-region: no-drag;
}

.done-orb {
  width: 180px; height: 180px;
  border-radius: 50%;
  margin-bottom: 16px;
  animation: orb-in 0.55s cubic-bezier(0.34,1.56,0.64,1) both;
}
@keyframes orb-in {
  from { transform: scale(0.3); opacity: 0; }
  to   { transform: scale(1);   opacity: 1; }
}

.done-word { font-size: 3rem; font-weight: 300; letter-spacing: -0.02em; }
.done-sub  { font-size: 13px; color: var(--text-muted); letter-spacing: 0.05em; }
.done-tap  {
  margin-top: 8px;
  font-size: 11px;
  color: #3d4f63;
  letter-spacing: 0.06em;
  animation: fade-in 1s ease 0.8s both;
}
@keyframes fade-in { from { opacity: 0; } to { opacity: 1; } }