// What if a submarine never stopped diving? — isometric infographic, 1080×1920
import { Iso, PAL, tri, mix, hex, rgb, css, clamp, lerp, seg, ss, eo, eio, back, hash, TAU, C30, S30,
  pin, cutLine, haloText, ring, iconGrid, shape, person, FONT } from './engine.js';
import { LINES, DUR as TDUR } from './timeline.js';

export const DUR = TDUR;
const L = Object.fromEntries(LINES.map(l => [l.id, l]));
const IMPACT = 1.25;                                  // the sub hits the water
const HOOK = -1;
const MIL = ['l01', 'l02', 'l03', 'l04', 'l05', 'l06', 'l07', 'l08', 'l11'];
const S = 14, R = 4.6, TH = .8;                       // milestone spacing, column half-width, wall thickness
const MS = [0, 40, 200, 1000, 2000, 3800, 6000, 8336, 10935, 12262];   // depths in metres
const MZ = MS.map((_, i) => -i * S);
const SUBY = 1.6;                                      // the sub runs at the front of the column
const ZFLOOR = MZ[8] - 1.15;                           // sea-floor top
const ZEND = MZ[9] - 2.0 * S;                          // sub's final position
const ZBOT = ZEND - 4.5, ZQ = ZEND - 9;                // column bottom, "?" plate
const T_CUT = L.l10.t0, T_PULL = L.l12.t0 + .2, T_PULL1 = DUR - .9;
const SUBC = '#E9BE5C', INK = PAL.ink;

// ---------- depth mapping ----------
export function depthAt(z) {
  const u = -z / S;
  if (u <= 0) return 0;
  const i = Math.floor(u);
  if (i >= MS.length - 1) return MS[9] + (u - 9) * (MS[9] - MS[8]);
  return lerp(MS[i], MS[i + 1], u - i);
}
// monotone cubic through keys
function mono(keys) {
  const n = keys.length, xs = keys.map(k => k[0]), ys = keys.map(k => k[1]), d = [], m = new Array(n).fill(0);
  for (let i = 0; i < n - 1; i++) d.push((ys[i + 1] - ys[i]) / (xs[i + 1] - xs[i]));
  m[0] = 0; m[n - 1] = d[n - 2];
  for (let i = 1; i < n - 1; i++) m[i] = d[i - 1] * d[i] <= 0 ? 0 : (d[i - 1] + d[i]) / 2;
  for (let i = 0; i < n - 1; i++) { if (d[i] === 0) { m[i] = m[i + 1] = 0; continue; } const a = m[i] / d[i], b = m[i + 1] / d[i], s = a * a + b * b; if (s > 9) { const k = 3 / Math.sqrt(s); m[i] = k * a * d[i]; m[i + 1] = k * b * d[i]; } }
  return t => { if (t <= xs[0]) return ys[0]; if (t >= xs[n - 1]) return ys[n - 1]; let i = 0; while (t > xs[i + 1]) i++; const h = xs[i + 1] - xs[i], u = (t - xs[i]) / h, u2 = u * u, u3 = u2 * u; return (2 * u3 - 3 * u2 + 1) * ys[i] + (u3 - 2 * u2 + u) * h * m[i] + (-2 * u3 + 3 * u2) * ys[i + 1] + (u3 - u2) * h * m[i + 1]; };
}
const ARR = ['l01', 'l02', 'l03', 'l04', 'l05', 'l06', 'l07', 'l08'].map((id, i) => [L[id].t0 + .15, MZ[i + 1]]);
const subZ0 = mono([[IMPACT, .35], [IMPACT + .45, -2.4], ...ARR, [T_CUT + .6, MZ[8]], [L.l11.t0 + .35, MZ[9]], [DUR, ZEND]]);
const subZ = t => t < IMPACT ? .35 + 21.6 * (1 - (t / IMPACT) ** 2) : subZ0(t);
const lnk = mono([[0, Math.log(50)], [IMPACT + .15, Math.log(56)], [IMPACT + 1.1, Math.log(70)], [L.l07.t1, Math.log(70)], [L.l08.t0 + .4, Math.log(84)], [T_CUT + .2, Math.log(84)], [T_CUT + 1.4, Math.log(70)], [T_PULL, Math.log(70)], [T_PULL1, Math.log(9.4)], [DUR, Math.log(9.3)]]);

// ---------- colour ----------
const WATER = [[0, '#86CBE8'], [40, '#62B1DA'], [200, '#3D84BA'], [1000, '#25487F'], [4000, '#1A2852'], [11000, '#121630']];
function waterCol(d) {
  const u = Math.log10(1 + d);
  for (let i = 0; i < WATER.length - 1; i++) { const a = Math.log10(1 + WATER[i][0]), b = Math.log10(1 + WATER[i + 1][0]); if (u <= b) return hex(mix(WATER[i][1], WATER[i + 1][1], clamp((u - a) / (b - a)))); }
  return WATER[WATER.length - 1][1];
}
const ROCK = ['#8A6A55', '#9E7E61', '#76604F', '#A88A6C', '#6C584A', '#93735A'];
function wallCol(z) {
  if (z > ZFLOOR) return waterCol(depthAt(z));
  if (z > ZFLOOR - 1.2) return '#9C8C78';           // sediment band
  const j = Math.floor(-z / 2.3), c = ROCK[(j * 7 + 3) % ROCK.length];
  return hex(mix(c, '#D0663A', ss(seg(-z, -MZ[9], -ZBOT)) * .75));     // deeper rock warms up
}
const dark = d => clamp(Math.log10(1 + d) / 3);       // 0 surface → 1 at 1000 m
const dim = (c, d, k = .6) => hex(mix(c, '#141832', dark(d) * k));

