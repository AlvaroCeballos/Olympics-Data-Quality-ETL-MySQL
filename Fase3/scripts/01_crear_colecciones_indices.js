// =============================================================================
// 01_crear_colecciones_indices.js
// Integrante 1: Creación de colecciones e índices
// =============================================================================

const dbName = 'olimpiadas';
const b = db.getSiblingDB(dbName);

print("=== INICIANDO CREACION DE COLECCIONES E INDICES EN '" + dbName + "' ===");
print("Fecha y hora de ejecucion: " + new Date().toISOString());

// 1. Colección: resultados
if (!b.getCollectionNames().includes('resultados')) {
  b.createCollection('resultados');
  print("Coleccion 'resultados' creada.");
} else {
  print("Coleccion 'resultados' ya existía.");
}

print("Creando indices para 'resultados'...");
b.resultados.createIndex({ "atleta.id": 1, "olimpiada.anio": 1 }, { name: "idx_resultados_atleta_anio" });
b.resultados.createIndex({ "pais.codigo": 1, "olimpiada.anio": 1, "deporte": 1 }, { name: "idx_resultados_pais_anio_deporte" });
b.resultados.createIndex({ "noc.codigo": 1, "olimpiada.anio": 1 }, { name: "idx_resultados_noc_anio" });

// 2. Colección: atletas
if (!b.getCollectionNames().includes('atletas')) {
  b.createCollection('atletas');
  print("Coleccion 'atletas' creada.");
} else {
  print("Coleccion 'atletas' ya existía.");
}

print("Creando índices para 'atletas'...");
b.atletas.createIndex({ "nombre_norm": 1 }, { name: "idx_atletas_nombre_norm" });
b.atletas.createIndex({ "tokens": 1 }, { name: "idx_atletas_tokens" });
// id_externo es nulo para los atletas provenientes de Kaggle (DT-001)
b.atletas.createIndex({ "id_externo": 1 }, { name: "idx_atletas_id_externo_parcial", partialFilterExpression: { id_externo: { $type: "number" } }, unique: true });

// 3. Colección: paises
if (!b.getCollectionNames().includes('paises')) {
  b.createCollection('paises');
  print("Coleccion 'paises' creada.");
} else {
  print("Coleccion 'paises' ya existía.");
}

print("Creando indices para 'paises'...");
b.paises.createIndex({ "codigo": 1 }, { name: "idx_paises_codigo_unique", unique: true });
b.paises.createIndex({ "nombre_norm": 1 }, { name: "idx_paises_nombre_norm" });
b.paises.createIndex({ "nocs.codigo": 1 }, { name: "idx_paises_nocs_codigo" });

// 4. Colección: ediciones
if (!b.getCollectionNames().includes('ediciones')) {
  b.createCollection('ediciones');
  print("Coleccion 'ediciones' creada.");
} else {
  print("Coleccion 'ediciones' ya existía.");
}

print("Creando indices para 'ediciones'...");
b.ediciones.createIndex({ "anio": 1, "temporada": 1 }, { name: "idx_ediciones_anio_temp_unique", unique: true });
b.ediciones.createIndex({ "sede.pais_codigo": 1 }, { name: "idx_ediciones_sede_pais_codigo" });

print("=== FINALIZADO CON EXITO LA CREACION DE COLECCIONES E INDICES ===");