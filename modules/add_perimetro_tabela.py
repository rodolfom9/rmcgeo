"""
/***************************************************************************
 RMCGeo
                                 A QGIS plugin
 Conjunto de ferramentas para simplificar tarefas geoespaciais.
                             -------------------
        begin                : 2025-06-01
        copyright            : (C) 2025 by Rodolfo Martins de Carvalho
        email                : rodolfomartins09@gmail.com
        git sha              : $Format:%H$
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

from .base_field_calculator import BaseCalculadoraTabela
from qgis.core import QgsWkbTypes
from qgis.PyQt.QtCore import QVariant


class PerimetroTabelaDialog(BaseCalculadoraTabela):
    """Adiciona campo de perímetro em metros"""
    
    window_title = "Adicionar Perímetro na Tabela"
    field_name = "Perim_m"  # Valor padrão inicial (será atualizado pelo formato)
    field_type = QVariant.String
    expression_string = "format_number($perimeter, 2)"  # Padrão: metros
    geometry_types = [QgsWkbTypes.PolygonGeometry]  # Apenas polígonos
    
    # Opções de formatação disponíveis
    format_options = {
        "Metros (m)": "format_number($perimeter, 2)",
        "Quilômetros (km)": "format_number($perimeter/1000, 3)",
        "Centímetros (cm)": "format_number($perimeter*100, 2)"
    }
    
    # Mapeamento de nomes de campo por formato
    field_names_by_format = {
        "Metros (m)": "Perim_m",
        "Quilômetros (km)": "Perim_km",
        "Centímetros (cm)": "Perim_cm"
    }


def run(iface):
    """Função principal que abre o diálogo"""
    dialog = PerimetroTabelaDialog(iface)
    dialog.exec_()
