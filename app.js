// WineDrop PWA — tunn klient som läser statisk JSON-API.
const API = "./api";
const state = {
  lang: localStorage.getItem("wd_lang") || (navigator.language || "en").slice(0, 2),
  market: localStorage.getItem("wd_market") || null,
  exploreMarkets: JSON.parse(localStorage.getItem("wd_explore") || "null"),
  markets: [],
  wines: [],            // aktuell lista (latest eller explore) för detaljvyn
  meta: null,
  tab: "latest",
  cache: {},            // market -> latest.json
  q: "",                // fritextsök i Utforska
  watch: JSON.parse(localStorage.getItem("wd_watch") || "[]"),  // bevakade producenter
  latestSort: localStorage.getItem("wd_sort") || "rank",        // rank | score | price
  releaseDate: null,   // valt släppdatum (ISO) eller "all"
  saved: JSON.parse(localStorage.getItem("wd_saved") || "[]"),  // sparade viner (snapshot)
};

// Formatera ett släppdatum snyggt på användarens språk, t.ex. "fre 21 nov".
function fmtRelease(iso) {
  try {
    const loc = state.lang === "en" ? "en-GB" : state.lang;
    return new Intl.DateTimeFormat(loc, { weekday: "short", day: "numeric", month: "short" })
      .format(new Date(iso + "T00:00:00"));
  } catch (e) { return iso; }
}

// Sortera en kopia av vinlistan. "rank" = backendens eftertraktan-ordning.
function sortWines(wines, mode) {
  const a = wines.slice();
  if (mode === "score") a.sort((x, y) => (y.score == null ? -1 : y.score) - (x.score == null ? -1 : x.score));
  else if (mode === "price") a.sort((x, y) => (x.price == null ? Infinity : x.price) - (y.price == null ? Infinity : y.price));
  return a;  // "rank": behåll backendordningen
}
if (!window.I18N[state.lang]) state.lang = "en";

// ---------- bevakade producenter ----------
const isWatched = (name) =>
  !!name && state.watch.some((p) => p.toLowerCase() === name.toLowerCase());

// ---------- sparade viner ----------
const isSaved = (id) => state.saved.some((w) => w.id === id);

function toggleSave(wine) {
  const i = state.saved.findIndex((w) => w.id === wine.id);
  if (i >= 0) state.saved.splice(i, 1);
  else state.saved.unshift(wine);   // senast sparad överst
  localStorage.setItem("wd_saved", JSON.stringify(state.saved));
}

// Tillfälligt sortiment / småparti = eftertraktat -> visa badge
const isLimited = (w) =>
  /tillfäll|limited|small/i.test(String(w.assortment || ""));

// Stiliserad flask-ikon som fallback när produktfoto saknas/inte laddar.
// Färgad efter vintyp. Global så onerror på <img> kan anropa den.
window.WD_bottle = function (type) {
  const t = String(type || "").toLowerCase();
  let glass = "#5B2834", liquid = "#8a3a48";           // rött (default) — burgundy
  if (/mousser|sparkl|champ|cava|prosecco|skum/.test(t)) { glass = "#7D8060"; liquid = "#D5A13B"; }
  else if (/ros/.test(t)) { glass = "#B56F52"; liquid = "#e7b6a2"; }
  else if (/vit|hvit|white|valko|hvid/.test(t)) { glass = "#7D8060"; liquid = "#dcc98a"; }
  return `<svg viewBox="0 0 40 64" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
    <rect x="17" y="3" width="6" height="13" rx="1.5" fill="${glass}"/>
    <path d="M11 22c0-4 2-6 5-7h8c3 1 5 3 5 7v33a5 5 0 0 1-5 5H16a5 5 0 0 1-5-5z" fill="${glass}"/>
    <rect x="11" y="24" width="18" height="9" fill="${liquid}" opacity=".85"/>
    <rect x="11" y="37" width="18" height="15" rx="2" fill="#fff" opacity=".92"/>
  </svg>`;
};

