"""
Generador de Gráficos de Análisis Comparativo — Fase 2 (Integrante 3)
Sistemas de Bases de Datos 2 — Grupo 18
"""

import os
import matplotlib.pyplot as plt
import numpy as np

# Configurar estilo visual limpio y profesional
plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')
plt.rcParams['font.sans-serif'] = 'Segoe UI', 'DejaVu Sans', 'Arial'
plt.rcParams['axes.edgecolor'] = '#CCCCCC'
plt.rcParams['axes.linewidth'] = 0.8

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "evidencias", "graficos")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# -----------------------------------------------------------------------------
# DATOS MEDIDOS REALES
# -----------------------------------------------------------------------------
ciclos = ['Deportista (Leve)', 'Deporte (Medio)', 'Año (Masivo)']
etapas = ['C0 - Full', 'C1 - Diff 1', 'C2 - Diff 2', 'C3 - Diff 3']

# Tiempos de restauración (segundos) de bitacora_restauracion.csv
tiempos = {
    'Deportista': [20.60, 35.14, 34.72, 32.98],
    'Deporte':    [18.89, 34.78, 34.84, 35.24],
    'Año':        [20.53, 34.93, 35.89, 35.84]
}

# Tamaños de respaldo (MB) de backup_manifest.csv
tamanos_mb = {
    'Deportista': [99.28, 2.49, 2.59, 2.77],
    'Deporte':    [99.28, 3.10, 3.34, 3.64],
    'Año':        [99.28, 12.34, 21.75, 24.64]
}

# -----------------------------------------------------------------------------
# GRÁFICO 1: Tiempos de Restauración por Ciclo y Carga
# -----------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(10, 5.5), dpi=300)

x = np.arange(len(etapas))
width = 0.25

colors = ['#2563EB', '#059669', '#D97706']

for i, (nombre, vals) in enumerate(tiempos.items()):
    offset = (i - 1) * width
    rects = ax.bar(x + offset, vals, width, label=nombre, color=colors[i], alpha=0.9, edgecolor='white', linewidth=1)
    # Etiquetas con los valores exactos
    for rect in rects:
        h = rect.get_height()
        ax.annotate(f'{h:.1f}s',
                    xy=(rect.get_x() + rect.get_width() / 2, h),
                    xytext=(0, 3), textcoords="offset points",
                    ha='center', va='bottom', fontsize=8.5, fontweight='bold', color='#1F2937')

ax.set_ylabel('Tiempo de Restauración Física (segundos)', fontsize=11, fontweight='bold', labelpad=8)
ax.set_title('Tiempo de Restauración Física por Ciclo y Ronda de Carga\n(Percona XtraBackup 8.0 en MySQL 8.0)', fontsize=13, fontweight='bold', pad=14)
ax.set_xticks(x)
ax.set_xticklabels(['C0 (Catálogos)\nFull Backup', 'C1 (Ronda 1)\nDiferencial 1', 'C2 (Ronda 2)\nDiferencial 2', 'C3 (Ronda 3)\nDiferencial 3'], fontsize=10)
ax.legend(title='Ciclo Evaluado', title_fontsize='10', fontsize=9.5, loc='upper left')
ax.set_ylim(0, 45)
ax.grid(axis='y', linestyle='--', alpha=0.5)

# Línea de referencia explicando la meseta
ax.axhline(20.0, color='#64748B', linestyle=':', linewidth=1.2, alpha=0.7)
ax.text(3.4, 20.5, 'Línea base Full (~20s)', color='#64748B', fontsize=8, ha='right', style='italic')

ax.axhline(35.0, color='#DC2626', linestyle=':', linewidth=1.2, alpha=0.7)
ax.text(3.4, 35.5, 'Línea base Diferencial (~35s: Full prepare + Diff apply)', color='#DC2626', fontsize=8, ha='right', style='italic')

plt.tight_layout()
g1_path = os.path.join(OUTPUT_DIR, "tiempos_restauracion_por_ciclo.png")
plt.savefig(g1_path)
plt.close()
print(f"[OK] Generado: {g1_path}")

# -----------------------------------------------------------------------------
# GRÁFICO 2: Tamaño del Respaldo vs Tiempo de Recuperación
# -----------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(9.5, 5.5), dpi=300)

