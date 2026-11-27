# Convencions de la sèrie CTE

Repositori d'extensions d'IngeTrazo lligades al CTE. Es treballa en català.

## Noms i estructura

- Nom visible: «CTE <tema>». Paquet: `cte_<tema>`.
- Una carpeta per extensió: `<tema>/{cte_<tema>/, tests/, tools/, docs/, README.md}`.
- Textos de la interfície en anglès al codi, amb català i castellà a `texts.py`.
- La guia d'estil de la interfície és a `docs/estil/` del repositori [ingetrazo-render-studio](https://github.com/moominot/ingetrazo-render-studio).

## La norma

- Contrasta sempre les xifres amb el PDF oficial de codigotecnico.org; no les escriguis de memòria.
- El que diu la norma va en una targeta pròpia (p. ex. «DB SUA 1»): indica **Compleix / No compleix** i **no canvia el disseny**.
- Digues sempre què **no** es comprova (al quadre d'ajuda i al README).
- Criteri adoptat a les rampes: 3,00 m i 6,00 m justos s'accepten (10 % i 8 %), encara que el text digui «menor que».

## Proves

Des de la carpeta de l'extensió:

```bash
INGETRAZO_SRC=<codi d'IngeTrazo> QT_QPA_PLATFORM=offscreen uv run --no-project --with pyside6 --with numpy --with pytest python -m pytest tests
```

El recorregut en finestra (`tools/shots.py`) pot acabar amb una fallada de segmentació en tancar-se, també sense cap extensió: mira les línies «OK».

## Repositori públic o compartible

Sense noms de clients, rutes locals ni dades personals.