// ---------- helpers ----------
const fmt = n => Math.round(n).toLocaleString('en-US');
function card(g, x, y, w, h, r) { g.beginPath(); g.moveTo(x + r, y); g.arcTo(x + w, y, x + w, y + h, r); g.arcTo(x + w, y + h, x, y + h, r); g.arcTo(x, y + h, x, y, r); g.arcTo(x, y, x + w, y, r); g.closePath(); }
function wrap(g, s, maxW) { const w = s.split(' '), out = []; let cur = ''; for (const x of w) { const t = cur ? cur + ' ' + x : x; if (g.measureText(t).width > maxW && cur) { out.push(cur); cur = x; } else cur = t; } out.push(cur); return out; }

// ---------- the submarine ----------
function drawSub(iso, t, z, d) {
  const lit = SUBC;
  iso.keep = true;
  iso.push(0, SUBY, z, 0, 1);
  const prop = t * 9;
  iso.cyl(-3.0, 0, 0, 1.0, 6.0, tri(lit), { axis: 'x', n: 28, bias: 0, layer: 3 });
  iso.sphere(3.0, 0, 0, 1.0, tri(lit), { layer: 3, bias: .2 });
  iso.sphere(-3.0, 0, 0, .98, tri(hex(mix(lit, '#B0832A', .25))), { layer: 3, bias: -.2 });
  iso.cyl(-4.2, 0, 0, .55, .9, tri('#B0832A'), { axis: 'x', n: 6, spin: prop, layer: 3, bias: -.6 });   // propeller hub
  iso.box(-4.0, -.08, -.9, .7, .16, 1.8, tri('#C9952F'), { layer: 3, bias: -.5 });                    // rudder
  iso.box(-.9, -.45, .75, 1.9, .9, 1.15, tri(lit), { layer: 3, bias: .5 });                          // sail
  iso.box(-.2, -.06, 1.9, .14, .12, .8, tri('#B0832A'), { layer: 3, bias: .6 });                      // periscope
  iso.box(-.6, -1.6, .55, .5, 3.2, .12, tri('#C9952F'), { layer: 3, bias: .55 });                    // dive planes
  for (let i = 0; i < 3; i++) iso.bill(-1.6 + i * 1.6 + 1.2, .98, .05, gg => { gg.beginPath(); gg.arc(0, 0, .26, 0, TAU); gg.fillStyle = '#FBF4E6'; gg.fill(); gg.beginPath(); gg.arc(0, 0, .17, 0, TAU); gg.fillStyle = d > 150 ? '#FFE9A8' : '#2D6390'; gg.fill(); }, { layer: 3.1, cull: false });
  iso.pop();
  iso.keep = false;
}
function headlight(iso, g, t, z, d) {
  const a = seg(d, 120, 600); if (a <= 0) return;
  const [nx, ny] = iso.P(3.9, SUBY, z), k = iso.cam.k;
  const ang = Math.atan2(S30, C30) + .08, len = 11 * k, spr = .3;
  const gr = g.createRadialGradient(nx, ny, 0, nx, ny, len);
  gr.addColorStop(0, `rgba(255,236,170,${.55 * a})`); gr.addColorStop(.5, `rgba(255,226,140,${.2 * a})`); gr.addColorStop(1, 'rgba(255,226,140,0)');
  g.save(); g.beginPath(); g.moveTo(nx, ny); g.arc(nx, ny, len, ang - spr, ang + spr); g.closePath(); g.fillStyle = gr; g.fill(); g.restore();
}

// ---------- world pieces ----------
function walls(iso, zTop, zBot) {
  const z0 = Math.min(.8, Math.ceil(zTop)), z1 = Math.max(ZBOT, Math.floor(zBot));
  for (let z = z0 - 1; z >= z1; z--) {
    const h = Math.min(1, z0 - z), c = tri(wallCol(z + .5));
    iso.box(-R - TH, -R - TH, z, TH, 2 * R + TH, h, c, { layer: 1, cull: false });
    iso.box(-R, -R - TH, z, 2 * R, TH, h, c, { layer: 1, cull: false });
  }
}
function wallLabels(iso, t, k) {
  const a = 1 - seg(k, 30, 18); if (a <= 0) return;
  const ZONES = [[0, 'SUNLIGHT ZONE'], [200, 'TWILIGHT ZONE'], [1000, 'MIDNIGHT ZONE'], [4000, 'THE ABYSS'], [6000, 'HADAL ZONE'], [10935.1, 'SOLID ROCK']];
  for (const [d, name] of ZONES) {
    const z = zOf(d) - (d === 10935.1 ? 2.4 : 1.6);
    iso.text3(name, -R + .02, R - .6, z, { plane: 'yz', size: .95, weight: 600, track: 6, face: '#FBF4E6', a: .9 * a, layer: 1.5 });
  }
  for (let i = 1; i < MS.length; i++) {
    const z = MZ[i] - (i === 8 ? 1.15 : 0);
    iso.line3([[-R, -R + .03, z], [R, -R + .03, z]], '#FBF4E6', 2, { dash: [10, 8], a: .55 * a, layer: 1.5 });
    if (i !== 8) iso.text3(fmt(MS[i]) + ' m', -R + .35, -R + .02, z + .25, { plane: 'xz', size: .8, weight: 500, face: '#FBF4E6', a: .85 * a, layer: 1.5 });
  }
}
function zOf(d) { for (let i = 0; i < MS.length - 1; i++) if (d <= MS[i + 1]) return -(i + (d - MS[i]) / (MS[i + 1] - MS[i])) * S; return MZ[9] - (d - MS[9]) / (MS[9] - MS[8]) * S; }