markers = ['o', 's', '^']
diff_colors = ['#2563EB', '#059669', '#D97706']

for i, nombre in enumerate(['Deportista', 'Deporte', 'Año']):
    # Graficar solo los diferenciales C1, C2, C3 para ver el impacto del crecimiento
    sz = tamanos_mb[nombre][1:]
    tm = tiempos[nombre][1:]
    ax.scatter(sz, tm, s=120, label=f'Ciclo {nombre} (Diff 1-3)', color=diff_colors[i], marker=markers[i], zorder=4, edgecolor='black', linewidth=0.8)
    for j, (s, t) in enumerate(zip(sz, tm)):
        ax.annotate(f'C{j+1} ({s:.1f}MB, {t:.1f}s)', xy=(s, t), xytext=(5, 5), textcoords="offset points", fontsize=8.5, color='#374151')

ax.set_xlabel('Tamaño del Respaldo Diferencial en Disco (MB)', fontsize=11, fontweight='bold', labelpad=8)
ax.set_ylabel('Tiempo de Restauración (segundos)', fontsize=11, fontweight='bold', labelpad=8)
ax.set_title('Relación entre Tamaño del Respaldo Diferencial y Tiempo de Recuperación\n(Demostración del Tiempo Base de Inicialización de InnoDB)', fontsize=13, fontweight='bold', pad=14)
ax.set_ylim(30, 40)
ax.set_xlim(0, 30)
ax.grid(True, linestyle='--', alpha=0.5)
ax.legend(title='Ciclos', fontsize=9.5, loc='lower right')

# Resaltado explicativo
ax.axhspan(32, 37, color='#FEF3C7', alpha=0.4, zorder=1)
ax.text(14, 32.5, 'Zona de Estabilidad de RTO (33s - 36s)\nEl tiempo base de InnoDB domina sobre el I/O en este rango de datos', fontsize=9, ha='center', color='#92400E', style='italic')

plt.tight_layout()
g2_path = os.path.join(OUTPUT_DIR, "tamano_backup_vs_tiempo_recuperacion.png")
plt.savefig(g2_path)
plt.close()
print(f"[OK] Generado: {g2_path}")

# -----------------------------------------------------------------------------
# GRÁFICO 3: Crecimiento del Tamaño de los Respaldos por Ciclo
# -----------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(10, 5), dpi=300)

x = np.arange(len(etapas))
for i, nombre in enumerate(['Deportista', 'Deporte', 'Año']):
    ax.plot(x, tamanos_mb[nombre], marker='o', linewidth=2.2, markersize=7, label=f'Ciclo {nombre}', color=colors[i])
    for j, val in enumerate(tamanos_mb[nombre]):
        ax.annotate(f'{val:.1f} MB', xy=(j, val), xytext=(0, 6 if i != 1 else -12), textcoords="offset points",
                    ha='center', fontsize=8.5, fontweight='bold', color=colors[i])

ax.set_ylabel('Tamaño en Disco (MB)', fontsize=11, fontweight='bold', labelpad=8)
ax.set_title('Crecimiento del Tamaño de Respaldo por Ronda de Carga\n(C0: Full Base de 99.3 MB vs C1-C3: Deltas Diferenciales)', fontsize=13, fontweight='bold', pad=14)
ax.set_xticks(x)
ax.set_xticklabels(['C0 (Catálogos)\nFull Base', 'C1 (Ronda 1)\nDiferencial', 'C2 (Ronda 2)\nDiferencial', 'C3 (Ronda 3)\nDiferencial'], fontsize=10)
ax.grid(True, linestyle='--', alpha=0.5)
ax.set_ylim(0, 115)
ax.legend(title='Estrategia por Ciclo', fontsize=9.5, loc='center left')

plt.tight_layout()
g3_path = os.path.join(OUTPUT_DIR, "crecimiento_tamano_respaldo_por_ciclo.png")
plt.savefig(g3_path)
plt.close()
print(f"[OK] Generado: {g3_path}")

# -----------------------------------------------------------------------------
# GRÁFICO 4: Comparativa de Arquitectura: Diferencial vs Incremental (RTO y Resiliencia)
# -----------------------------------------------------------------------------
fig, (ax_rto, ax_risk) = plt.subplots(1, 2, figsize=(12, 5), dpi=300)