function thumbHTML(w) {
  if (w.image) {
    return `<span class="thumb"><img src="${esc(w.image)}" loading="lazy" alt=""
      onerror="this.parentNode.innerHTML=window.WD_bottle('${esc(w.wine_type)}')"></span>`;
  }
  return `<span class="thumb">${window.WD_bottle(w.wine_type)}</span>`;
}

function toggleWatch(name) {
  if (!name) return;
  const i = state.watch.findIndex((p) => p.toLowerCase() === name.toLowerCase());
  if (i >= 0) state.watch.splice(i, 1); else state.watch.push(name);
  localStorage.setItem("wd_watch", JSON.stringify(state.watch));
  // meddela push-lagret så servern kan uppdatera bevakningslistan
  if (window.WD_syncSubscription) window.WD_syncSubscription();
}

// ---------- delbar länk ----------
function shareUrl(w) {
  return `${location.origin}${location.pathname}#${w.market}/${encodeURIComponent(w.id)}`;
}
async function doShare(w) {
  const url = shareUrl(w);
  const data = { title: "WineDrop", text: `${w.name} — ${w.producer}`, url };
  try {
    if (navigator.share) { await navigator.share(data); return; }
    await navigator.clipboard.writeText(url);
    toast(t("copied"));
  } catch (e) { /* avbruten delning */ }
}
function toast(msg) {
  let el = document.getElementById("toast");
  if (!el) {
    el = document.createElement("div"); el.id = "toast";
    el.className = "toast"; document.body.appendChild(el);
  }
  el.textContent = msg; el.classList.add("show");
  setTimeout(() => el.classList.remove("show"), 1600);
}

const $ = (s) => document.querySelector(s);
const $$ = (s) => [...document.querySelectorAll(s)];
const t = (k) => (window.I18N[state.lang] || window.I18N.en)[k] || k;
const pick = (o) => (!o || typeof o !== "object") ? "" : (o[state.lang] || o.en || Object.values(o)[0] || "");

async function getJSON(path) {
  const r = await fetch(path, { cache: "no-cache" });
  if (!r.ok) throw new Error(r.status);
  return r.json();
}

async function loadMarkets() {
  state.markets = await getJSON(`${API}/markets.json`);
  if (!state.market && state.markets.length) state.market = state.markets[0].code;
  if (!state.exploreMarkets) state.exploreMarkets = state.markets.map((m) => m.code);
}

async function marketLatest(code) {
  if (state.cache[code]) return state.cache[code];
  try {
    const d = await getJSON(`${API}/${code}/latest.json`);
    state.cache[code] = d;
    return d;
  } catch (e) {
    return { market: code, wines: [] };
  }
}

const marketByCode = (c) => state.markets.find((m) => m.code === c) || {};
const scoreClass = (s) => s == null ? "none" : s >= 90 ? "hi" : s >= 80 ? "mid" : "lo";