function surface(iso, t) {
  const sea = tri('#7CC4E4'), E = 9;
  iso.flat([[-R - E, -R - E], [-R - TH, -R - E], [-R - TH, R + 3], [-R - E, R + 3]], .8, sea[0], { layer: 0 });
  iso.flat([[-R - TH, -R - E], [R + 3, -R - E], [R + 3, -R - TH], [-R - TH, -R - TH]], .8, sea[0], { layer: 0 });
  const sub = t > IMPACT + .02;              // once the sub is under, the water surface sits over it
  iso.flat([[-R, -R], [R, -R], [R, R], [-R, R]], .8, '#9AD4EC', { layer: sub ? 3.4 : 1.2, a: sub ? .5 : 1 });
  // ripples on the open water
  for (let i = 0; i < 6; i++) { const y = -R + .8 + i * 1.5, ph = t * 1.4 + i; const pts = []; for (let x = -R + .4; x <= R - .4; x += .4) pts.push([x, y + Math.sin(x * 1.3 + ph) * .12, .8]); iso.line3(pts, '#FBF4E6', 2, { a: .55, layer: sub ? 3.41 : 1.25 }); }
}
function title(iso, t) {}
function titleCard(g, W, t) {            // the question, set as a map title above the board
  const a = 1 - seg(t, 3.0, 3.6); if (a <= 0) return;
  const r1 = back(seg(t, .15, .7), 1.6), r2 = back(seg(t, .4, .95), 1.6);
  g.save(); g.globalAlpha = a;
  haloText(g, 'WHAT IF A SUBMARINE', W / 2, 330 - (1 - r1) * 30, { font: `700 64px ${FONT}`, align: 'center', track: 5, hw: 14 });
  g.globalAlpha = a * clamp(r2);
  haloText(g, 'NEVER STOPPED DIVING?', W / 2, 430 - (1 - r2) * 30, { font: `700 64px ${FONT}`, align: 'center', track: 5, hw: 14, color: '#B3352B' });
  g.restore();
}
// milestone props (behind the sub, toward the back wall)
function diver(iso, t) {
  const z = MZ[1] + 1.6, d = 40, bob = Math.sin(t * 2) * .15;
  iso.bill(1.2, -2.8, z + bob, gg => {
    gg.save(); gg.rotate(-.35);
    gg.fillStyle = dim('#948E83', d); gg.fillRect(-.42, -2.0, .32, 1.1);                       // tank
    person(gg, { body: dim('#2D6390', d), legs: dim('#23384F', d), skin: '#C98B62', hair: '#3A2A22', h: 2.4, arm: 1.9 });
    gg.fillStyle = dim('#E9DFCB', d); gg.fillRect(-.42, -.06, .36, .14); gg.fillRect(.02, -.06, .4, .14);  // fins
    gg.restore();
  }, { layer: 2, r: 3 });
  bubbles(iso, t, [1.0, -2.8, z + 2], 5, 77);
  return [1.2, -2.8, z + 1.4];
}
function sunIcon(iso, g, t) { return [2.6, -3.0, MZ[2] + 2.2]; }
function jelly(iso, t) {
  const z = MZ[3] + 1.8, x = 1.8, y = -3.0, p = Math.sin(t * 2.4) * .12;
  iso.bill(x, y, z, gg => {
    const gr = gg.createRadialGradient(0, -.2, 0, 0, -.2, 2.2); gr.addColorStop(0, 'rgba(160,240,255,.35)'); gr.addColorStop(1, 'rgba(160,240,255,0)');
    gg.fillStyle = gr; gg.beginPath(); gg.arc(0, -.2, 2.2, 0, TAU); gg.fill();
    gg.strokeStyle = '#9FE8F4'; gg.lineWidth = .07; gg.lineCap = 'round';
    for (let i = 0; i < 5; i++) { gg.beginPath(); gg.moveTo(-.5 + i * .25, 0); for (let s = 1; s <= 6; s++) gg.lineTo(-.5 + i * .25 + Math.sin(s * .9 + t * 3 + i) * .12, s * .32); gg.stroke(); }
    gg.beginPath(); gg.ellipse(0, -.1, .85 * (1 + p), .7 * (1 - p), 0, Math.PI, TAU); gg.fillStyle = '#7FE0F0'; gg.fill();
    gg.beginPath(); gg.ellipse(-.2, -.4, .35, .2, 0, 0, TAU); gg.fillStyle = '#D5FBFF'; gg.fill();
  }, { layer: 2, r: 3 });
  return [x, y, z - .3];
}
const WHALE = [[4, -.9], [4.1, .6], [3.5, 1.0], [1, 1.1], [-1.5, .9], [-3.2, .45], [-3.9, .25], [-4.7, 1.0], [-4.45, 0], [-4.7, -1.0], [-3.9, -.25], [-3.2, -.45], [-1, -1.0], [1.5, -1.25], [3.5, -1.15]];
function whale(iso, t) {
  const z = MZ[4] + 2.0, sw = Math.sin(t * 1.3) * .2;
  shape(iso, WHALE.map(p => [p[0], p[1] + (p[0] < -3 ? sw * (p[0] + 3) * -.5 : 0)]), [-.2, -3.4, z], { color: tri('#6F7186'), depth: 1.6, plane: 'xz', scale: .95, layer: 2 });
  iso.bill(3.0, -1.75, z + .5, gg => { gg.beginPath(); gg.arc(0, 0, .12, 0, TAU); gg.fillStyle = '#FBF4E6'; gg.fill(); }, { layer: 2.1 });
  return [1.5, -2.6, z + 1.1];
}
function wreck(iso, t) {
  const z = MZ[5] + 1.0;
  iso.box(-R, -R, z - 1.4, 2 * R, 2.6, 1.4, tri('#3E3A4C'), { layer: 2, cull: false });              // ledge
  const top = z;
  iso.box(-3.6, -3.9, top, 6.0, 1.5, 1.2, tri('#2E2A33'), { layer: 2, cull: false, faceColor: [null, '#7A2E2A', null] });   // hull
  iso.box(-2.2, -3.7, top + 1.2, 3.4, 1.1, .7, tri('#B9B2A3'), { layer: 2, cull: false });            // deck house
  for (let i = 0; i < 2; i++) { iso.cyl(-1.5 + i * 1.6, -3.15, top + 1.9, .3, 1.1, tri('#A88A5E'), { layer: 2, cull: false, n: 12 }); iso.cyl(-1.5 + i * 1.6, -3.15, top + 2.75, .31, .25, tri('#2E2A33'), { layer: 2.01, cull: false, n: 12 }); }
  iso.box(2.4, -3.9, top, .6, 1.5, 1.2, tri('#2E2A33'), { layer: 2, cull: false, faceColor: [null, '#1E1B22', '#1E1B22'] });
  return [-.5, -3.2, top + 2.8];
}
const FISH = [[1.1, -.1], [.9, -.45], [.3, -.55], [-.4, -.35], [-1.1, -.1], [-1.25, .05], [-1.1, .15], [-.4, .3], [.3, .5], [.9, .4]];
function snailfish(iso, t) {
  const z = MZ[7] + 1.6, x = 1.6 + Math.sin(t * .8) * .4;
  shape(iso, FISH, [x, -2.6, z], { color: tri('#E8C9C2'), depth: .5, plane: 'xz', scale: 1.15, layer: 2 });
  iso.bill(x + .85, -2.05, z + .12, gg => { gg.beginPath(); gg.arc(0, 0, .1, 0, TAU); gg.fillStyle = '#2E2522'; gg.fill(); }, { layer: 2.1 });
  return [x, -2.4, z + .6];
}
function bubbles(iso, t, at, n, seed) {
  for (let i = 0; i < n; i++) {
    const per = 1.6, ph = hash(seed + i) * per, age = ((t + ph) % per) / per;
    const x = at[0] + (hash(seed + i * 3.1) - .5) * .8 + Math.sin(age * 9 + i) * .15, z = at[2] + age * 3.2;
    iso.sphere(x, at[1], z, .12 + .1 * hash(seed + i * 7), tri('#DDF3FB'), { layer: 2.4, hi: false, cull: false });
  }
}
function subBubbles(iso, t, z, vz) {
  if (vz > -.5 || t < IMPACT + .05) return;                                  // only while moving down
  for (let i = 0; i < 10; i++) {
    const per = .9, ph = hash(i + 3) * per, age = ((t + ph) % per) / per;
    const x = -4.2 + (hash(i * 5.3) - .5) * .9, y = SUBY + (hash(i * 2.7) - .5) * .8;
    iso.sphere(x - age * .4, y, z + age * 3.5 + .3, .14 + .12 * hash(i), tri('#DDF3FB'), { layer: 2.9, hi: false, cull: false });
  }
}
function floorCore(iso, t) {
  const p = seg(t, T_CUT + .55, T_CUT + 1.15), s = 22 * Math.pow(p, 2);
  if (s > 21) return;
  const top = '#A8977F', side = '#7E6A58';
  iso.push(s, s, -s * .2, 0, 1);
  iso.box(-R, -R, ZFLOOR - 30, 2 * R, 2 * R, 30, tri(side), { layer: 2.2, cull: false, faceColor: [top, '#8C7662', '#6E5B4B'] });
  iso.pop();
}
function debris(iso, t, z) {
  const a = seg(t, T_CUT + .7, T_CUT + 1.1) * (1 - seg(t, L.l11.t0 + .6, L.l11.t0 + 1.4)); if (a <= 0) return;
  for (let i = 0; i < 14; i++) {
    const per = .7, ph = hash(i + 40) * per, age = ((t + ph) % per) / per;
    const ang = hash(i * 9.1) * TAU, r = 3.2 + age * 2.2;
    iso.box(Math.cos(ang) * r * .6, SUBY + Math.sin(ang) * 1.2, z - 1.2 + age * 2.4, .35, .35, .35, tri(ROCK[i % ROCK.length]), { layer: 2.8, cull: false });
  }
}
function dust(iso, t) {
  const t0 = L.l08.t0 + .2, a = seg(t, t0, t0 + .2) * (1 - seg(t, t0 + 1.4, t0 + 2.4)); if (a <= 0) return;
  const age = seg(t, t0, t0 + 2.4);
  iso.alpha = a * .7;
  for (let i = 0; i < 12; i++) { const ang = i / 12 * TAU, r = 3.2 + eo(age) * 2.2; iso.sphere(Math.cos(ang) * r * 1.1, SUBY + Math.sin(ang) * r * .45, ZFLOOR + .25 + eo(age) * .5, .18 + age * .14, tri('#BFAE96'), { layer: 3.2, hi: false, cull: false }); }
  iso.alpha = 1;
}
function qPlate(iso, g, t) {
  const a = seg(t, T_PULL + 1.6, T_PULL + 2.4); if (a <= 0) return null;
  return a;
}

