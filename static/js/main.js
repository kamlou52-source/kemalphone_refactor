// main.js — version sans burger / cohérente avec main.css

// Exécuter quand le DOM est prêt (si <script defer>, ça fonctionne aussi sans)
document.addEventListener("DOMContentLoaded", () => {
  // 1) Charger les dernières demandes dans le sous-menu (si l’élément existe)
  const recentList = document.getElementById("nav-recent");
  if (recentList) {
    fetch("/api/userinputs?limit=8")
      .then((r) => r.json())
      .then((items) => {
        recentList.innerHTML = "";
        if (!items.length) {
          recentList.innerHTML = '<li class="nav-muted">Aucune demande</li>';
          return;
        }
        for (const it of items) {
          const li = document.createElement("li");
          li.innerHTML = `
            <a class="nav-link" href="/request/${it.id}">
              ${escapeHtml(it.fname)} — <span class="nav-muted">${escapeHtml(it.modele)}</span>
            </a>`;
          recentList.appendChild(li);
        }
      })
      .catch(() => {
        recentList.innerHTML = '<li class="nav-muted">Erreur de chargement</li>';
      });
  }

  // 2) Validation minimale côté client (fallback)
  document.addEventListener("submit", (e) => {
    const form = e.target;
    if (!form.matches("form")) return;

    const fname = form.querySelector("#fname");
    if (fname) {
      const value = fname.value.trim();
      // Lettres + accents, tiret et espace autorisés
      const re = /^[A-Za-zÀ-ÖØ-öø-ÿ -]+$/;
      if (!re.test(value)) {
        e.preventDefault();
        alert("Le prénom doit contenir uniquement des lettres (éventuellement espaces ou tirets).");
        fname.focus();
      }
    }
  });

  // 3) Bascule de thème (optionnelle : nécessite un bouton #themeToggle)
  const root = document.documentElement;
  const saved = localStorage.getItem("theme");
  if (saved === "light") root.classList.add("light");

  const themeBtn = document.getElementById("themeToggle");
  if (themeBtn) {
    themeBtn.addEventListener("click", () => {
      root.classList.toggle("light");
      localStorage.setItem("theme", root.classList.contains("light") ? "light" : "dark");
    });
  }
});

// Petite utilité pour échapper le HTML injecté (sécurité XSS basique)
function escapeHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

// --- README viewer + contrôle de vitesse ---
(async function readmeViewer(){
  const container = document.getElementById("readme");
  if (!container) return;

  // UI: slider de vitesse optionnel (0.25x à 3x)
  let speedFactor = 1; // 1 = normal ; <1 = plus lent ; >1 = plus rapide
  const speedInput = document.getElementById("readmeSpeed");
  if (speedInput) {
    speedInput.addEventListener("input", () => {
      speedFactor = parseFloat(speedInput.value || "1");
    });
  }

  // Charge les lignes
  const resp = await fetch("/api/readme");
  const data = await resp.json();
  const lines = data?.lines || [];

  // Machine à écrire
  const baseDelay = 400;     // ms (plus grand = plus lent)
  const baseChars = 20;      // nb de caractères par tick (plus petit = plus lent)
  let i = 0, j = 0;         // i: index ligne, j: index caractère
  let current = "";         // ligne en cours

  function tick() {
    if (i >= lines.length) return; // fini
    const target = lines[i] + (i < lines.length - 1 ? "\n" : "");
    const stepChars = Math.max(1, Math.round(baseChars * speedFactor));
    j = Math.min(j + stepChars, target.length);
    current = target.slice(0, j);

    // Affiche
    container.textContent = lines.slice(0, i).join("\n") + (i ? "\n" : "") + current;

    if (j >= target.length) { i++; j = 0; }

    const delay = Math.max(10, Math.round(baseDelay / Math.max(0.25, speedFactor)));
    setTimeout(tick, delay);
  }
  tick();
})();
