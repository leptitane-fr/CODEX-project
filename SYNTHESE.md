# Synthèse intégrale des travaux — Toy Model de la TEI

*Compilation de bout en bout du dépôt `TEI-reproductibility`, de la première
expérience (6 juillet 2026) à la dernière (10 juillet 2026). Ce document
raconte le fil complet : les questions posées, les chemins empruntés et
**pourquoi**, les réussites, les échecs, les retours en arrière, et les pièges
méthodologiques évités. Le détail brut de chaque étape vit dans `math/` ; ce
récit relie les morceaux. Les résumés canoniques restent `CLAUDE.md` (pour les
assistants) et `README.md` (pour un lecteur nouveau).*

---

## 0. Ce que ce dépôt est, et la discipline qui le gouverne

La **Théorie de l'Émergence Informationnelle** (TEI, Stéphane Goulet, v5.0)
propose que l'espace, le temps et la matière observés *émergent* d'un substrat
causal discret et non-spatial. Ce dépôt n'est pas la théorie : c'est un **toy
model computationnel** qui teste, une brique à la fois, si des règles
purement locales et sans espace imposé peuvent faire émerger les propriétés
que la TEI leur attribue.

**La règle absolue, héritée d'un échec.** Une version antérieure (TEI 3.x)
avait « dérivé » la constante de structure fine et les pics du CMB par
ajustement numérique post-hoc déguisé en calcul ; les deux furent réfutés.
Depuis, le projet s'interdit formellement de traiter un nombre « qui tombe
juste » comme une validation sans provenance indépendante et explicite. Dans
ce dépôt, cela se traduit par une exigence gravée dans chaque étape :

- **Zéro paramètre libre accordé vers une cible.** On ne règle jamais un knob
  jusqu'à ce qu'un exposant atterrisse près de 3, ni ne choisit la métrique
  qui « flatte » l'hypothèse.
- **Critère de succès pré-enregistré** *avant* de lancer une étude.
- **Les négatifs sont des résultats**, documentés avec leur mode d'échec nommé.
- **Une mesure cassée n'est jamais un résultat** : on la corrige et on le dit.

