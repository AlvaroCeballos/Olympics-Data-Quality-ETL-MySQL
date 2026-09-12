import pandas as pd

excel_path = 'Datasets.xlsx'
xls = pd.ExcelFile(excel_path)

# Exporta cada pestaña a un CSV individual optimizado
for sheet in xls.sheet_names:
    df = pd.read_excel(excel_path, sheet_name=sheet)
    # Guardar las primeras 5 filas para contexto ligero o df completo para pruebas
    df.head(15).to_csv(f"{sheet}_sample.csv", index=False, encoding='utf-8')
    print(f"Exportada hoja: {sheet} -> {sheet}_sample.csv")