// ---------- HUD ----------
function hud(g, W, t, d, pressMode, pop = 0, hot = 0) {
  const a = seg(t, IMPACT + .75, IMPACT + 1.05); if (a <= 0) return; if (a <= 0) return;
  g.save(); g.globalAlpha = a;
  const x = 64, y = 170;
  haloText(g, 'DEPTH', x, y, { font: `600 30px ${FONT}`, track: 7 });
  const fs = Math.round(112 * (1 + .2 * pop)); g.font = `400 ${fs}px ${FONT}`; const ns = fmt(d);
  haloText(g, ns, x - 4, y + 112, { font: `400 ${fs}px ${FONT}`, track: 1, hw: 10, color: hot || pop > .3 ? '#B3352B' : PAL.ink });
  const nw = g.measureText(ns).width;
  haloText(g, 'm', x + nw + 6, y + 112, { font: `500 52px ${FONT}`, hw: 8 });
  const atm = 1 + d / 10;
  const sc = 1 + .18 * pressMode;
  g.translate(x, y + 158); g.scale(sc, sc);
  haloText(g, 'PRESSURE', 0, 0, { font: `600 26px ${FONT}`, track: 6 });
  haloText(g, '≈ ' + fmt(atm) + ' × surface', 0, 40, { font: `500 32px ${FONT}`, hw: 8 });
  // Isotype: one block = 100 atmospheres
  iconGrid(g, -4, 52, 12, atm / 100, 12, 34, (gg, px, py, s, on) => {
    const t3 = on ? tri(pressMode > .05 ? '#CF5140' : '#5A7FA8') : ['#E6DCC8', '#DCD0BA', '#CFC2AA'];
    gg.save(); gg.translate(px, py); const k = s * .36;
    const P = (X, Y, Z) => [(X - Y) * C30 * k, ((X + Y) * S30 - Z) * k];
    const f = (pts, c) => { gg.beginPath(); pts.forEach((p, i) => { const q = P(...p); i ? gg.lineTo(q[0], q[1]) : gg.moveTo(q[0], q[1]); }); gg.closePath(); gg.fillStyle = c; gg.fill(); };
    f([[-.5, .5, -.5], [.5, .5, -.5], [.5, .5, .5], [-.5, .5, .5]], t3[1]); f([[.5, -.5, -.5], [.5, .5, -.5], [.5, .5, .5], [.5, -.5, .5]], t3[2]); f([[-.5, -.5, .5], [.5, -.5, .5], [.5, .5, .5], [-.5, .5, .5]], t3[0]);
    gg.restore();
  });
  haloText(g, '■ = 100 atm', 0, 128, { font: `500 22px ${FONT}`, track: 2, color: '#6E625C' });
  g.restore();
}
function subtitle(g, W, H, t) {
  for (const l of LINES) {
    const t0 = l.t0 - .05, t1 = Math.max(l.t1 + .1, l.t0 + 1.5);
    if (t < t0 || t > t1 + .12) continue;
    const out = seg(t, t1, t1 + .12), bIn = eo(seg(t, t0, t0 + .15)), tIn = ss(seg(t, t0 + .05, t0 + .25));
    g.save(); g.globalAlpha = 1 - out;
    g.font = `600 52px ${FONT}`;
    const lines = wrap(g, l.sub, 820), lh = 64, w = Math.max(...lines.map(s => g.measureText(s).width)) + 120, h = lines.length * lh + 40;
    const x = (W - w) / 2, y = (l.id === 'l12' ? 1120 : 1400) - h / 2 + (1 - back(bIn, 2)) * 26;
    card(g, x, y, w, h, 14); g.fillStyle = 'rgba(251,244,230,.96)'; g.fill();
    g.save(); g.setLineDash([2400]); g.lineDashOffset = 2400 * (1 - bIn); g.strokeStyle = INK; g.lineWidth = 3; g.stroke(); g.restore();
    // legend chip: tiny iso cube in the sub's colour
    const cx = x + 44, cy = y + h / 2, k = 15, t3 = tri(SUBC); const P = (X, Y, Z) => [cx + (X - Y) * C30 * k, cy + ((X + Y) * S30 - Z) * k];
    const f = (pts, c) => { g.beginPath(); pts.forEach((p, i) => { const q = P(...p); i ? g.lineTo(q[0], q[1]) : g.moveTo(q[0], q[1]); }); g.closePath(); g.fillStyle = c; g.fill(); };
    f([[-.5, .5, -.5], [.5, .5, -.5], [.5, .5, .5], [-.5, .5, .5]], t3[1]); f([[.5, -.5, -.5], [.5, .5, -.5], [.5, .5, .5], [.5, -.5, .5]], t3[2]); f([[-.5, -.5, .5], [.5, -.5, .5], [.5, .5, .5], [-.5, .5, .5]], t3[0]);
    g.save(); g.beginPath(); g.rect(x + 76, y, (w - 76) * tIn + 4, h); g.clip();
    g.fillStyle = INK; g.textBaseline = 'middle';
    lines.forEach((s, i) => g.fillText(s, x + 84, y + 20 + lh / 2 + i * lh + 2));
    g.restore(); g.restore();
  }
}
function scaleLegend(g, iso, t) {           // end frame: every milestone labelled along the column
  const a = seg(t, T_PULL1 - .9, T_PULL1); if (a <= 0) return;
  const NAMES = ['SURFACE', 'SCUBA LIMIT', 'SUNLIGHT ENDS', 'MIDNIGHT ZONE', 'SPERM WHALES', 'TITANIC WRECK', 'HADAL ZONE', 'DEEPEST FISH', 'OCEAN FLOOR', 'DEEPEST HOLE'];
  g.save();
  for (let i = 0; i < MS.length; i++) {
    const b = seg(a, i * .06, i * .06 + .4); if (b <= 0) continue;
    const z = MZ[i] - (i === 8 ? 1.15 : 0), [sx, sy] = iso.P(R, -R, z), x2 = sx + 46;
    g.globalAlpha = b; g.strokeStyle = INK; g.lineWidth = 2; g.beginPath(); g.moveTo(sx + 4, sy); g.lineTo(sx + 4 + 40 * eo(b), sy); g.stroke();
    g.beginPath(); g.arc(sx + 4, sy, 4, 0, TAU); g.fillStyle = INK; g.fill();
    haloText(g, (i ? fmt(MS[i]) + ' m' : '0 m'), x2, sy + 9, { font: `500 28px ${FONT}` });
    haloText(g, NAMES[i], x2 + 128, sy + 9, { font: `600 22px ${FONT}`, track: 3, color: '#5E524C' });
  }
  g.restore();
}

