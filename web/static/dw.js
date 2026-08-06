/*
 * Composants Alpine de Democracy Watch.
 *
 * Les deux seules fonctions qui ont besoin d'un état client : l'historique de
 * consultation et le seuil de similarité, tous deux persistés dans localStorage.
 * Aucune garde d'hydratation n'est nécessaire — un magasin purement client n'a
 * pas de rendu serveur à faire concorder.
 *
 * Défini sur `window` et chargé avant Alpine (qui, en `defer`, s'initialise au
 * DOMContentLoaded) pour que les attributs `x-data` trouvent ces fonctions.
 */

const HISTORY_KEY = 'dw_amendment_history'
const MAX_ENTRIES = 50
const RECENT_ENTRIES = 20

const THRESHOLD_KEY = 'dw_similarity_threshold'
const THRESHOLD_MIN = 0
const THRESHOLD_MAX = 95
const THRESHOLD_DEFAULT = 70

/** Lecture tolérante : un localStorage indisponible (mode privé, quota) ne doit
 *  pas casser la page, seulement priver l'utilisateur de la persistance. */
function readStorage(key) {
  try {
    return window.localStorage.getItem(key)
  } catch {
    return null
  }
}

function writeStorage(key, value) {
  try {
    window.localStorage.setItem(key, value)
  } catch {
    /* pas de persistance disponible : l'état reste en mémoire */
  }
}

window.dwHistory = function dwHistory(currentUid = '') {
  return {
    currentUid,
    entries: [],
    /** Horloge partagée par tous les libellés relatifs, avancée une fois par
     *  minute : la lire à chaque rendu ferait autant de `Date.now()` que de
     *  lignes, pour un résultat identique. */
    now: 0,

    init() {
      this.entries = this.load()
      this.now = Date.now()
      setInterval(() => { this.now = Date.now() }, 60_000)

      // Poussée de l'amendement courant. Le `data-dw-entry` est posé par la vue
      // sur le conteneur de la page : le pousser ici plutôt que depuis un
      // second `x-init` évite d'avoir deux sources de vérité sur le magasin.
      const node = document.querySelector('[data-dw-entry]')
      if (node) {
        try {
          this.push(JSON.parse(node.dataset.dwEntry))
        } catch (err) {
          // Signalé plutôt que tu : un attribut illisible veut dire que la vue
          // rend un JSON mal formé, et l'historique reste alors silencieusement
          // vide — c'est précisément ce qui rendait ce défaut invisible.
          console.error('dwHistory : `data-dw-entry` illisible', err)
        }
      }
    },

    load() {
      try {
        const parsed = JSON.parse(readStorage(HISTORY_KEY) || '[]')
        return Array.isArray(parsed) ? parsed.slice(0, MAX_ENTRIES) : []
      } catch {
        return []
      }
    },

    save() {
      writeStorage(HISTORY_KEY, JSON.stringify(this.entries))
    },

    push(entry) {
      if (!entry || !entry.uid) return
      // L'entrée existante est retirée avant d'être réinsérée en tête, de sorte
      // qu'une seconde visite remonte la ligne au lieu de la dupliquer. Son
      // épinglage est conservé.
      const previous = this.entries.find(e => e.uid === entry.uid)
      this.entries = [
        { ...entry, pinned: previous?.pinned || false, visitedAt: Date.now() },
        ...this.entries.filter(e => e.uid !== entry.uid),
      ].slice(0, MAX_ENTRIES)
      this.save()
    },

    pin(uid) {
      this.entries = this.entries.map(e => (e.uid === uid ? { ...e, pinned: !e.pinned } : e))
      this.save()
    },

    /** Vide tout, épinglés compris — c'est ce que « Vider l'historique »
     *  annonce. Le bouton appelait auparavant la variante préservant les
     *  épingles et paraissait donc sans effet sur elles. */
    clear() {
      this.entries = []
      this.save()
    },

    /** Ne retire que les entrées non épinglées. */
    clearUnpinned() {
      this.entries = this.entries.filter(e => e.pinned)
      this.save()
    },

    get recent() {
      return this.entries.slice(0, RECENT_ENTRIES)
    },

    get pinned() {
      return this.entries.filter(e => e.pinned)
    },

    relativeTime(ts) {
      if (!this.now || !ts) return ''
      const minutes = Math.floor((this.now - ts) / 60_000)
      if (minutes < 1) return 'à l\'instant'
      if (minutes < 60) return `il y a ${minutes} min`
      return `il y a ${Math.floor(minutes / 60)} h`
    },
  }
}

window.dwThreshold = function dwThreshold() {
  return {
    threshold: THRESHOLD_DEFAULT,

    init() {
      const raw = parseInt(readStorage(THRESHOLD_KEY), 10)
      if (Number.isFinite(raw)) this.threshold = this.clamp(raw)
    },

    clamp(value) {
      return Math.max(THRESHOLD_MIN, Math.min(THRESHOLD_MAX, Math.round(value)))
    },

    save() {
      this.threshold = this.clamp(this.threshold)
      writeStorage(THRESHOLD_KEY, String(this.threshold))
    },
  }
}

/*
 * Barre de progression des échanges HTMX.
 *
 * HTMX pose déjà `.htmx-request` sur l'élément déclencheur, mais les déclencheurs
 * sont ici dispersés (pastilles, options de menu, tri, pagination) et certains
 * sont remplacés par l'échange qu'ils ont lancé — l'indicateur disparaîtrait donc
 * avec eux. La barre est donc un élément unique, hors de la cible d'échange, et le
 * seul état suivi est « une requête est en cours sur ce panneau ».
 *
 * Le compteur, plutôt qu'un booléen, évite qu'une requête rapide terminée
 * n'éteigne la barre alors qu'une plus lente est encore en vol.
 */
const PROGRESS_ID = 'amendement-progress'
const PANEL_ID = 'amendement-results'
let pendingRequests = 0

function progressNode() {
  return document.getElementById(PROGRESS_ID)
}

/** Vrai si la requête vise le panneau d'amendements, pour ne pas réagir aux
 *  échanges d'autres blocs de la page. */
function targetsPanel(event) {
  const target = event.detail && event.detail.target
  return target instanceof Element
    && (target.id === PANEL_ID || target.closest(`#${PANEL_ID}`) !== null)
}

function renderProgress() {
  const node = progressNode()
  if (node) node.classList.toggle('is-busy', pendingRequests > 0)
}

document.addEventListener('htmx:beforeRequest', event => {
  if (!targetsPanel(event)) return
  pendingRequests += 1
  renderProgress()
})

// `afterRequest` couvre aussi les réponses en erreur, là où `afterSwap` ne serait
// pas émis : le compteur ne peut donc pas rester bloqué et laisser la barre
// tourner indéfiniment.
document.addEventListener('htmx:afterRequest', event => {
  if (!targetsPanel(event)) return
  pendingRequests = Math.max(0, pendingRequests - 1)
  renderProgress()
})

// La barre vit dans le fragment réémis en « out of band » : le nœud qui portait
// `.is-busy` est remplacé à chaque échange, d'où la réapplication après swap.
document.addEventListener('htmx:afterSwap', renderProgress)
