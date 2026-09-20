# Instrucciones de Agente para JsBOT

Este proyecto cuenta con soporte integrado para **Graphify** (`skills/graphify/SKILL.md`).

## Habilidades y Comandos Disponibles

- **/graphify**: Convierte el código, documentación, bases de datos y assets en un grafo de conocimiento navegable (`graphify-out/`).
  - Uso: `/graphify .` para analizar la base de código de JsBOT.
  - Genera: `graphify-out/graph.html` (visualizador interactivo), `graphify-out/GRAPH_REPORT.md` (reporte de arquitectura y nodos clave), `graphify-out/graph.json` y bóveda para Obsidian.