// ---------- events for the mixer ----------
export function events() {
  const ev = [{ t: 0, type: 'fall', d: IMPACT }, { t: IMPACT, type: 'bigsplash' }, ...HOOKW.map(w => ({ t: w[2] + FALL, type: 'slam' }))];
  for (const id of ['l01', 'l02', 'l03', 'l04', 'l05', 'l06', 'l07', 'l11']) ev.push({ t: L[id].t0 + .05, type: 'hit' });
  ev.push({ t: L.l08.t0 + .15, type: 'thud' }, { t: L.l09.t0 + .2, type: 'creak' });
  ev.push({ t: T_CUT + .05, type: 'cut' }, { t: T_CUT + .55, type: 'crack' }, { t: T_CUT + .6, type: 'drill', d: L.l11.t0 + .9 - (T_CUT + .6) });
  ev.push({ t: T_PULL, type: 'whoosh' }, { t: T_PULL1 - .2, type: 'end' });
  return ev;
}
// hook text: each word drops in from above, lands with a squash, then all fall into the water on impact
const HOOKW = [['WHAT', 0, .0], ['IF A', 0, .12], ['SUBMARINE', 0, .24], ['KEEPS', 1, .46], ['DIVING?', 1, .62]];
const FALL = .2;
function hookText(g, W, t) {
  if (t > IMPACT + 1.1) return;
  const te = t - IMPACT, jolt = te > 0 && te < .25 ? Math.sin(te * 90) * 12 * (1 - te / .25) : 0;
  const F = [`800 70px ${FONT}`, `800 108px ${FONT}`], Y = [250, 370];
  g.save(); g.translate(W / 2 + jolt, jolt * .4);
  for (const ln of [0, 1]) {
    const words = HOOKW.map((w, i) => [...w, i]).filter(w => w[1] === ln); g.font = F[ln]; g.letterSpacing = '3px';
    const sp = ln ? 30 : 24, ws = words.map(w => g.measureText(w[0]).width), tot = ws.reduce((a, b) => a + b, 0) + sp * (ws.length - 1);
    let x = -tot / 2;
    words.forEach((w, i) => {
      const t0 = w[2], p = seg(t, t0, t0 + FALL), cx = x + ws[i] / 2; x += ws[i] + sp;
      if (p <= 0) return;
      // drop in: gravity ease, land, squash and settle
      let y = Y[ln] - 520 * (1 - p * p), sx = 1, sy = 1;
      if (p < 1) { sy = 1.18; sx = .9; }
      const lt = t - t0 - FALL;
      if (lt > 0) { const q = Math.exp(-lt / .09) * Math.cos(lt * 38); sy = 1 - .26 * q; sx = 1 + .2 * q; y = Y[ln]; }
      // fall out after the impact, staggered, into the water
      const ot = te - .22 - w[3] * .06;
      let al = 1, rot = 0;
      if (ot > 0) { y += 1700 * ot * ot + 120 * ot; rot = (hash(w[3] * 4.1) - .5) * ot * 2.2; al = 1 - seg(ot, .35, .6); }
      if (al <= 0) return;
      g.save(); g.translate(cx, y);
      // motion trail while falling in
      if (p < 1) for (let k = 1; k <= 3; k++) { g.save(); g.globalAlpha = .18 / k; g.translate(0, -k * 34); g.font = F[ln]; g.letterSpacing = '3px'; g.textAlign = 'center'; g.textBaseline = 'alphabetic'; g.fillStyle = ln ? '#D9402F' : '#2E2522'; g.fillText(w[0], 0, 0); g.restore(); }
      g.rotate(rot); g.scale(sx, sy); g.globalAlpha = al;
      g.font = F[ln]; g.letterSpacing = '3px'; g.textAlign = 'center'; g.textBaseline = 'alphabetic'; g.lineJoin = 'round';
      g.lineWidth = ln ? 26 : 20; g.strokeStyle = '#2E2522'; g.strokeText(w[0], 6, 8);
      g.lineWidth = ln ? 18 : 14; g.strokeStyle = '#FBF4E6'; g.strokeText(w[0], 0, 0);
      g.fillStyle = ln ? '#D9402F' : '#2E2522'; g.fillText(w[0], 0, 0);
      g.restore();
      // landing puff: short speed ticks under the word
      if (lt > 0 && lt < .25 && ot <= 0) { const u = lt / .25; g.save(); g.globalAlpha = 1 - u; g.strokeStyle = '#E9BE5C'; g.lineWidth = 6; g.lineCap = 'round';
        for (const s of [-1, 1]) for (let k = 0; k < 2; k++) { const bx = cx + s * (ws[i] / 2 + 10 + k * 22), by = Y[ln] - 20 - k * 26; g.beginPath(); g.moveTo(bx, by); g.lineTo(bx + s * (18 + 30 * u), by - 10 - 14 * u); g.stroke(); }
        g.restore(); }
    });
  }
  g.restore();
}
// the impact: crown of droplets, a central jet, foam and rings on the surface
function splash(iso, t) {
  const te = t - IMPACT; if (te < 0 || te > 2.2) return;
  const cx = 0, cy = SUBY, Z = .8, drop = tri('#EAF7FD');
  const fa = 1 - seg(te, .3, 2.0);
  if (fa > 0) {                                      // foam
    const r = 2.6 + eo(seg(te, 0, .5)) * 2.2, pts = [];
    for (let i = 0; i < 28; i++) { const a = i / 28 * TAU, w = 1 + .12 * Math.sin(i * 5.3 + te * 6); pts.push([cx + Math.cos(a) * r * w, cy + Math.sin(a) * r * w]); }
    iso.flat(pts, Z + .01, '#F4FBFE', { layer: 3.42, a: .8 * fa });
  }
  for (let j = 0; j < 3; j++) {                      // rings
    const u = te - j * .22; if (u <= 0) continue; const r = 2 + u * 6.5, a = .8 * (1 - seg(u, .2, 1.8)); if (a <= 0) continue;
    const pts = []; for (let i = 0; i <= 40; i++) { const q = i / 40 * TAU; pts.push([cx + Math.cos(q) * r, cy + Math.sin(q) * r, Z]); }
    iso.line3(pts, '#FBFEFF', 4 - j, { a, layer: 3.43 });
  }
  for (let i = 0; i < 30; i++) {                     // crown droplets
    const a = i / 30 * TAU + hash(i) * .2, v0 = 7 + hash(i * 3) * 6, vr = 3 + hash(i * 7) * 4;
    const z = Z + v0 * te - 11 * te * te; if (z < Z || te > 1.6) continue;
    const r = 2.2 + vr * te;
    iso.sphere(cx + Math.cos(a) * r, cy + Math.sin(a) * r, z, .22 + .28 * hash(i * 11), drop, { layer: 3.5, hi: false, cull: false });
  }
  const jt = te - .25;                               // central jet
  if (jt > 0 && jt < 1.1) for (let i = 0; i < 5; i++) {
    const z = Z + (9 - i * 1.2) * jt - 12 * jt * jt; if (z < Z) continue;
    iso.sphere(cx + Math.sin(i * 2) * .2, cy, z, .55 - i * .07, drop, { layer: 3.5, hi: false, cull: false });
  }
}
// speed streaks: light lines rushing up past the camera
function streaks(g, W, H, t, spd, vz) {
  const rew = t > HOOK - .32 && t < HOOK + .1;
  if (spd < 120 && !rew) return;
  const n = rew ? 60 : Math.min(46, Math.round(spd / 30)), v = rew ? -9000 : spd * 2.4, len = rew ? 420 : Math.min(260, spd * .16);
  g.save(); g.lineCap = 'round';
  for (let i = 0; i < n; i++) {
    const x = hash(i * 3.7) * W, ph = hash(i * 1.3) * (H + len), y = ((ph - t * v * (.6 + hash(i) * .8)) % (H + len) + H + len) % (H + len) - len;
    g.strokeStyle = `rgba(255,255,255,${(rew ? .55 : .16 + .14 * hash(i * 9)) * clamp(spd / 500 + (rew ? 1 : 0))})`; g.lineWidth = 2 + hash(i * 5) * 3;
    g.beginPath(); g.moveTo(x, y); g.lineTo(x, y + len); g.stroke();
  }
  g.restore();
}
function hookTag(g, W, t) {            // flash-forward tag
  const a = seg(t, .05, .25) * (1 - seg(t, HOOK - .35, HOOK - .2)); if (a <= 0) return;
  g.save(); g.globalAlpha = a * (Math.floor(t * 3) % 2 ? 1 : .55);
  g.beginPath(); g.arc(W - 250, 196, 13, 0, TAU); g.fillStyle = '#E04434'; g.fill();
  haloText(g, 'LIVE', W - 226, 208, { font: `700 34px ${FONT}`, track: 5, color: '#E04434', hw: 9 });
  g.restore();
}

