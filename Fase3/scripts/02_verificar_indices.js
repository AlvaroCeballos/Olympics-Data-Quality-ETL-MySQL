// =============================================================================
// 02_verificar_indices.js
// Verificación de índices y rendimiento de consultas
// =============================================================================

const dbName = 'olimpiadas';
const b = db.getSiblingDB(dbName);

print("=== INICIANDO VERIFICACION DE INDICES Y RENDIMIENTO EN '" + dbName + "' ===");
print("Fecha y hora de ejecucion: " + new Date().toISOString());

// Casos de prueba representativos para validar el uso de índices
const casos = [
  {
    nombre: "Consulta Atleta por ID en resultados",
    coleccion: b.resultados,
    query: { "atleta.id": 678 }
  },
  {
    nombre: "Consulta País por Código en resultados",
    coleccion: b.resultados,
    query: { "pais.codigo": "FRA" }
  },
  {
    nombre: "Consulta Atleta por Nombre Normalizado en atletas",
    coleccion: b.atletas,
    query: { "nombre_norm": "usain bolt" }
  },
  {
    nombre: "Consulta País por Código en paises",
    coleccion: b.paises,
    query: { "codigo": "FRA" }
  },
  {
    nombre: "Consulta Edición por Año y Temporada en ediciones",
    coleccion: b.ediciones,
    query: { "anio": 2008, "temporada": "Summer" }
  }
];

let todosIndicesOk = true;

casos.forEach((caso, i) => {
  print("\n------------------------------------------------------------------");
  print(`Caso ${i + 1}: ${caso.nombre}`);
  print("Filtro: " + JSON.stringify(caso.query));
  
  const exp = caso.coleccion.find(caso.query).explain("executionStats");
  const stats = exp.executionStats;
  const planner = exp.queryPlanner;
  
  // Extraer el plan ganador
  let winningPlan = planner.winningPlan;
  let stage = winningPlan.stage;
  
  // Si hay un stage de FETCH, el stage de escaneo suele estar dentro de inputStage
  if (stage === "FETCH" && winningPlan.inputStage) {
    stage = winningPlan.inputStage.stage + " -> FETCH";
  }

  print("Plan ganador (Stage): " + stage);
  print("Tiempo de ejecución:  " + stats.executionTimeMillis + " ms");
  print("Documentos examinados: " + stats.totalDocsExamined);
  print("Documentos devueltos:  " + stats.nReturned);
  
  const esIndexScan = stage.includes("IXSCAN") || stage.includes("IDHACK");
  if (esIndexScan) {
    print("Resultado de índice:   [OK] La consulta utiliza ÍNDICE");
  } else {
    print("Resultado de índice:   [ALERTA] La consulta realizó COLLSCAN (escaneo completo)");
    todosIndicesOk = false;
  }
});

print("\n==================================================================");
if (todosIndicesOk) {
  print("=== RESUMEN: TODOS LOS INDICES UTILIZAN IXSCAN CORRECTAMENTE ===");
} else {
  print("=== RESUMEN: SE DETECTARON CONSULTAS SIN INDICE (REVISAR CONFIGURACION) ===");
}
print("==================================================================");