function esc(s) {
  return String(s == null ? "" : s).replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

// Butikslänk. För Sverige en Systembolaget-brandad knapp i deras gröna färg;
// för övriga marknader butikens namn i vinröd knapp.
function retailerButton(w) {
  if (!w.url) return "";
  if (w.market === "se") {
    return `<a class="sb-btn" href="${esc(w.url)}" target="_blank" rel="noopener"
      aria-label="Öppna på Systembolaget">
      <span class="sb-word">Systembolaget</span>
      <span class="sb-go">${t("buy")} ↗</span></a>`;
  }
  const r = marketByCode(w.market).retailer || t("buy");
  return `<a class="buy" href="${esc(w.url)}" target="_blank" rel="noopener">${esc(r)} ↗</a>`;
}

// ---------- header/nav ----------
function renderChrome() {
  $("#tagline").textContent = t("tagline");
  $("#offline").textContent = t("offline");
  $("#tabLatest").textContent = t("tabLatest");
  $("#tabExplore").textContent = t("tabExplore");
  $("#tabMine").textContent = t("tabMine");

  const mkt = $("#marketSel");
  mkt.innerHTML = state.markets.map((m) =>
    `<option value="${m.code}"${m.code === state.market ? " selected" : ""}>${m.flag} ${esc(m.name)}</option>`
  ).join("");

  const lng = $("#langSel");
  lng.innerHTML = Object.keys(window.I18N).map((l) =>
    `<option value="${l}"${l === state.lang ? " selected" : ""}>${l.toUpperCase()}</option>`
  ).join("");
}

// Bokmärkes-ikon (fylld när sparat).
function bookmarkSVG(filled) {
  return `<svg viewBox="0 0 24 24" fill="${filled ? "currentColor" : "none"}" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6.5 3.5h11a1 1 0 0 1 1 1V21l-6.5-3.8L5.5 21V4.5a1 1 0 0 1 1-1z"/></svg>`;
}

// ---------- kort ----------
function cardHTML(w, showFlag) {
  const m = showFlag ? marketByCode(w.market) : null;
  return `
    ${thumbHTML(w)}
    <span class="cardbody">
      <span class="name">${m ? m.flag + " " : ""}${esc(w.name)}${isWatched(w.producer) ? ' <b class="watchdot">★</b>' : ""}${
        isLimited(w) ? ` <b class="tag">${t("limited")}</b>` : ""}</span>
      <span class="meta">${esc(w.producer)}${w.vintage ? " · " + esc(w.vintage) : ""}${
        w.origin_country ? " · " + esc(w.origin_country) : ""}</span>
    </span>
    <span class="cardright">
      <span class="score ${scoreClass(w.score)}">${w.score ?? t("noScore")}</span>
      ${w.price ? `<span class="price">${Math.round(w.price)} ${esc(w.currency)}</span>` : ""}
    </span>
    <span class="cardsave ${isSaved(w.id) ? "on" : ""}" role="button" aria-label="${t("save")}">${bookmarkSVG(isSaved(w.id))}</span>`;
}

function listInto(container, wines, showFlag) {
  container.innerHTML = "";
  if (!wines.length) {
    container.innerHTML = `<p class="empty">${t("noWines")}</p>`;
    return;
  }
  wines.forEach((w, i) => {
    const el = document.createElement("button");
    el.className = "card";
    el.onclick = () => { state.wines = wines; renderDetail(i); };
    el.innerHTML = cardHTML(w, showFlag);
    const sv = el.querySelector(".cardsave");
    if (sv) sv.onclick = (e) => {
      e.stopPropagation();
      toggleSave(w);
      if (state.tab === "mine") { renderMine(); return; }  // uppdatera sparad-listan
      sv.classList.toggle("on", isSaved(w.id));
      sv.innerHTML = bookmarkSVG(isSaved(w.id));
    };
    container.appendChild(el);
  });
}

// ---------- SENASTE ----------
async function renderLatest() {
  $("#list").innerHTML = `<p class="empty">${t("loading")}</p>`;
  try {
    state.meta = await marketLatest(state.market);
    $("#offline").hidden = true;
  } catch (e) { $("#offline").hidden = false; }
  const m = marketByCode(state.market);
  const allWines = state.meta ? state.meta.wines || [] : [];

  // Släppväljare: gruppera på släppdatum (Systembolaget släpper på fredagar).
  const dates = [...new Set(allWines.map((w) => w.launch_date).filter(Boolean))].sort().reverse();
  if (state.releaseDate == null ||
      (state.releaseDate !== "all" && !dates.includes(state.releaseDate))) {
    state.releaseDate = dates[0] || "all";   // öppna på senaste släppet
  }
  const rbar = ensureReleaseBar();
  rbar.innerHTML = [`<button class="rchip ${state.releaseDate === "all" ? "on" : ""}" data-d="all">${t("all")}</button>`]
    .concat(dates.map((d) =>
      `<button class="rchip ${state.releaseDate === d ? "on" : ""}" data-d="${d}">${fmtRelease(d)}</button>`
    )).join("");
  rbar.querySelectorAll(".rchip").forEach((b) => {
    b.onclick = () => { state.releaseDate = b.dataset.d; renderLatest(); };
  });

  const pool = state.releaseDate === "all"
    ? allWines : allWines.filter((w) => w.launch_date === state.releaseDate);

  const label = state.releaseDate === "all"
    ? `${t("week")} ${state.meta ? state.meta.week || "" : ""}`
    : fmtRelease(state.releaseDate);
  $("#sub").textContent = `${m.retailer || ""} · ${label} · ${pool.length} ${t("results")}`;

  const modes = [["rank", t("sortSought")], ["score", t("sortScore")], ["price", t("sortCheapest")]];
  $("#latestSort").innerHTML = modes.map(([k, lbl]) =>
    `<button class="seg ${k === state.latestSort ? "on" : ""}" data-s="${k}">${lbl}</button>`
  ).join("");
  $("#latestSort").querySelectorAll(".seg").forEach((b) => {
    b.onclick = () => {
      state.latestSort = b.dataset.s;
      localStorage.setItem("wd_sort", state.latestSort);
      renderLatest();
    };
  });

  const wines = sortWines(pool, state.latestSort);
  listInto($("#list"), wines, false);
}

// Skapar (vid behov) och returnerar raden med släppdatum ovanför sorteringen.
function ensureReleaseBar() {
  let rb = document.getElementById("releaseBar");
  if (!rb) {
    rb = document.createElement("div");
    rb.id = "releaseBar";
    rb.className = "releasebar";
    const sort = document.getElementById("latestSort");
    sort.parentNode.insertBefore(rb, sort);
  }
  return rb;
}

// ---------- UTFORSKA ----------
async function renderExplore() {
  // marknads-chips
  const chips = $("#marketChips");
  chips.innerHTML = state.markets.map((m) => {
    const on = state.exploreMarkets.includes(m.code);
    return `<button class="chip ${on ? "on" : ""}" data-m="${m.code}">${m.flag} ${esc(m.name)}</button>`;
  }).join("");
  chips.querySelectorAll(".chip").forEach((b) => {
    b.onclick = () => {
      const c = b.dataset.m;
      const i = state.exploreMarkets.indexOf(c);
      if (i >= 0) state.exploreMarkets.splice(i, 1); else state.exploreMarkets.push(c);
      localStorage.setItem("wd_explore", JSON.stringify(state.exploreMarkets));
      renderExplore();
    };
  });

  // hämta valda marknader
  $("#exploreList").innerHTML = `<p class="empty">${t("loading")}</p>`;
  const datas = await Promise.all(state.exploreMarkets.map(marketLatest));
  let wines = [];
  datas.forEach((d) => wines = wines.concat(d.wines || []));

  // fyll filteralternativ
  fillFilter("#fType", "wine_type", t("type"), wines);
  fillFilter("#fCountry", "origin_country", t("country"), wines);
  const sortSel = $("#fSort");
  const searchEl = $("#fSearch");
  searchEl.placeholder = t("search");
  if (!sortSel.dataset.init) {
    sortSel.innerHTML =
      `<option value="score">${t("sortScore")}</option>` +
      `<option value="pa">${t("sortPriceAsc")}</option>` +
      `<option value="pd">${t("sortPriceDesc")}</option>`;
    sortSel.dataset.init = "1";
    sortSel.onchange = renderExplore;
    $("#fType").onchange = renderExplore;
    $("#fCountry").onchange = renderExplore;
    searchEl.oninput = () => { state.q = searchEl.value; renderExplore(); };
  }

  // filtrera + sortera
  const ft = $("#fType").value, fc = $("#fCountry").value, fs = sortSel.value;
  const q = state.q.trim().toLowerCase();
  wines = wines.filter((w) =>
    (!ft || w.wine_type === ft) && (!fc || w.origin_country === fc) &&
    (!q || (w.name + " " + w.producer).toLowerCase().includes(q)));
  wines.sort((a, b) =>
    fs === "pa" ? (a.price || 1e9) - (b.price || 1e9)
    : fs === "pd" ? (b.price || 0) - (a.price || 0)
    : (b.score || 0) - (a.score || 0));

  $("#exploreCount").textContent = `${wines.length} ${t("results")}`;
  listInto($("#exploreList"), wines, true);
}

function fillFilter(sel, field, label, wines) {
  const el = $(sel);
  const cur = el.value;
  const vals = [...new Set(wines.map((w) => w[field]).filter(Boolean))].sort();
  el.innerHTML = `<option value="">${label}: ${t("all")}</option>` +
    vals.map((v) => `<option value="${esc(v)}">${esc(v)}</option>`).join("");
  if (vals.includes(cur)) el.value = cur;
}

// ---------- MINA VINER ----------
async function renderMine() {
  const body = $("#mineBody");
  body.innerHTML = `
    <h3 class="tsection">${t("saved")}</h3><div id="savedList"></div>
    <h3 class="tsection">${t("followedProducers")}</h3><div id="watchWrap"></div>`;

  // Sparade viner
  if (state.saved.length) listInto($("#savedList"), state.saved, true);
  else $("#savedList").innerHTML = `<p class="empty">${t("emptySaved")}</p>`;

  // Bevakade producenter
  const wrap = $("#watchWrap");
  if (!state.watch.length) {
    wrap.innerHTML = `<p class="empty">${t("emptyWatch")}</p>`;
    return;
  }
  await marketLatest(state.market);   // se till att någon marknad är laddad
  const chips = state.watch.map((p) =>
    `<button class="chip on" data-p="${esc(p)}">★ ${esc(p)}</button>`).join("");
  wrap.innerHTML = `<div class="chips">${chips}</div><div id="watchWines"></div>`;
  wrap.querySelectorAll(".chip").forEach((b) => {
    b.onclick = () => { toggleWatch(b.dataset.p); renderMine(); };
  });

  // Viner från bevakade producenter i laddad data (dedup)
  const seen = {}, wines = [];
  Object.values(state.cache).forEach((d) => (d.wines || []).forEach((w) => {
    if (isWatched(w.producer) && !seen[w.id]) { seen[w.id] = 1; wines.push(w); }
  }));
  if (wines.length) listInto($("#watchWines"), wines, true);
  else $("#watchWines").innerHTML = `<p class="empty">${t("noWines")}</p>`;
}

// ---------- DETALJ ----------
function renderDetail(i) {
  const w = state.wines[i];
  const watched = isWatched(w.producer);
  $("#detailBody").innerHTML = `
    <div class="detailtop">
      <button class="back" id="backBtn">‹ ${t("back")}</button>
      <span class="dactions">
        <button class="iconbtn ${isSaved(w.id) ? "on" : ""}" id="saveBtn"><svg class="mini" viewBox="0 0 24 24" fill="${isSaved(w.id) ? "currentColor" : "none"}" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6.5 3.5h11a1 1 0 0 1 1 1V21l-6.5-3.8L5.5 21V4.5a1 1 0 0 1 1-1z"/></svg>${isSaved(w.id) ? t("savedState") : t("save")}</button>
        <button class="iconbtn" id="shareBtn" title="${t("share")}">↗ ${t("share")}</button>
      </span>
    </div>
    <div class="hero">${w.image
      ? `<img src="${esc(w.image)}" alt="" onerror="this.parentNode.innerHTML=window.WD_bottle('${esc(w.wine_type)}')">`
      : window.WD_bottle(w.wine_type)}</div>
    <div class="dhead">
      <span class="score ${scoreClass(w.score)} big">${w.score ?? t("noScore")}</span>
      <div><h2>${esc(w.name)}</h2>
        <p class="meta">${esc(w.producer)}${w.vintage ? " · " + esc(w.vintage) : ""}${
          w.origin_country ? " · " + esc(w.origin_country) : ""
        }${w.price ? " · " + Math.round(w.price) + " " + esc(w.currency) : ""}</p></div>
    </div>
    ${w.producer ? `<button class="followbtn ${watched ? "on" : ""}" id="followBtn">
        ${watched ? "★ " + t("following") : "☆ " + t("follow")}</button>` : ""}
    <p class="verdict">${esc(pick(w.verdict))}</p>
    ${pick(w.taste_notes) ? `<p><strong>${t("tasteNotes")}:</strong> ${esc(pick(w.taste_notes))}</p>` : ""}
    ${pick(w.pairing) ? `<p><strong>${t("pairing")}:</strong> ${esc(pick(w.pairing))}</p>` : ""}
    ${retailerButton(w)}
    ${(w.sources && w.sources.length) ? `<p class="src"><strong>${t("sources")}:</strong> ${
        w.sources.map((s) => `<a href="${esc(s.url)}" target="_blank" rel="noopener">${esc(s.source)} ↗</a>`).join(" · ")
      }</p>` : ""}`;
  $("#backBtn").onclick = () => { try { history.replaceState(null, "", location.pathname); } catch (e) {} showTab(state.tab); };
  $("#shareBtn").onclick = () => doShare(w);
  $("#saveBtn").onclick = () => { toggleSave(w); toast(isSaved(w.id) ? t("savedState") : t("save")); renderDetail(i); };
  const fb = $("#followBtn");
  if (fb) fb.onclick = () => { toggleWatch(w.producer); renderDetail(i); };
  try { location.hash = `${w.market}/${encodeURIComponent(w.id)}`; } catch (e) {}
  $$("main > section").forEach((s) => s.hidden = s.id !== "detailView");
  window.scrollTo(0, 0);
}

// Öppna ett specifikt vin från en delad länk (#market/id)
async function openFromHash() {
  let raw = "";
  try { raw = location.hash || ""; } catch (e) { return false; }
  const h = decodeURIComponent(raw.replace(/^#/, ""));
  const [market, id] = h.split("/");
  if (!market || !id) return false;
  const data = await marketLatest(market);
  const idx = (data.wines || []).findIndex((w) => w.id === id);
  if (idx < 0) return false;
  state.market = market;
  state.wines = data.wines;
  renderDetail(idx);
  return true;
}

// ---------- flikar ----------
function showTab(tab) {
  state.tab = tab;
  $$("#tabbar .tab").forEach((b) => b.classList.toggle("active", b.dataset.tab === tab));
  const map = { latest: "latestView", explore: "exploreView", mine: "mineView" };
  $$("main > section").forEach((s) => s.hidden = s.id !== map[tab]);
  // marknadsväljaren i headern gäller Senaste, inte Utforska/Mina viner
  $("#marketControl").style.display = (tab === "explore" || tab === "mine") ? "none" : "flex";
  window.scrollTo(0, 0);
  if (tab === "latest") renderLatest();
  if (tab === "explore") renderExplore();
  if (tab === "mine") renderMine();
}

function bind() {
  $("#marketSel").onchange = (e) => {
    state.market = e.target.value;
    localStorage.setItem("wd_market", state.market);
    showTab(state.tab);
  };
  $("#langSel").onchange = (e) => {
    state.lang = e.target.value;
    localStorage.setItem("wd_lang", state.lang);
    document.documentElement.lang = state.lang;
    renderChrome();
    $("#fSort").dataset.init = "";   // tvinga omritning av filteretiketter
    showTab(state.tab);
  };
  $$("#tabbar .tab").forEach((b) => b.onclick = () => showTab(b.dataset.tab));
}

(async function init() {
  document.documentElement.lang = state.lang;
  bind();
  try {
    await loadMarkets();
    renderChrome();
    // Delad länk? Öppna vinet direkt, annars starta på Senaste.
    let opened = false;
    try { opened = await openFromHash(); } catch (e) {}
    if (!opened) showTab("latest");
  } catch (e) {
    $("#list").innerHTML = `<p class="empty">API saknas — kör backend först (python run.py --demo).</p>`;
  }
  if ("serviceWorker" in navigator) navigator.serviceWorker.register("./sw.js").catch(() => {});
})();