// ---------- render ----------
export function render(g, tR, W = 1080, H = 1920) {
  const t = tR;
  const iso = new Iso(g, W, H);
  // dynamics: milestone punches, wobble at speed
  let punch = 0; for (const id of MIL) { const x = tR - L[id].t0 + .05; if (x > 0 && x < 1) punch = Math.max(punch, Math.exp(-x / .2) * (1 - Math.exp(-x / .03))); }
  const hookX = tR < HOOK ? 1 : 0;
  const zs = subZ(t), vz = (subZ(t + .05) - zs) / .05, d = depthAt(zs);
  const k = Math.exp(lnk(t)) * (1 + .13 * punch) * (1 + .1 * hookX);
  // camera: hold on the title, follow the sub, then pull out to the whole column
  const follow = zs - .4, open = 1.6;
  let cz = lerp(2.2, follow, ss(seg(t, IMPACT + .1, IMPACT + 1.0)));
  const pull = ss(seg(t, T_PULL, T_PULL1));
  cz = lerp(cz, (2 + ZQ) / 2, pull);
  let shake = 0;
  if (t > L.l08.t0 + .2 && t < L.l08.t0 + .6) shake = Math.sin(t * 90) * .08 * (1 - seg(t, L.l08.t0 + .2, L.l08.t0 + .6));
  if (t > T_CUT + .6 && t < L.l11.t0 + .8) shake = Math.sin(t * 70) * .05;
  const te = tR - IMPACT; if (te > 0 && te < .6) shake = Math.sin(tR * 70) * .22 * (1 - te / .6);
  iso.cam = { x: 0, y: 0, z: cz + shake, k };
  const spd = Math.abs(vz) * k, wob = Math.sin(tR * 2.3) * .014 * clamp(spd / 900) + (tR < HOOK ? Math.sin(tR * 23) * .006 : 0);
  g.save(); g.translate(W / 2, H / 2); g.rotate(wob); g.scale(1.04, 1.04); g.translate(-W / 2, -H / 2);

  // ground: pale paper, a little cooler as we go deep; iso dot lattice scrolls with the camera
  const bg = hex(mix('#F2E6D0', '#D8DCE2', dark(d) * .8));
  g.fillStyle = bg; g.fillRect(0, 0, W, H);
  const sp = 38, oy = ((cz * k) % sp + sp) % sp;
  g.fillStyle = 'rgba(46,37,34,.10)';
  for (let y = -sp; y < H + sp; y += sp / 2) { const row = Math.round(y / (sp / 2)); for (let x = (row % 2 ? sp * C30 : 0); x < W; x += sp * C30 * 2) { g.beginPath(); g.arc(x, y + oy, 1.6, 0, TAU); g.fill(); } }

  // visible z range
  const zTop = cz + (H / 2) / k + 2 * R, zBot = cz - (H / 2) / k - 2 * R;
  // soft shadow of the column on the ground (style: board floats on pale ground)
  walls(iso, zTop, zBot);
  if (zTop > -3) { surface(iso, t); splash(iso, t); }
  wallLabels(iso, t, k);
  title(iso, t);

  const lod = k > 22;
  const anchors = {};
  const near = z => z < zTop + 4 && z > zBot - 4;
  if (lod) {
    if (near(MZ[1])) anchors.l01 = diver(iso, t);
    if (near(MZ[2])) anchors.l02 = sunIcon(iso, g, t);
    if (near(MZ[3])) anchors.l03 = jelly(iso, t);
    if (near(MZ[4])) anchors.l04 = whale(iso, t);
    if (near(MZ[5])) anchors.l05 = wreck(iso, t);
    if (near(MZ[6])) anchors.l06 = [2.4, -3.2, MZ[6] + 1.2];
    if (near(MZ[7])) anchors.l07 = snailfish(iso, t);
    if (near(MZ[8])) anchors.l08 = [2.6, -2.6, ZFLOOR];
    if (near(MZ[9])) anchors.l11 = [2.6, -3.0, MZ[9] + 1];
  }
  if (near(ZFLOOR)) floorCore(iso, t);
  // headlight sits between the world and the sub
  iso.add(0, () => headlight(iso, g, t, zs, d), 2.7);
  if (lod) { subBubbles(iso, t, zs, vz); debris(iso, t, zs); dust(iso, t); }
  // route line from the surface to the sub (drawn during the pull-out)
  const rA = seg(t, T_PULL + .2, T_PULL1 - .4);
  if (rA > 0) { const pts = []; for (let z = .35; z >= zs; z -= 1) pts.push([0, SUBY, z]); pts.push([0, SUBY, zs]); iso.line3(pts, '#FBF4E6', 3, { dash: [9, 9], a: rA, layer: 2.95 }); }
  drawSub(iso, t, zs, d);
  iso.flush();

  // "?" plate: the unanswered station below the column
  const qa = seg(t, T_PULL + 1.2, T_PULL + 2.2);
  if (qa > 0) {
    const pts = [[-R, -R], [R, -R], [R, R], [-R, R], [-R, -R]].map(p => iso.P(p[0], p[1], ZQ));
    g.save(); g.globalAlpha = qa; g.beginPath(); pts.slice(0, 4).forEach((p, i) => i ? g.lineTo(p[0], p[1]) : g.moveTo(p[0], p[1])); g.closePath(); g.fillStyle = '#FBF4E6'; g.fill(); g.restore();
    cutLine(g, pts, eo(qa));
    const [qx, qy] = iso.P(0, 0, ZQ);
    haloText(g, '?', qx, qy + 26 * (k / 9.3) * .6, { font: `700 ${Math.round(70 * back(qa, 2))}px ${FONT}`, align: 'center', color: '#CF5140' });
    // dashed route continues from the sub to the plate
    const [ax, ay] = iso.P(0, SUBY, zs - 1), [bx, by] = iso.P(0, 0, ZQ + .2);
    g.save(); g.strokeStyle = '#CF5140'; g.lineWidth = 3; g.setLineDash([8, 8]); g.beginPath(); g.moveTo(ax, ay); g.lineTo(lerp(ax, bx, eo(qa)), lerp(ay, by, eo(qa))); g.stroke(); g.restore();
  }

  streaks(g, W, H, tR, spd, vz);
  g.restore();
  // tracking ring on the sub when small
  const [sx, sy] = iso.P(0, SUBY, zs + .3);
  ring(g, sx, sy, 34, seg(t, T_PULL + .8, T_PULL + 1.6), t, 'YOU ARE HERE', { ang: -2.6, ts: 22 });

  // label pins
  const PINS = {
    l01: { title: 'SCUBA LIMIT', num: '40', dir: -1 },
    l02: { title: 'SUNLIGHT FADES', num: '200', dir: -1 },
    l03: { title: 'MIDNIGHT ZONE', num: '1,000', dir: -1 },
    l04: { title: 'SPERM WHALES', num: '2,000', dir: -1 },
    l05: { title: 'TITANIC WRECK', num: '3,800', dir: -1 },
    l06: { title: 'HADAL ZONE', num: '6,000', dir: -1 },
    l07: { title: 'DEEPEST FISH FILMED', num: '8,336', dir: -1 },
    l08: { title: 'OCEAN FLOOR', num: '10,935', dir: -1 },
    l11: { title: 'DEEPEST HOLE EVER DUG', num: '12,262', dir: -1 },
  };
  for (const id in PINS) {
    const an = anchors[id]; if (!an) continue;
    const l = L[id], end = id === 'l08' ? L.l10.t0 + .2 : l.t1 + .8;
    const a = seg(t, l.t0 - .2, l.t0 + .45), fade = 1 - seg(t, end, end + .4);
    if (a <= 0 || fade <= 0) continue;
    if (id === 'l02') {         // sun icon greys out as light fades
      const [px, py] = iso.P(...an); g.save(); g.globalAlpha = fade * seg(t, l.t0 - .3, l.t0); ICON_SUN(g, px, py, 70, 1 - seg(t, l.t0 + .3, l.t1)); g.restore();
    }
    pin(iso, an[0], an[1], an[2], { ...PINS[id], unit: 'M', a, fade, up: id === 'l08' ? 330 : 46, len: 90, ns: 60, ts: 28 });
  }

  const dShow = d;
  hud(g, W, tR, dShow, seg(tR, L.l09.t0, L.l09.t0 + .3) * (1 - seg(tR, L.l09.t1, L.l09.t1 + .4)), punch, hookX);
  // flashes: each milestone, and the rewind whip
  let fl = .2 * punch; if (te > 0 && te < .5) fl = Math.max(fl, .7 * Math.exp(-te / .07));
  if (fl > .01) { g.fillStyle = `rgba(255,252,240,${fl})`; g.fillRect(0, 0, W, H); }
  scaleLegend(g, iso, t);
  subtitle(g, W, H, tR);
  hookText(g, W, tR);
  // closing beat: fade the HUD and subtitle area cleanly at the very end
}
function ICON_SUN(g, x, y, s, lit) {
  g.save(); g.translate(x, y); const c = hex(mix('#B7AFA0', '#E4A93A', lit)); g.strokeStyle = c; g.lineWidth = s * .09; g.lineCap = 'round';
  for (let i = 0; i < 8; i++) { const a = i / 8 * TAU; g.beginPath(); g.moveTo(Math.cos(a) * s * .36, Math.sin(a) * s * .36); g.lineTo(Math.cos(a) * s * .5, Math.sin(a) * s * .5); g.stroke(); }
  g.beginPath(); g.arc(0, 0, s * .26, 0, TAU); g.fillStyle = c; g.fill(); g.restore();
}