Ce document montre que cette discipline a tenu du premier au dernier commit —
et que, paradoxalement, c'est en refusant de fabriquer les résultats espérés
(N³, le halo gravitationnel, l'inertie) que le modèle a produit ses vraies
découvertes (la matière, sa thermodynamique).

**Le fil conducteur, en une phrase.** Le substrat de la TEI produit
*spontanément* de la matière et une thermodynamique complète (gaz, liquide,
cristal, verre) — mais **résiste** à produire de l'espace vide et du mouvement
inertiel. Il conserve *ce qu'est* un corps et *où* il est, jamais *comment il
bouge*.

---

## Acte I — L'instrument et la question (6 juillet)

### La règle du jeu : mesurer la croissance causale

La question ouverte de la TEI (Partie 3.2 / 7.5) : le nombre de nœuds
atteignables en N pas causaux (« ticks ») depuis un point croît-il
*polynomialement* (comme N^dim, idéalement N³), et non *exponentiellement*
comme un graphe quelconque ? Pour trancher, il faut deux repères.

### Réussite : l'étalon (sprinkling de Minkowski)

`sprinkle_minkowski` + `reachable_within_ticks` sème des points de Poisson
dans un espace-temps de Minkowski de dimension `dim` et mesure la croissance
du cône de lumière futur. Le volume d'un cône jusqu'au temps propre τ croît
comme τ^dim — c'est l'**estimateur de dimension de Myrheim-Meyer**, théorie
standard des causal sets (Bombelli-Lee-Meyer-Sorkin 1987), *pas* un résultat
de la TEI. Provenance consignée dans `math/causal_set_dimension.md`. Validé
numériquement en dim 2, 3, 4. **C'est un instrument, pas une réponse** : la
dimension y est *imposée de l'extérieur* avant de placer le moindre point.

### Le contraste : le graphe générique

`generate_random_dag` : un DAG causal quelconque. Sa croissance sature le
graphe entier en ~7 hops — le « régime générique » exponentiel que la TEI
prétend éviter. Repère négatif en place.

**La vraie question, maintenant nette** : une règle *locale et non-embarquée*
peut-elle produire une croissance polynomiale d'exposant stable, sans qu'on
lui ait soufflé la dimension ?

---

## Acte II — La Règle de l'Ombre Causale (6-7 juillet)

### Le mécanisme candidat de la TEI

`generate_tei_shadow_graph` implémente la « Règle de l'Ombre Causale » : chaque
nouveau nœud se connecte à ≤ k nœuds existants, sous une contrainte dure — les
parents choisis doivent être **mutuellement indépendants causalement** (aucun
chemin dirigé entre deux d'entre eux). L'ensemble d'arêtes est donc toujours
une réduction transitive stricte. Aucun espace, aucune métrique.

### Réussite partielle, échec sur la cible

Détail brut : `math/tei_shadow_rule_analysis.md`, Partie A.

- **Réussite** : la règle *casse* le régime exponentiel générique. Là où le
  random-dag sature en 7 hops, l'ombre causale n'atteint que 2-14 % d'un
  graphe de 300 000 nœuds après 50 hops. C'est un effet réel et reproductible
  de la contrainte d'antichaîne.
- **Échec** : l'exposant *ne se stabilise pas*. Il dérive vers le haut (k=3 :
  2.1 sur la première moitié → 3.5 sur la seconde), la pente locale est
  bruitée, jamais plate. Un exposant qui dérive n'est pas une loi de
  puissance. **N³ n'est pas confirmé.** Le fait que k=3 « encadre » 3 est
  précisément la coïncidence que la discipline interdit de lire comme une
  confirmation.

### Retour en arrière n°1 : changer la métrique de profondeur

**Pourquoi** : hypothèse que ce sont les *raccourcis géométriques* du plus
court chemin (des arêtes longue-portée depuis des nœuds restés éligibles),
et non la règle elle-même, qui gonflent la croissance. Un graphe relationnel
pur n'a aucune métrique embarquée pour justifier le plus court chemin ; le
*plus long chemin dirigé* est le meilleur analogue du « temps propre » (chaque
arête = un délai de relais). Ajout de `longest_path_depths` /
`reachable_within_depth`.

Résultat (Partie B) : le drift monotone disparaît — remplacé par une **bosse**
(montée puis descente), pas un plateau. Retirer l'artefact du raccourci n'a
pas révélé de loi stable dessous ; ça a révélé une *autre* forme de
non-stationnarité. Les deux métriques s'accordent : la croissance n'est une
loi de puissance à exposant fixe *nulle part* dans les plages testées. Et le
choix de la métrique n'est pas laissé au hasard : on rapporte les deux, pas
celle qui flatte.

### Piège méthodologique évité (consigné publiquement)

Un premier passage de la Partie B ajustait la pente sur l'*indice local* du
tableau tranché au lieu des vraies valeurs de profondeur. Bug → un exposant
faussement « stable » à ~0.3, un résultat frappant et **faux**. Attrapé avant
publication. Il est documenté *dans* le fichier d'analyse, pas caché — parce
qu'attraper une fausse stabilisation avant de la rapporter *est* la discipline.

---

## Acte III — L'architecture événementielle (7 juillet)

### Pourquoi une refonte : supprimer le point de vue de Dieu

`generate_tei_shadow_graph` gardait deux hypothèses « œil de Dieu » : une
boucle `for` globale qui avance tous les nœuds en lock-step, et un
échantillonnage des parents sur *tout* le front. `generate_event_driven_shadow_graph`
les supprime : tas de priorité **asynchrone** (délai local par nœud, pas
d'horloge globale), **marche aléatoire locale bornée** pour le choix des
parents, et surtout une mesure de croissance depuis le *point de vue d'un
Observateur* (une worldline auto-continuée) plutôt que depuis une origine
extérieure. Conception et historique : `math/event_driven_shadow_analysis.md`.

### Deux impasses documentées (échecs francs)

Avant la version qui marche, deux tentatives ont échoué *outright*, et sont
consignées comme mises en garde :

1. **Observateur à nœud fixe + tas global** : l'Observateur meurt de faim
   (croissance logarithmique) — un nœud fixe n'accumule pas de ticks.
2. **Observateur à nœud fixe + marche locale** : même famine.

La solution : un Observateur **worldline auto-continué** (chaque « soi » futur
est par construction un descendant du premier). Il fallait aussi que
`walk_hops` et `background_ratio` soient assez grands, sinon la courbe mesurée
est indistinguable d'une droite triviale.

### Étude 50 graines : verdict négatif, plus fort que le premier

L'exposant du cône causal de l'Observateur est ~1.0-1.5, jamais proche de 3,
dépend de k, dérive vers 1 pour k=3/4, et — coup fatal — **n'est même pas
indépendant du paramètre arbitraire `background_ratio`**. « L'exposant de la
règle » n'est donc pas une quantité bien définie. Mise en garde gravée : ne pas
sauver cela en cherchant un triplet `(k, background_ratio, walk_hops)` qui
tombe près de 3 — la table de sensibilité aux paramètres est *précisément* la
preuve qu'une telle trouvaille serait vide de sens.

---

## Acte IV — La largeur d'intervalle et la dimension spatiale (7 juillet)

### Changer l'observable, pas le générateur

Le cône cumulatif mélange la direction temporelle (« mémoire ») et la
direction transverse (« espace »), et traîne la chaîne worldline (pente 1)
dans son plancher. Nouvel observable : `interval_width` / `max_antichain_size`
— la **largeur transverse** (antichaîne maximale, calcul exact via Dilworth /
matching) d'un intervalle d'Alexandrov, dont l'exposant estime la dimension
spatiale d-1 *sans* la chaîne dans le plancher.

### Réussite partielle, puis diagnostic implacable

Ça répare *vraiment* la pathologie `background_ratio` (l'exposant de largeur
*est* invariant sous ce paramètre). Mais l'exposant dépend encore de k et
dérive. Un passage de diagnostic (sans nouveau mécanisme) trouve la cause
racine : la largeur d'un intervalle de hauteur fixe glissé le long de la
worldline **s'effondre quand l'Observateur vieillit** (k=3 : 75 à l'âge 100 →
4 à l'âge 1200), vers le plancher de la chaîne nue (1) pour tout k.

**L'Observateur se découple du flux de fond avec l'âge.** La dimension
spatiale émergente asymptotique est donc effectivement **0 (une worldline 1D
nue)** ; la richesse précoce (le quasi-succès d~3 à k=3) est un *transitoire de
naissance*, pas une dimension — documenté et désamorcé pour ne jamais être
re-rapporté comme un résultat.

### Un critère pré-enregistré, avant de construire quoi que ce soit

Ce diagnostic pose la **condition de succès de toute mécanique future**
d'attraction/courbure, *avant* de la construire : une largeur de fenêtre
glissante **stationnaire** vs l'âge (à une valeur *non-triviale* — plat à 1 est
le point fixe dégénéré du fil nu et ne compte pas). Ce n'est pas un exposant
proche de 3 qu'on vise désormais, c'est la **persistance**.

---

## Acte V — La matière : le motif fermé et la quête du halo (7-8 juillet)

### Le routage réfractif, et son premier échec

`charge_biased_routing` : la marche est pondérée par 1+charge (la même loi que
le délai, pas un knob neuf). Idée : le flux « réfracte » près de la masse
(TEI 7.7). Verdict (Axe 1) : **échec par condensation sur hubs** — le flux se
condense sur les hubs de fond (charge max 26 → ~1100), la largeur s'écrase à 1.
Le mécanisme de gravité implémenté *draine* son voisinage au lieu de le
remplir.

### v0.7 : l'Observateur devient un motif fermé (la matière)

Pivot conceptuel majeur (TEI 6ter.3-D) : l'Observateur n'est plus un nœud
unique mais un **motif fermé** — un worldtube de W nœuds par antichaîne
(generation), tressé par 2 parents internes par nœud, se métabolisant par des
captures antichaîne-vérifiées, l'entropie étant la rotation générationnelle.
`generate_braided_motif_graph`. Prédiction structurelle testée et confirmée :
**k=2 est scellé** (aucun créneau de capture — un cristal inerte).

Verdict du halo A/B pré-enregistré : **la clôture guérit l'évaporation** — le
motif tient une largeur stationnaire non-triviale (~1.6·W) *pour toujours*, la
**première structure persistante du projet**. Mais le **halo réfractif est
nul-à-négatif** pour tout W. La matière persiste et ne courbe rien.

### Trois négatifs successifs sur le halo (la rigueur en action)

1. **v0.7** : cause racine — la rotation plafonne la résidence par nœud ; la
   masse du motif est collective mais la marche réfractive pèse la charge *par
   nœud* (membres à charge ~3 invisibles à côté de hubs de fond à ~600-900).
2. **Consommation** (loi de conservation, TEI 7.7 : la capture *consomme* sa
   proie, événement en attente invalidé + re-planifié) : la **ceinture
   d'accrétion chargée se forme exactement comme prévu** (Canal 1, dilatation
   temporelle près de la masse, mécaniquement réelle), capture 98-100 %, **mais
   le halo reste nul**. Cause vérifiée : le motif est un pur *absorbeur* — ses
   membres sont les seuls nœuds exemptés du tas d'événements, donc il ne
   *rayonne* jamais (violant TEI 6bis.2). Canal 2 (« espace sécrété ») manquant
   par structure.
3. **Rayonnement structurel** (les générations retirées re-rentrent au tas ;
   plus aucun nœud exempté) : le rayonnement *marche* (fraction de sillage
   propre 49-59 % en routage aveugle), **mais la réfraction envoie encore la
   marche vers la classe de hubs incumbente** (sillage propre 0-7 %) — un
   monopole de charge du premier arrivé qu'aucune population émise ne rattrape.
   **3e négatif.** Soupçon d'une borne de débit : le self-halo d'un corps
   unique pourrait être structurellement incapable de croître.

Mise en garde constante : ne pas forcer le halo par des patchs de loi de
routage (boosts de sillage, plafonds de hubs, pondération par l'âge) — c'est le
mode d'échec TEI-3.x.

---

## Acte VI — Deux corps : gravité, chute, horizon causal (8 juillet)

### Changer l'observable : la sonde Terre-Mars

Puisque le self-halo d'un corps échoue trois fois, on change de *quoi* on
mesure : deux motifs fermés, et le canal causal *entre* eux (TEI 6bis.4).
`generate_two_motif_graph` + `first_contact_lag`.

Calibration d'échelle d'abord (une découverte à part entière) : la portée
d'interaction `walk_hops` *façonne la géométrie de l'univers* — hops≥8 = un
univers à une pièce (les corps fusionnent à la naissance), hops=2 = univers
étendu mais métabolisme étouffé, hops=3 = la fenêtre étroite qui marche.

### Réussite et limite

- **Réussite** : le **premier différentiel réfractif positif du projet** — des
  corps séparés se couplent dans 5/10 runs réfractifs vs 0/10 aveugles, avec
  une dynamique d'infall chronométrée.
- **Limite** : pas de canal stationnaire. Les issues sont **bimodales**
  (silence total ou fusion), le couplage soutenu n'atteint que le passé fossile
  du partenaire, et « l'espace entre les corps » n'existe toujours pas.

### La métrologie : reconstruire la métrique passée

Instruments purement observationnels (`id_watermarks` + `_hops_at_time` +
`intertube_metrics` + `wake_gap`) : les arêtes pointent vieux→neuf, donc le
sous-graphe sur les ids anciens *est* l'état passé de l'univers, métrique
comprise. Résultats mesurés :

- La **récession** est réelle, linéaire (~1.08 hops/génération),
  indépendante du routage.
- Le front de sillage rayonné n'avance qu'à ~0.53 hops/génération : **la
  métrique dépasse le signal 2 pour 1** — un **horizon causal** mesuré. Toute
  génération émise après la fenêtre précoce rayonne dans un horizon dont elle
  ne ressort jamais. C'est pourquoi le couplage n'atteint que le passé fossile.
- L'infall n'est **pas** une accélération constante : trois phases (récession,
  demi-tour au premier pont de sillage, fermeture quasi-linéaire par tricotage
  d'arêtes de capture — une **fermeture éclair**, pas une chute balistique). La
  bimodalité silence/fusion est une course à la naissance (le pont doit se
  former en ~30 générations avant que la récession n'emporte le partenaire
  au-delà de l'horizon). Le taux de récession est spécifique à l'architecture ;
  le phénomène d'horizon est structurel.

---

## Acte VII — La longue quête de l'inertie (9-10 juillet)

### L'impulsion tangentielle, et son échec par éjection

Pour désaxer la fusion radiale en orbite : une condition initiale de « moment
angulaire » (`kick_ticks`, `kick_mode` — une fenêtre d'asymétrie métabolique,
lois intouchées, `kick_ticks=0` reproduit le générateur bit-pour-bit). Verdict
**négatif, par éjection** : le burn *affame* le motif (capture 2-9 %), la
cinématique des tubes éjecte les corps à d~54 en 25 générations, tous les runs
deviennent silencieux. La décomposition en mouvement propre montre T=0 pendant
et après le burn : **aucune dérive latérale injectée**. Conclusion posée : le
substrat n'a pas de moment angulaire parce qu'il **n'a pas d'inertie** — il ne
conserve aucune variable portant un *taux*.

### Retour en arrière n°2 (correction de cadre, cruciale)

Cette conclusion reposait sur une **erreur de cadre**, signalée par Stef et
acceptée : avec seulement *deux* corps, il n'existe qu'une seule distance (une
ligne, 1D). Un axe transverse ne peut littéralement pas exister — le scalaire
tangentiel T mesurait une coordonnée qui *n'est pas là*. Ce n'était pas un null
sur l'inertie. **La coordonnée transverse n'existe qu'à trois corps.**

### Trois corps : l'inertie testée dans le bon cadre

`generate_three_motif_graph` + `triangle_angle` : A et B fixent une ligne de
base, l'angle de C par rapport à elle (loi des cosinus sur les 3 distances de
saut, en métrique passée) est une position transverse 2D **invariante
d'échelle** (la récession commune s'annule). `test_mode ∈ {plain, correlated,
correlated_seed, forced}`, `forced` étant un **contrôle instrumental**
pré-enregistré (advection latérale forcée : il *doit* bouger l'angle de façon
balistique, sinon l'observable est aveugle).

Verdict (5 graines × 900 gén) : `forced` = exposant de dérive **1.21
(balistique — instrument validé)**, tandis que plain / correlated /
correlated_seed = **~0.56-0.59 (diffusif)**, nettement séparés, métabolisme
sain. **Pas d'inertie tangentielle**, cette fois un null *positif* dans le
cadre où la coordonnée existe vraiment : le mécanisme A⊕B encode une
*disposition* latérale (il change la tresse et l'angle de naissance de C) mais
elle ne s'intègre pas en mouvement balistique.

### Le spin topologique : conservé, mais pas de l'inertie

Puisque la topologie est la seule chose que ce graphe conserve naturellement :
`test_mode="chiral"` (`chirality ∈ {+1,-1}`) donne à la tresse une chiralité
stricte — le brin i parente le bloc consécutif `[i, i+h, …]` mod W et démarre
sa marche depuis `previous[(i+h)%W]`, si bien que le cap d'intake *circule*
dans une direction fixe (robuste topologiquement, pas de knob). Porte
métabolique franchie (le twist *améliore* la capture : 86-91 % vs 67 %).

Verdict : les **deux handedness sont diffusives** (0.49, 0.64),
indistinguables de plain, nettement séparées du balistique `forced` (1.21),
sans dérive miroir-antisymétrique. **Un spin protégé n'est pas de l'inertie** :
le substrat *peut* porter une charge topologique conservée (l'enroulement est
robuste et altère le métabolisme) mais ne la convertit pas en un *taux*
conservé. Un spin est une part de *ce qu'est* le corps, pas de *comment il
bouge*.

---

## Acte VIII — Le QR code du mouvement (10 juillet)

### Le recadrage strictement markovien (les 3 lois de Stef)

Trois lois fixées d'avance : (1) **pas de mémoire** — le présent N est le jeu
complet d'instructions (« QR code ») pour N+1 ; (2) le **mouvement constant
n'invoque pas l'inertie** — c'est la perpétuation d'un état, pas un changement
résisté ; (3) l'état de mouvement doit donc être **encodé dans la structure
présente**, dont la *lecture* le déplace tout en le reproduisant. Formellement :
un état propre de translation Φ(σ)=T(σ) de la carte à un pas. Les nulls
antérieurs triangulent ce qu'il faut : auto-perpétuant + lisible par le flux +
auto-contenu, *simultanément*.

Trois encodages analysés :

- **Option B — dipôle de charge d'interface** : **rejetée sur papier**. Les
  deux seules lectures de la charge ont le signe anti-propulsif (l'aveugle
  l'ignore, la réfraction la *remonte* vers la traîne) ; inverser ce signe
  contredirait la gravité du Canal 1. On ne sacrifie pas la gravité pour
  fabriquer du mouvement.
- **Option A — le front d'accrétion auto-collimaté** (`test_mode="front"`) :
  le QR code = les arêtes d'entrée externes de la membrane (les proies du
  présent, pure structure présente), et les W marches de N+1 démarrent de ce
  pool partagé. Règle binaire, pas de knob.
- **Option C — l'exclusion antichaîne stricte** (`test_mode="strict"`) : une
  proie doit être indépendante de *toute* la membrane précédente.

### Option A : le codage marche, mais compile en liaison

Porte métabolique franchie (99-100 %). Verdict : **verrouillage de capture,
5/5 graines**. Le feedback s'auto-perpétue *parfaitement* (le codage markovien
*marche*, contrairement au pointeur caché de `correlated`) — mais son point
fixe est l'*attachement*, pas le mouvement : en ~100 générations C se verrouille
sur le corps de référence le plus proche et le chevauche à distance 1-3 pour
580+ générations, mangeant 94-97 % de ses captures sur la membrane de l'hôte.
L'instrument angulaire montre la signature d'**ancrage** pré-enregistrée
(plateaux quantifiés gelés à 60/90/120°), pas une dérive balistique.

Lecture structurelle appartenant à l'ontologie : **le flux est périssable**
(axiome TEI). Le seul locus d'intake renouvelable à position stable est un
autre worldtube — donc un état de déplacement auto-perpétuant ne peut pas
pointer vers *l'espace*, seulement vers *la matière*. **Le QR code du mouvement
compile en capture gravitationnelle.** Bénéfice inattendu consigné : c'est le
**premier état lié à deux corps stable** du projet (ni silence ni fusion — un
binaire de contact, identité de C intacte).

### Option C : la géométrie répond

Verdict : **échec de porte métabolique avec une découverte géométrique
positive**. La capture démarre ~60-70 % puis s'effondre à 7-13 % en ~60
générations — et la cause mesurée est le résultat le plus fort de l'arc : le
voisinage d'un corps plain contient **0 % de nœuds strictement indépendants à
tout rayon ≤ 6, à tout âge**. L'espace local d'un corps est *entièrement* fait
de ses propres intrications causales (le métabolisme ordinaire est, en termes
stricts, ~100 % de ré-interprétation du cône étendu du corps). Une graine sur
trois échappe à la famine en se verrouillant sur le worldtube du partenaire —
le même attracteur d'état lié que `front`, atteint par le chemin inverse.

**Adjudication du programme QR code** : B rejetée sur le signe, A et C se
terminent toutes deux en *matière liée à la matière*. Un état de déplacement
pointant vers *l'espace* n'existe pas dans ce substrat à cette échelle, parce
qu'à portée métabolique il n'y a **pas d'espace causalement frais** où aller.

---

## Acte IX — La genèse matérielle : la soupe primordiale (10 juillet)

### Le pivot de paradigme

La directionnalité mène à l'interaction forte, c'est-à-dire à la matière. On
arrête de chercher la mécanique céleste et on suit la matière.
`generate_soup_graph` : N=20 corps indépendants, tous sous la règle A (front),
semés au hasard (aucun contrôle de séparation), **sélection aveugle** avec un
cutoff de mort pré-enregistré (0 capture pendant 5 générations → dissolution ;
le fossile reste mangeable).

### Une architecture à deux phases, pilotée par le flux

- **Abondance (20 événements/corps)** : un **gaz** — 60/60 survivent, capture
  96-100 %, régime croisé médian 21-27 %, contacts transitoires. Et surtout :
  **le verrouillage parasitaire du labo 3-corps ne se reproduit pas (0/60 vs
  5/5)**. Le binaire parasite était un *artefact de basse densité* : dans une
  foule, chaque voisinage est une soupe de sillages mêlés, la rétroaction du
  front ne converge jamais sur un seul tube. (Un négatif qui recadre un
  résultat antérieur — c'est un retour en arrière salutaire.)
- **Rareté (5 événements/corps)** : *condensation* — zéro mort encore, mais le
  régime croisé saute à médiane 90 % et les contacts condensent en un **réseau
  trophique réciproque** (intra-amas 63-99 %, 0 % extra-amas, pas d'hôte
  dominant) — un métabolisme communal fermé qui vainc la rareté en recyclant sa
  propre matière. **Survivre et s'agréger sont le même acte.**

### Cristallographie : la forme est une loi, la taille est stochastique

Passage cristallographique 5 graines. La topologie est *toujours* une
**gouttelette liquide dense homogène** — une clique de broutage mutuel (densité
≥0.94, clustering ≥0.95, Gini de degré ~0, balance de flux 0.71-0.88), **pas**
une étoile/chaîne/anneau. Le seuillage progressif la dissout *uniformément*
(pas de cœur cristallin, pas de liaison forte privilégiée). Il *y a* une
différenciation **cœur/surface** (cœur : bg 0-2 %, saturé ; surface : bg
20-41 %, valence libre). Mais la taille finale est stochastique (9,6,4,5,4 ;
médiane ~5) et l'univers fait *plusieurs* gouttelettes coexistantes. La
condensation produit une *forme* reproductible à une *taille* imprévisible —
exactement le rapport d'un liquide à ses gouttes.

---

## Acte X — La thermodynamique émergente (10 juillet)

### Le thermomètre causal

La température n'est pas dans les axiomes de la TEI ; si la soupe en a une, elle
est émergente. Définition : la **volatilité topologique des liens de
broutage**. `grazing_bond_volatility` — un lien i→j est actif quand le tube de
j fournit ≥20 % des captures de i sur une fenêtre disjointe ; `turnover` /
`occupancy_mean` / `frozen_fraction` mesurent le brassage.

### Correction méthodologique (attrapée avant de conclure)

Le premier passage utilisait une fenêtre *glissante* (chevauchement 95 %), ce
qui épinglait le turnover à un plancher lié à la largeur de fenêtre (~17 gén
dans *toutes* les phases) et masquait tout le signal. Corrigé par des
**fenêtres disjointes**. Le turnover garde un confound de densité partiel,
neutralisé par les métriques par-lien `occupancy_mean` / `frozen_fraction` (non
confondues, qui bougent de même) — le refroidissement est donc réel.

### Trois états, puis un quatrième par le temps

Un *unique* observable résout trois états ordonnés monotonement par le flux :
**gaz** (turnover 0.96, occ 0.12, 0 lien gelé), **liquide** (0.81 / 0.21),
**liquide froid** (2 év/corps : 0.71 / 0.28). À 250 générations, le flux seul
ne gèle pas. La variable de gel est le **temps** : à froid + horizon long,
certaines graines **cristallisent** (turnover → ~0.1, frozen → 0.6-0.9) — une
**nucléation stochastique**, franche, pilotée par le temps.

### Cristal ou verre ? Le verdict final

Étude d'horizon (12 graines × 1500 générations, 2 év/corps) :

- **Le taux de nucléation plafonne à ~17 %** (2/12 à 1500 gén = les *mêmes* 2
  graines qu'à 600 gén — zéro nouvelle cristallisation sur 900 générations de
  plus). La cristallisation est un événement **précoce ou jamais** (~gén
  250-600).
- Les 10 autres graines restent piégées **indéfiniment** dans un liquide
  surfondu métastable — un **verre causal** — avec un continuum de pré-gel.

**La TEI a inventé le verre autant que le cristal.** Le gel n'est pas une
fatalité ; le substrat supporte gaz, liquide, cristal *et* verre.

Anatomie du germe (2 cristallisateurs) : le cristal **nuclée dans le cœur
saturé** (liens cœur-cœur gelés dès l'onset) et rayonne vers l'extérieur (les
liens de surface à valence libre se figent 50-150 générations plus tard). La
surface est la *dernière* à geler, pas la première.

---

## Bilan transversal

### Ce qui est établi (les réussites)

1. **Un instrument causal-set validé** (Myrheim-Meyer, dim 2/3/4), avec sa
   provenance clairement séparée de toute prétention TEI.
2. **La Règle de l'Ombre Causale casse le régime exponentiel générique** — un
   effet réel, reproductible, non-trivial (même si N³ n'est jamais confirmé).
3. **La matière existe** : le motif fermé tressé persiste pour toujours (la
   première structure stable), guérissant l'évaporation du fil 1D nu.
4. **La dilatation temporelle (Canal 1)** : une ceinture d'accrétion chargée se
   forme mécaniquement près de la masse.
5. **L'attraction gravitationnelle** : premier différentiel réfractif positif
   (5/10 vs 0/10), avec chute (fermeture éclair) et fusion.
6. **Un horizon causal 2:1 mesuré** : la métrique dépasse le signal, phénomène
   structurel.
7. **La genèse matérielle multi-phases** : gaz, liquide, et une gouttelette
   liquide dense à structure cœur/surface.
8. **Une thermodynamique émergente à quatre états** (gaz/liquide/cristal/verre)
   lue par un seul observable, avec transitions de type changement de phase.

### Ce qui a échoué (les négatifs honnêtes)

1. **N³ n'est jamais confirmé** — sous aucune métrique, aucun générateur.
   L'exposant ne se stabilise pas.
2. **Le halo gravitationnel (Canal 2, « espace sécrété ») n'est jamais
   obtenu** — trois négatifs successifs pour un corps unique.
3. **L'inertie / le moment angulaire sont absents** — testés dans le bon cadre
   3D, via l'A⊕B, via un spin topologique : tout reste diffusif.
4. **L'orbite stable est impossible** au niveau exploré : silence, fusion
   radiale, ou liaison de contact — jamais une séparation stationnaire.
5. **« L'espace entre les corps » n'existe pas** : à portée métabolique, il n'y
   a pas d'espace causalement frais ; tout état de déplacement pointe vers la
   matière.

### Les retours en arrière, et pourquoi ils comptent

- **Métrique hops → plus long chemin** (Acte II) : pour tester si les
  raccourcis, pas la règle, causaient la dérive. Réponse : ni l'un ni l'autre
  ne stabilise l'exposant.
- **Le bug du fit à 0.3** (Acte II) : une fausse stabilisation attrapée et
  consignée publiquement.
- **Le cadre 2D → 3D pour l'inertie** (Acte VII) : la plus importante. Conclure
  « pas d'inertie » à deux corps était une erreur de cadre (1D, pas d'axe
  transverse). Le vrai null exige trois corps.
- **Le verrouillage était un artefact de densité** (Acte IX) : le parasite
  binaire 5/5 du labo 3-corps ne se reproduit pas dans la foule (0/60) — un
  résultat de labo recadré par le passage à l'échelle.
- **Le biais de fenêtre chevauchante** (Acte X) : un thermomètre qui semblait
  plat, corrigé en fenêtres disjointes avant toute conclusion.

### La méta-leçon : la discipline a tenu

À chaque étape, la tentation TEI-3.x était nommée *à l'avance* et évitée : ne
pas tuner un knob vers l'exposant 3, ne pas choisir la métrique qui flatte, ne
pas sauver le halo par une loi de routage ad hoc, ne pas exempter les autres
corps du pool de front (« ne mange pas les corps »), ne pas chercher un scope
d'indépendance intermédiaire qui passe la porte, ne pas tuner le flux vers une
cible de gel. Les critères de succès étaient pré-enregistrés (la largeur
stationnaire, l'instrument `forced` balistique, la porte métabolique 60-90 %).
Les mesures cassées étaient corrigées et le dites. **C'est précisément ce
refus de fabriquer les résultats espérés qui a rendu crédibles ceux qui ont
émergé.**

### Le récit en une ligne

Le substrat de la TEI, sommé de produire de l'espace vide et du mouvement
inertiel, refuse — mais, ce faisant, il produit *spontanément* de la matière
close, une gravité par dilatation temporelle, un horizon causal, et une
thermodynamique complète de la matière condensée. Il conserve *ce qu'est* un
corps (clôture, topologie) et *où* il est (son voisinage), jamais *comment il
bouge* (aucune variable ne porte un taux). L'espace, dans ce modèle, n'est pas
un milieu qu'un corps traverse : c'est son propre sillage, plus les autres
corps.

---

## Annexe — Carte du code et des documents

### Générateurs (`sim/graph_generators.py`)

| Fonction | Rôle | Acte |
|---|---|---|
| `sprinkle_minkowski` + `reachable_within_ticks` | étalon causal-set (dim imposée) | I |
| `generate_random_dag` | contraste exponentiel générique | I |
| `generate_tei_shadow_graph` | Règle de l'Ombre Causale (embarquée nulle part) | II |
| `generate_event_driven_shadow_graph` | version asynchrone, observateur-relative | III-IV |
| `generate_braided_motif_graph` | le motif fermé = la matière (v0.7 → conso → rayonnement) | V |
| `generate_two_motif_graph` | sonde deux corps + kick tangentiel | VI-VII |
| `generate_three_motif_graph` | inertie transverse (plain/correlated/forced/chiral/front/strict) | VII-VIII |
| `generate_soup_graph` | soupe primordiale N corps, sélection aveugle | IX |

### Observables et instruments

`max_antichain_size` / `interval_width` (largeur transverse exacte, Dilworth) ·
`longest_path_depths` / `reachable_within_depth` (temps propre par plus long
chemin) · `_hops_at_time` (reconstruction de la métrique passée) ·
`intertube_metrics` / `wake_gap` / `worldtube_drift` / `first_contact_lag`
(métrologie deux corps) · `triangle_angle` (position transverse 2D invariante
d'échelle) · `grazing_bond_volatility` (le thermomètre causal).

### Documents d'analyse (le détail brut)

- `math/causal_set_dimension.md` — provenance de la loi τ^dim (Myrheim-Meyer).
- `math/tei_shadow_rule_analysis.md` — Parties A & B de la Règle de l'Ombre.
- `math/event_driven_shadow_analysis.md` — l'arc complet, de l'architecture
  événementielle jusqu'au verre causal (le journal technique le plus long).
- `CLAUDE.md` — résumé canonique pour les assistants, avec la discipline.
- `README.md` — présentation pour un lecteur nouveau.

### Chronologie (dates de commit)

- **6 juil.** : instrument causal-set ; Règle de l'Ombre Causale.
- **7 juil.** : métrique plus long chemin ; architecture événementielle ; étude
  50 graines (N³ négatif) ; largeur d'intervalle ; diagnostic du découplage ;
  routage réfractif ; motif tressé (v0.7).
- **8 juil.** : consommation ; rayonnement structurel ; sonde deux corps ;
  métrologie (horizon 2:1).
- **9 juil.** : impulsion tangentielle ; verdict « pas d'inertie ».
- **10 juil.** : trois corps ; spin chiral ; front d'accrétion ; exclusion
  stricte ; soupe primordiale ; cristallographie ; thermomètre causal ;
  thermodynamique ; cristal-vs-verre.