etapas_c = ['Restaurar C1', 'Restaurar C2', 'Restaurar C3']

# RTO Proyectado: Diferencial (constante ~35s) vs Incremental (acumulación secuencial de logs)
# En incremental cada ronda suma la aplicación de un delta adicional: C1 ~35s, C2 ~48s, C3 ~62s
rto_diff = [35.0, 35.2, 35.8]
rto_inc  = [35.0, 48.5, 62.4]

x_c = np.arange(len(etapas_c))
w = 0.35

rects1 = ax_rto.bar(x_c - w/2, rto_diff, w, label='Diferencial (Estrategia Aplicada)', color='#059669', alpha=0.9, edgecolor='white')
rects2 = ax_rto.bar(x_c + w/2, rto_inc,  w, label='Incremental (Proyección)', color='#DC2626', alpha=0.8, edgecolor='white')

for rect in rects1:
    h = rect.get_height()
    ax_rto.annotate(f'{h:.1f}s', xy=(rect.get_x() + rect.get_width()/2, h), xytext=(0, 3), textcoords="offset points", ha='center', fontsize=9, fontweight='bold')
for rect in rects2:
    h = rect.get_height()
    ax_rto.annotate(f'{h:.1f}s', xy=(rect.get_x() + rect.get_width()/2, h), xytext=(0, 3), textcoords="offset points", ha='center', fontsize=9, fontweight='bold')

ax_rto.set_ylabel('RTO: Tiempo de Recuperación Estimado (segundos)', fontsize=10, fontweight='bold')
ax_rto.set_title('RTO según Estrategia de Respaldo', fontsize=11.5, fontweight='bold')
ax_rto.set_xticks(x_c)
ax_rto.set_xticklabels(etapas_c, fontsize=9.5)
ax_rto.set_ylim(0, 75)
ax_rto.legend(fontsize=8.5, loc='upper left')
ax_rto.grid(axis='y', linestyle='--', alpha=0.5)

# Gráfico de dependencias y riesgo
piezas_diff = [2, 2, 2] # Siempre Full + Diff N
piezas_inc  = [2, 3, 4] # Full + Inc1 (+ Inc2 (+ Inc3))

rects3 = ax_risk.bar(x_c - w/2, piezas_diff, w, label='Diferencial (Independencia)', color='#059669', alpha=0.9, edgecolor='white')
rects4 = ax_risk.bar(x_c + w/2, piezas_inc,  w, label='Incremental (Cadena Crítica)', color='#DC2626', alpha=0.8, edgecolor='white')

for rect in rects3:
    h = rect.get_height()
    ax_risk.annotate(f'{int(h)} piezas', xy=(rect.get_x() + rect.get_width()/2, h), xytext=(0, 3), textcoords="offset points", ha='center', fontsize=9, fontweight='bold')
for rect in rects4:
    h = rect.get_height()
    ax_risk.annotate(f'{int(h)} piezas', xy=(rect.get_x() + rect.get_width()/2, h), xytext=(0, 3), textcoords="offset points", ha='center', fontsize=9, fontweight='bold')

ax_risk.set_ylabel('Número de Archivos/Backups en la Cadena', fontsize=10, fontweight='bold')
ax_risk.set_title('Complejidad y Puntos Únicos de Fallo (SPOF)', fontsize=11.5, fontweight='bold')
ax_risk.set_xticks(x_c)
ax_risk.set_xticklabels(etapas_c, fontsize=9.5)
ax_risk.set_ylim(0, 5.5)
ax_risk.legend(fontsize=8.5, loc='upper left')
ax_risk.grid(axis='y', linestyle='--', alpha=0.5)

fig.suptitle('Análisis Comparativo de Estrategias: Diferencial vs. Incremental\n(Evaluación de RTO y Riesgo Operativo en Ambientes de Misión Crítica)', fontsize=13, fontweight='bold', y=1.02)
plt.tight_layout()
g4_path = os.path.join(OUTPUT_DIR, "comparativa_diferencial_vs_incremental.png")
plt.savefig(g4_path)
plt.close()
print(f"[OK] Generado: {g4_path}")

print("\n¡Todos los 4 gráficos generados con éxito en alta resolución!")
